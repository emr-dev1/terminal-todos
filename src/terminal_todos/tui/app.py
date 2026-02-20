"""Main Textual TUI application."""

import os
import warnings
import asyncio

# Suppress tqdm warnings
os.environ['TQDM_DISABLE'] = '1'
warnings.filterwarnings('ignore', category=Warning)

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input
from textual.binding import Binding

from terminal_todos.tui.widgets.todo_list import TodoListWidget
from terminal_todos.tui.widgets.chat_log import ChatLogWidget
from terminal_todos.tui.widgets.input_bar import InputBarWidget
from terminal_todos.core.todo_service import TodoService
from terminal_todos.core.note_service import NoteService
from terminal_todos.db.migrations import run_migrations
from terminal_todos.agent.graph import get_agent_graph
from terminal_todos.extraction.todo_extractor import TodoExtractor
from langchain_core.messages import HumanMessage


class TodosApp(App):
    """Terminal Todos TUI application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 3;
        grid-rows: auto 1fr auto;
    }

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #todo-pane {
        width: 40%;
        border: solid $primary;
    }

    #chat-pane {
        width: 60%;
        border: solid $accent;
    }

    #input-container {
        height: auto;
        dock: bottom;
    }

    #user-input {
        height: 3;
    }

    #user-input-multiline {
        height: 10;
    }

    TodoListWidget {
        padding: 1;
    }

    ChatLogWidget {
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("/", "command_mode", "Command", show=True),
        Binding("ctrl+l", "clear_chat", "Clear Chat", show=False),
        Binding("ctrl+r", "refresh_todos", "Refresh", show=True),
        Binding("ctrl+enter", "submit_multiline", "Send (Multi-line)", show=False),
    ]

    def on_unmount(self):
        """Clean up when app is unmounting."""
        self._cleanup()

    TITLE = "Terminal Todos"
    SUB_TITLE = "AI-powered todo management"

    def __init__(self):
        super().__init__()
        self.todo_service = None
        self.note_service = None
        self.agent_graph = None
        self.extractor = None
        self.capture_mode = False  # For multi-line capture
        self.capture_buffer = []  # Buffer for captured lines
        # Removed pending_extraction - now using waiting_for_todo_selection flow
        self.pending_note_id = None  # Note ID for pending extraction
        self.pending_deletion = None  # Stores deletion awaiting confirmation
        self.deletion_from_agent = False  # Track if deletion came from agent
        self.import_mode = False  # For multi-line import
        self.import_buffer = []  # Buffer for imported content
        self.pending_import = None  # Stores import extraction awaiting confirmation
        self.pending_import_tags = None  # Stores tags for pending import
        self.waiting_for_import_tags = False  # Flag when waiting for tag input
        self.knowledge_extractor = None  # Knowledge extractor for imports
        self.pending_extracted_todos = None  # Stores extracted todos for selection
        self.pending_extracted_priorities = None  # Stores priorities for extracted todos
        self.waiting_for_todo_selection = False  # Waiting for user to select todo numbers
        self.pending_focus_clear = False  # Waiting for confirmation to clear focus list
        self.waiting_for_focus_selection = False  # Waiting for user to select focus suggestions
        self.pending_focus_suggestions = None  # Stores suggested todo IDs for focus
        self.in_note_conversation = False  # Tracking if user is having a conversation about notes
        self.last_generated_email_id = None  # Last generated email ID for /copy-email

        # Conversation history for agent context
        self.conversation_history = []  # List of BaseMessage objects
        self.max_history_messages = 30  # Keep last N messages to avoid token limits (increased for RAG context)

    def add_to_conversation_history(self, message):
        """
        Add a message to conversation history and truncate if needed.

        Args:
            message: BaseMessage to add (HumanMessage or AIMessage)
        """
        from terminal_todos.utils.logger import log_debug

        self.conversation_history.append(message)

        # Truncate if exceeds max
        if len(self.conversation_history) > self.max_history_messages:
            removed = len(self.conversation_history) - self.max_history_messages
            self.conversation_history = self.conversation_history[-self.max_history_messages:]
            log_debug(f"Truncated conversation history, removed {removed} old messages")

        log_debug(f"Conversation history now has {len(self.conversation_history)} messages")

    def clear_conversation_history(self):
        """Clear the conversation history."""
        from terminal_todos.utils.logger import log_info

        log_info("Clearing conversation history")
        self.conversation_history = []

    def purge_recent_conversation(self, num_turns: int = 1):
        """
        Purge the last N conversation turns (user message + AI response + tool calls).

        Args:
            num_turns: Number of recent conversation turns to remove
        """
        from terminal_todos.utils.logger import log_info, log_debug

        if not self.conversation_history:
            return

        # Count turns from the end
        # A turn is: HumanMessage -> [ToolMessages] -> AIMessage
        messages_to_remove = []
        turns_removed = 0

        # Walk backwards through history
        i = len(self.conversation_history) - 1
        while i >= 0 and turns_removed < num_turns:
            msg = self.conversation_history[i]
            msg_type = msg.__class__.__name__

            # Mark this message for removal
            messages_to_remove.append(i)

            # If we hit a HumanMessage, that completes a turn
            if msg_type == "HumanMessage":
                turns_removed += 1

            i -= 1

        # Remove messages (in reverse order to maintain indices)
        for idx in sorted(messages_to_remove, reverse=True):
            removed_msg = self.conversation_history.pop(idx)
            log_debug(f"Purged message from history", {
                "type": removed_msg.__class__.__name__,
                "content_preview": str(removed_msg.content)[:50] if hasattr(removed_msg, 'content') else "N/A"
            })

        log_info(f"Purged {turns_removed} conversation turn(s), removed {len(messages_to_remove)} messages")

    def purge_confirmation_context(self):
        """
        Purge confirmation-related context from conversation history.
        This removes the last 2 turns (the request + confirmation exchange).
        """
        from terminal_todos.utils.logger import log_info

        log_info("Purging confirmation context from conversation history")
        self.purge_recent_conversation(num_turns=2)

    def clear_conversation_history(self):
        """
        Clear all conversation history to start fresh.
        Called after each complete interaction to prevent context accumulation.
        """
        from terminal_todos.utils.logger import log_info

        previous_count = len(self.conversation_history)
        self.conversation_history = []
        log_info(f"Cleared conversation history ({previous_count} messages removed)")

    def clean_tool_execution_from_history(self):
        """
        Remove ToolMessage objects from conversation history to prevent re-execution.

        This keeps the conversational flow (user questions and agent answers) but
        removes the tool execution details (ToolMessages and intermediate AIMessages
        with tool_calls) that can cause the agent to re-execute old queries.

        Called after each agent response to keep context clean.
        """
        from langchain_core.messages import AIMessage
        from terminal_todos.utils.logger import log_debug

        if not self.conversation_history:
            return

        cleaned_history = []
        removed_count = 0

        for msg in self.conversation_history:
            msg_type = msg.__class__.__name__

            # Keep HumanMessages (user questions)
            if msg_type == "HumanMessage":
                cleaned_history.append(msg)

            # Keep AIMessages that have text content (final responses)
            # Skip AIMessages that only have tool_calls (intermediate steps)
            elif msg_type == "AIMessage":
                # Check if this is a final response (has content) or just tool calls
                has_content = hasattr(msg, 'content') and msg.content and msg.content.strip()
                has_only_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls and not has_content

                if not has_only_tool_calls:
                    # This is a final response, keep it but STRIP tool_calls to prevent re-execution
                    # Create a new AIMessage with the same content but no tool_calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        # Has both content and tool_calls - strip the tool_calls
                        cleaned_msg = AIMessage(content=msg.content)
                        cleaned_history.append(cleaned_msg)
                        removed_count += 1
                        log_debug(f"Stripped tool_calls from AIMessage to prevent re-execution")
                    else:
                        # Just content, no tool_calls - keep as is
                        cleaned_history.append(msg)
                else:
                    # This is just tool call instructions, remove it entirely
                    removed_count += 1
                    log_debug(f"Removed AIMessage with only tool_calls from history")

            # Remove ToolMessages (tool execution results)
            elif msg_type == "ToolMessage":
                removed_count += 1
                log_debug(f"Removed ToolMessage from history")

            # Keep any other message types
            else:
                cleaned_history.append(msg)

        if removed_count > 0:
            self.conversation_history = cleaned_history
            log_debug(f"Cleaned {removed_count} tool execution messages from history")

    def get_conversation_summary(self) -> str:
        """Get a summary of current conversation state."""
        human_count = sum(1 for msg in self.conversation_history if msg.__class__.__name__ == "HumanMessage")
        ai_count = sum(1 for msg in self.conversation_history if msg.__class__.__name__ == "AIMessage")
        return f"{len(self.conversation_history)} total messages ({human_count} user, {ai_count} assistant)"

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()

        with Horizontal(id="main-container"):
            yield TodoListWidget(id="todo-pane")
            yield ChatLogWidget(id="chat-pane")

        yield InputBarWidget(id="input-container")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app on mount."""
        chat_log = self.query_one(ChatLogWidget)

        try:
            # Run database migrations
            chat_log.write_system("Initializing database...")
            run_migrations()

            # Initialize services
            chat_log.write_system("Starting services...")
            self.todo_service = TodoService()
            self.note_service = NoteService()

            # Initialize agent
            chat_log.write_system("Initializing AI agent...")
            self.agent_graph = get_agent_graph()
            self.extractor = TodoExtractor()

            # Load initial todos
            await self.refresh_todos()

            chat_log.write_system("✓ Ready! Type naturally or use /help for commands")

            # Focus input
            input_bar = self.query_one(InputBarWidget)
            input_bar.focus_input()

        except Exception as e:
            chat_log.write_error(f"Initialization failed: {e}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        from terminal_todos.utils.logger import log_error, log_info, log_debug

        try:
            log_debug("Input submitted event received", {"input_id": event.input.id})

            if event.input.id not in ["user-input", "user-input-multiline"]:
                log_debug("Ignoring input from unexpected source", {"input_id": event.input.id})
                return

            # Get the input
            input_bar = self.query_one(InputBarWidget)
            user_input = input_bar.get_text().strip()

            log_debug("User input received", {"input": user_input, "length": len(user_input)})

            if not user_input:
                log_debug("Empty input, ignoring")
                return

            # Add to history (for arrow key navigation)
            log_debug("Adding to input history")
            input_bar.add_to_history(user_input)

            # Clear input
            log_debug("Clearing input bar")
            input_bar.clear_input()

            # Get chat log
            chat_log = self.query_one(ChatLogWidget)

            # Log user message
            log_info(f"Processing user input: {user_input[:50]}...")
            chat_log.write_user(user_input)

        except Exception as e:
            log_error(e, "Error in on_input_submitted - before processing", show_traceback=True)
            try:
                chat_log = self.query_one(ChatLogWidget)
                chat_log.write_error(f"Failed to process input: {str(e)}")
            except:
                pass
            return

        # Handle input
        try:
            log_debug("Determining input type", {"is_command": user_input.startswith("/")})

            # Check for pending focus clear confirmation
            if self.pending_focus_clear:
                self.pending_focus_clear = False
                if user_input.lower() == "yes":
                    count = self.todo_service.clear_focus()
                    chat_log.write_success(f"✓ Cleared {count} todos from focus")
                    await self.refresh_todos()
                else:
                    chat_log.write_system("Focus clear cancelled")
                return

            # Check if waiting for focus selection
            if self.waiting_for_focus_selection:
                log_info("Processing focus selection")
                await self.handle_focus_selection(user_input)
            # Check if waiting for todo selection numbers
            elif self.waiting_for_todo_selection:
                log_info("Processing todo selection")
                await self.handle_todo_selection(user_input)
            elif user_input.startswith("/"):
                # Command mode
                log_info(f"Processing command: {user_input}")
                await self.handle_command(user_input)
            else:
                # Natural language mode - send to agent
                log_info(f"Processing natural language: {user_input[:50]}...")
                await self.handle_natural_language(user_input)

        except Exception as e:
            log_error(e, "Error in on_input_submitted - during handling", show_traceback=True)
            try:
                chat_log = self.query_one(ChatLogWidget)
                chat_log.write_error(f"Failed to handle input: {str(e)}")
            except:
                pass

    async def handle_todo_selection(self, user_input: str):
        """Handle user selection of extracted todos by number."""
        chat_log = self.query_one(ChatLogWidget)

        try:
            user_input_lower = user_input.lower().strip()

            # Parse user input
            if user_input_lower in ["none", "cancel", "no"]:
                chat_log.write_system("❌ Cancelled. No todos were created.")
                self.waiting_for_todo_selection = False
                self.pending_extracted_todos = None
                self.pending_extracted_priorities = None
                return

            if user_input_lower == "all":
                # Select all todos
                selected_indices = list(range(len(self.pending_extracted_todos)))
            else:
                # Parse comma-separated numbers
                selected_indices = []
                parts = user_input.replace(" ", "").split(",")
                for part in parts:
                    try:
                        num = int(part)
                        # Convert to 0-indexed
                        if 1 <= num <= len(self.pending_extracted_todos):
                            selected_indices.append(num - 1)
                        else:
                            chat_log.write_error(f"Invalid number: {num}. Must be between 1 and {len(self.pending_extracted_todos)}")
                    except ValueError:
                        chat_log.write_error(f"Invalid input: '{part}'. Please enter numbers separated by commas (e.g., '1,2,3')")
                        return

            if not selected_indices:
                chat_log.write_system("No valid todos selected.")
                self.waiting_for_todo_selection = False
                self.pending_extracted_todos = None
                self.pending_extracted_priorities = None
                return

            # Create the selected todos
            chat_log.write_system(f"\n✨ Creating {len(selected_indices)} todo(s)...\n")

            created_count = 0
            for idx in sorted(selected_indices):
                todo_content = self.pending_extracted_todos[idx]
                priority = self.pending_extracted_priorities[idx]

                # Create the todo (link to note if we have a pending_note_id from /capture)
                todo = self.todo_service.create_todo(
                    content=todo_content,
                    priority=priority,
                    note_id=self.pending_note_id if hasattr(self, 'pending_note_id') and self.pending_note_id else None
                )
                created_count += 1

                priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(priority, "")
                chat_log.write_success(f"✓ Created todo #{todo.id}: {todo_content}{priority_label}")

            # Reload todos in the list
            todos = self.todo_service.list_active()
            todo_list = self.query_one(TodoListWidget)
            todo_list.update_todos(todos)

            chat_log.write_success(f"\n✅ Successfully created {created_count} todo(s)!")

        except Exception as e:
            from terminal_todos.utils.logger import log_error
            error_msg = log_error(e, "Failed to create todos", show_traceback=True)
            chat_log.write_error(f"❌ {error_msg}")
        finally:
            # Clear pending state
            self.waiting_for_todo_selection = False
            self.pending_extracted_todos = None
            self.pending_extracted_priorities = None
            self.pending_note_id = None  # Also clear note_id after selection

    async def handle_focus_selection(self, user_input: str):
        """Handle user selection of focus suggestions by number."""
        from langchain_core.messages import AIMessage, HumanMessage

        chat_log = self.query_one(ChatLogWidget)

        try:
            user_input_lower = user_input.lower().strip()

            # Parse user input
            if user_input_lower in ["none", "cancel", "no"]:
                chat_log.write_system("❌ Cancelled. No todos were added to focus.")

                # Add to conversation history so agent knows the interaction completed
                completion_msg = AIMessage(content="Focus suggestion cancelled by user.")
                self.add_to_conversation_history(completion_msg)

                self.waiting_for_focus_selection = False
                self.pending_focus_suggestions = None
                return

            if user_input_lower == "all":
                # Select all suggestions
                selected_indices = list(range(len(self.pending_focus_suggestions)))
            else:
                # Parse comma-separated numbers
                selected_indices = []
                parts = user_input.replace(" ", "").split(",")
                for part in parts:
                    try:
                        num = int(part)
                        # Convert to 0-indexed
                        if 1 <= num <= len(self.pending_focus_suggestions):
                            selected_indices.append(num - 1)
                        else:
                            chat_log.write_error(f"Invalid number: {num}. Must be between 1 and {len(self.pending_focus_suggestions)}")
                    except ValueError:
                        chat_log.write_error(f"Invalid input: '{part}'. Please enter numbers separated by commas (e.g., '1,2,3')")
                        return

            if not selected_indices:
                chat_log.write_system("No valid todos selected.")
                self.waiting_for_focus_selection = False
                self.pending_focus_suggestions = None
                return

            # Add user's selection to conversation history
            selection_msg = HumanMessage(content=f"Selected focus suggestions: {user_input}")
            self.add_to_conversation_history(selection_msg)

            # Add selected todos to focus
            chat_log.write_system(f"\n⭐ Adding {len(selected_indices)} todo(s) to focus...\n")

            added_count = 0
            for idx in sorted(selected_indices):
                todo_id = self.pending_focus_suggestions[idx]

                # Add to focus
                todo = self.todo_service.add_to_focus(todo_id)
                if todo:
                    added_count += 1
                    priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(todo.priority, "")
                    due_label = f" (due {todo.due_date.strftime('%m/%d')})" if todo.due_date else ""
                    chat_log.write_success(f"⭐ Added to focus: #{todo.id} {todo.content}{priority_label}{due_label}")
                else:
                    chat_log.write_error(f"✗ Failed to add todo #{todo_id} to focus")

            # Refresh todos
            await self.refresh_todos()

            chat_log.write_success(f"\n✅ Successfully added {added_count} todo(s) to focus!")

            # Check if focus count is getting high
            focus_count = self.todo_service.get_focus_count()
            if focus_count > 10:
                chat_log.write_system(f"💡 You now have {focus_count} focused todos. Consider keeping it to 5-10 for best focus.")

            # Add to conversation history so agent knows what was added
            # Keep history preserved so user can continue conversation with context
            summary_msg = AIMessage(content=f"Successfully added {added_count} todo(s) to the focus list based on user's selection.")
            self.add_to_conversation_history(summary_msg)

        except Exception as e:
            from terminal_todos.utils.logger import log_error
            error_msg = log_error(e, "Failed to add todos to focus", show_traceback=True)
            chat_log.write_error(f"❌ {error_msg}")

            # Add error to conversation history
            error_msg_obj = AIMessage(content=f"Failed to add todos to focus: {str(e)}")
            self.add_to_conversation_history(error_msg_obj)
        finally:
            # Clear pending state
            self.waiting_for_focus_selection = False
            self.pending_focus_suggestions = None

    async def handle_command(self, command: str):
        """
        Handle slash commands (will be expanded in Phase 8).

        Args:
            command: The command string starting with /
        """
        chat_log = self.query_one(ChatLogWidget)

        # Parse command
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        try:
            if cmd == "help":
                await self._cmd_help()
            elif cmd == "quit" or cmd == "exit":
                self._cleanup()
                self.exit()
            elif cmd == "clear":
                # Clear chat log only (not conversation history)
                chat_log.clear_log()
                chat_log.write_system("✓ Chat log cleared")
            elif cmd == "clear-history":
                # Clear conversation history and reset conversation modes
                self.clear_conversation_history()
                self.in_note_conversation = False
                chat_log.write_success("✓ Conversation history cleared - agent will start fresh")
            elif cmd == "history":
                # Show conversation history summary
                summary = self.get_conversation_summary()
                mode_info = ""
                if self.in_note_conversation:
                    mode_info = " | 📖 In note conversation mode (history preserved)"
                chat_log.write_system(f"📝 Conversation History: {summary}{mode_info}")
            elif cmd == "list":
                await self._cmd_list(args)
            elif cmd == "todo":
                await self._cmd_todo(args)
            elif cmd == "done":
                await self._cmd_done(args)
            elif cmd == "delete" or cmd == "del":
                await self._cmd_delete(args)
            elif cmd == "stats":
                await self._cmd_stats()
            elif cmd == "todo-stats":
                await self._cmd_todo_stats(args)
            elif cmd == "capture":
                await self._cmd_capture()
            elif cmd == "search":
                await self._cmd_search(args)
            elif cmd == "notes":
                await self._cmd_notes(args)
            elif cmd == "note":
                await self._cmd_view_note(args)
            elif cmd == "delnote":
                await self._cmd_delete_note(args)
            elif cmd == "copy-note":
                await self._cmd_copy_note(args)
            elif cmd == "email":
                await self._cmd_email(args)
            elif cmd == "copy-email":
                await self._cmd_copy_email(args)
            elif cmd == "list-emails":
                await self._cmd_list_emails(args)
            elif cmd == "import" or cmd == "transfer":
                await self._cmd_import()
            elif cmd == "resync":
                await self._cmd_resync()
            elif cmd == "extract-todos" or cmd == "extract":
                await self._cmd_extract_todos(args)
            elif cmd == "focus":
                await self._cmd_focus(args)
            else:
                chat_log.write_error(f"Unknown command: /{cmd}. Type /help for available commands.")
        except Exception as e:
            chat_log.write_error(f"Command failed: {e}")

    async def _cmd_help(self):
        """Show help message."""
        chat_log = self.query_one(ChatLogWidget)
        help_text = """# Available Commands

## Todos
- `/todo <text>` - Create a single todo
- `/list [open|done|all]` - List todos (default: open)
- `/done <id>` - Mark todo as done
- `/focus [add|remove|list|clear]` - Manage focus list (pin important todos to top)
- `/search <query>` - Search todos semantically
- `/stats` - Show todo statistics
- `/todo-stats [days]` - Show detailed completion stats with graphs (default: 5 days)

## Notes
- `/capture` - Enter multi-line mode to paste notes and extract todos (press **Ctrl+Enter** to submit)
- `/import` - Bulk import notes with AI categorization and metadata extraction (press **Ctrl+Enter** to submit)
- `/extract-todos <note_ids>` - Extract todos from specific notes with interactive selection (use arrow keys + space)
- `/notes [limit]` - List recent notes (default: 10)
- `/note <id>` - View full content of a specific note
- `/copy-note <id>` - Copy note to clipboard in markdown format with all metadata
- `/delnote <id>` - Delete a note
- `/resync` - Re-index all notes with updated search (includes titles, summaries, metadata)

## Email Generation
- `/email <context>` - Generate professional email from context or note reference
- `/copy-email [id]` - Copy email draft to clipboard (uses last generated if no ID)
- `/list-emails [limit]` - List recent email drafts (default: 10)

## General
- `/clear` - Clear chat log (visual only)
- `/clear-history` - Clear conversation history (agent starts fresh)
- `/history` - Show conversation history summary
- `/help` - Show this help
- `/quit` - Exit application

## Natural Language
Just type naturally (no / prefix) to chat with the AI:
- "what do I need to do today?"
- "mark the PR review as done"
- "show me todos about meetings"
- "create a todo to review the design doc"
- "suggest todos for my focus list"
- "show me my notes"
- "delete note 5"

## Keyboard Shortcuts
- `Enter` - Send message (single-line mode)
- `Ctrl+Enter` - Submit multi-line input (in capture mode)
- `Ctrl+R` - Refresh todos
- `Ctrl+L` - Clear chat
- `Ctrl+C/Q` - Quit
- `/` - Focus input (command mode)"""
        chat_log.write_assistant(help_text)

    async def _cmd_list(self, args: str):
        """List todos."""
        status = args.strip() or "open"

        if status == "open":
            todos = self.todo_service.list_active()
        elif status == "done":
            todos = self.todo_service.list_completed()
        elif status == "all":
            todos = self.todo_service.list_all()
        else:
            chat_log = self.query_one(ChatLogWidget)
            chat_log.write_error(f"Invalid status: {status}. Use open, done, or all.")
            return

        await self.refresh_todos()

        chat_log = self.query_one(ChatLogWidget)
        if not todos:
            chat_log.write_system(f"No {status} todos found")
        else:
            chat_log.write_success(f"Showing {len(todos)} {status} todo(s)")

    async def _cmd_todo(self, args: str):
        """Create a new todo."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("Usage: /todo <description>")
            return

        todo = self.todo_service.create_todo(content=args)
        chat_log.write_success(f"Created todo #{todo.id}: {todo.content}")

        await self.refresh_todos()

    async def _cmd_done(self, args: str):
        """Mark a todo as done."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("Usage: /done <todo_id>")
            return

        try:
            todo_id = int(args.strip())
            todo = self.todo_service.complete_todo(todo_id)

            if todo:
                chat_log.write_success(f"✓ Completed: {todo.content}")
                await self.refresh_todos()
            else:
                chat_log.write_error(f"Todo #{todo_id} not found")
        except ValueError:
            chat_log.write_error("Invalid todo ID. Must be a number.")

    async def _cmd_focus(self, args: str):
        """Manage the focus list."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            # Show focused todos
            focused = self.todo_service.list_focused()
            if not focused:
                chat_log.write_system("No todos in focus list. Use /focus add <id> to add one.")
            else:
                chat_log.write_success(f"⭐ Focus List ({len(focused)} items):")
                for todo in focused:
                    priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(todo.priority, "")
                    due_label = f" (due {todo.due_date.strftime('%m/%d')})" if todo.due_date else ""
                    chat_log.write_system(f"  #{todo.id}: {todo.content}{priority_label}{due_label}")
            return

        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()
        subargs = parts[1] if len(parts) > 1 else ""

        try:
            if subcmd == "add":
                if not subargs:
                    chat_log.write_error("Usage: /focus add <todo_id>")
                    return

                todo_id = int(subargs.strip())

                # Check current count
                count = self.todo_service.get_focus_count()
                if count >= 10:
                    chat_log.write_system(f"⚠️  You already have {count} focused todos. Consider removing one to maintain focus.")

                todo = self.todo_service.add_to_focus(todo_id)
                if todo:
                    chat_log.write_success(f"⭐ Added to focus: #{todo.id} {todo.content}")
                    await self.refresh_todos()
                else:
                    chat_log.write_error(f"Todo #{todo_id} not found")

            elif subcmd == "remove" or subcmd == "rm":
                if not subargs:
                    chat_log.write_error("Usage: /focus remove <todo_id>")
                    return

                todo_id = int(subargs.strip())
                todo = self.todo_service.remove_from_focus(todo_id)
                if todo:
                    chat_log.write_success(f"Removed from focus: #{todo.id} {todo.content}")
                    await self.refresh_todos()
                else:
                    chat_log.write_error(f"Todo #{todo_id} not found")

            elif subcmd == "list":
                # Same as /focus with no args
                focused = self.todo_service.list_focused()
                if not focused:
                    chat_log.write_system("No todos in focus list.")
                else:
                    chat_log.write_success(f"⭐ Focus List ({len(focused)} items):")
                    for todo in focused:
                        priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(todo.priority, "")
                        due_label = f" (due {todo.due_date.strftime('%m/%d')})" if todo.due_date else ""
                        chat_log.write_system(f"  #{todo.id}: {todo.content}{priority_label}{due_label}")

            elif subcmd == "clear":
                focused = self.todo_service.list_focused()
                if not focused:
                    chat_log.write_system("Focus list is already empty.")
                    return

                chat_log.write_system(f"Are you sure you want to clear {len(focused)} todos from focus?")
                chat_log.write_system("Type 'yes' to confirm or anything else to cancel.")
                self.pending_focus_clear = True

            elif subcmd == "suggest":
                # Use natural language to invoke the AI suggestion tool
                chat_log.write_system("🔍 Analyzing your todos to suggest focus items...")
                await self.handle_natural_language("suggest todos for my focus list")

            else:
                chat_log.write_error(f"Unknown focus command: {subcmd}")
                chat_log.write_system("""Usage:
  /focus                - Show focus list
  /focus add <id>       - Add todo to focus
  /focus remove <id>    - Remove todo from focus
  /focus list           - Show focus list
  /focus clear          - Clear all focused todos
  /focus suggest        - AI suggests todos to focus on""")

        except ValueError:
            chat_log.write_error("Invalid todo ID. Must be a number.")

    async def _cmd_delete(self, args: str):
        """Delete todos - single or bulk."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("""Usage: /delete <option>

Options:
  <id>              - Delete a single todo by ID (e.g., /delete 5)
  <id,id,...>       - Delete multiple todos by IDs (e.g., /delete 1,2,3)
  completed         - Delete all completed todos
  no-due-date       - Delete all todos without due dates
  overdue           - Delete all overdue todos

Examples:
  /delete 5
  /delete 1,2,3
  /delete 1, 2, 3
  /delete completed
  /delete no-due-date""")
            return

        args = args.strip().lower()

        # Check if args contains commas (multi-ID deletion)
        if ',' in args:
            try:
                # Parse comma-separated IDs and deduplicate
                id_strings = [s.strip() for s in args.split(',')]
                todo_ids = [int(id_str) for id_str in id_strings if id_str]
                todo_ids = list(dict.fromkeys(todo_ids))  # Deduplicate while preserving order

                if not todo_ids:
                    chat_log.write_error("No valid todo IDs provided")
                    return

                # Validate all todos exist and collect them
                todos_to_delete = []
                invalid_ids = []

                for todo_id in todo_ids:
                    todo = self.todo_service.get_todo(todo_id)
                    if todo:
                        todos_to_delete.append(todo)
                    else:
                        invalid_ids.append(todo_id)

                # Report any invalid IDs
                if invalid_ids:
                    chat_log.write_error(f"Todo(s) not found: {', '.join(f'#{id}' for id in invalid_ids)}")
                    if not todos_to_delete:
                        return
                    chat_log.write_system(f"Continuing with {len(todos_to_delete)} valid todo(s)...")

                # Show what will be deleted
                chat_log.write_system(f"⚠️  Found {len(todos_to_delete)} todo(s) to delete:")
                for i, todo in enumerate(todos_to_delete, 1):
                    status = "✓" if todo.completed else "○"
                    chat_log.write_system(f"  {i}. {status} #{todo.id}: {todo.content}")

                chat_log.write_system("")
                chat_log.write_system(f"Type 'yes' to delete all {len(todos_to_delete)} todos, or anything else to cancel.")

                # Store pending deletion
                self.pending_deletion = {
                    "type": "multiple",
                    "todo_ids": [t.id for t in todos_to_delete],
                    "count": len(todos_to_delete)
                }
                self.deletion_from_agent = False  # This is a manual command
                return

            except ValueError:
                chat_log.write_error("Invalid todo IDs. All IDs must be numbers.")
                return

        # Check if it's a numeric ID for single deletion
        try:
            todo_id = int(args)
            # Single todo deletion
            todo = self.todo_service.get_todo(todo_id)
            if not todo:
                chat_log.write_error(f"Todo #{todo_id} not found")
                return

            # Show what will be deleted
            chat_log.write_system(f"Are you sure you want to delete: #{todo_id}: {todo.content}?")
            chat_log.write_system("Type 'yes' to confirm or anything else to cancel.")

            # Store pending deletion
            self.pending_deletion = {"type": "single", "todo_id": todo_id}
            self.deletion_from_agent = False  # This is a manual command
            return

        except ValueError:
            # Not a number, must be a bulk deletion keyword
            pass

        # Handle bulk deletion keywords
        filter_map = {
            "completed": "completed",
            "no-due-date": "no_due_date",
            "noduedate": "no_due_date",
            "overdue": "overdue"
        }

        filter_type = filter_map.get(args)
        if not filter_type:
            chat_log.write_error(f"Unknown deletion option: {args}. Type /delete for usage.")
            return

        # Get todos that would be deleted
        if filter_type == "completed":
            todos = self.todo_service.list_completed()
            desc = "completed todos"
        elif filter_type == "no_due_date":
            todos = self.todo_service.list_no_due_date()
            desc = "todos without due dates"
        elif filter_type == "overdue":
            todos = self.todo_service.list_overdue()
            desc = "overdue todos"

        if not todos:
            chat_log.write_system(f"No {desc} found to delete.")
            return

        # Show preview
        chat_log.write_system(f"⚠️  Found {len(todos)} {desc} to delete:")
        for i, todo in enumerate(todos[:10], 1):
            chat_log.write_system(f"  {i}. #{todo.id}: {todo.content}")
        if len(todos) > 10:
            chat_log.write_system(f"  ... and {len(todos) - 10} more")

        chat_log.write_system("")
        chat_log.write_system(f"Type 'yes' to delete all {len(todos)} todos, or anything else to cancel.")

        # Store pending deletion
        self.pending_deletion = {"type": "bulk", "filter": filter_type, "count": len(todos)}
        self.deletion_from_agent = False  # This is a manual command

    async def _cmd_stats(self):
        """Show todo statistics."""
        chat_log = self.query_one(ChatLogWidget)
        counts = self.todo_service.get_todo_count()

        stats_text = f"""[bold]📊 Todo Statistics:[/bold]
• Active: {counts['active']}
• Completed: {counts['completed']}
• Total: {counts['total']}"""

        chat_log.write(stats_text)

    async def _cmd_todo_stats(self, args: str):
        """Show detailed completion statistics with graphs."""
        from rich.text import Text
        from rich.table import Table
        from rich.panel import Panel

        chat_log = self.query_one(ChatLogWidget)

        # Parse days argument (default to 5)
        days = 5
        if args.strip():
            try:
                days = int(args.strip())
                if days < 1 or days > 90:
                    chat_log.write_error("Days must be between 1 and 90")
                    return
            except ValueError:
                chat_log.write_error("Invalid number of days. Usage: /todo-stats [days]")
                return

        try:
            # Get stats from service
            stats = self.todo_service.get_completion_stats(days)

            # Create header
            chat_log.write("")
            header = Text()
            header.append("═" * 70, style="bold cyan")
            chat_log.write(header)

            title = Text()
            title.append("📊 ", style="bold cyan")
            title.append("TODO COMPLETION STATS", style="bold white")
            title.append(f" - Last {days} Days", style="cyan")
            chat_log.write(title)

            date_range = Text()
            date_range.append(f"   {stats['start_date'].strftime('%b %d')} → {stats['end_date'].strftime('%b %d, %Y')}", style="dim cyan")
            chat_log.write(date_range)

            header2 = Text()
            header2.append("═" * 70, style="bold cyan")
            chat_log.write(header2)
            chat_log.write("")

            # Summary metrics
            summary = Table.grid(padding=(0, 2))
            summary.add_column(style="bold yellow", justify="right")
            summary.add_column(style="white")
            summary.add_column(style="bold green", justify="right")
            summary.add_column(style="white")

            summary.add_row(
                "✓ Completed:", f"{stats['totals']['completed']}",
                "📝 Created:", f"{stats['totals']['created']}"
            )
            summary.add_row(
                "📈 Avg/Day:", f"{stats['avg_per_day']:.1f}",
                "🎯 Rate:", f"{stats['completion_rate']:.1f}%"
            )
            summary.add_row(
                "⚡ Active:", f"{stats['current_active']}",
                "⚠️  Overdue:", f"{stats['current_overdue']}"
            )

            chat_log.write(summary)
            chat_log.write("")

            # Priority breakdown
            if stats['totals']['completed'] > 0:
                priority_title = Text()
                priority_title.append("🎯 Completed by Priority:", style="bold cyan")
                chat_log.write(priority_title)
                chat_log.write("")

                # Create horizontal bar chart for priorities
                max_priority = max(stats['totals']['by_priority'].values()) if stats['totals']['by_priority'].values() else 1

                priority_labels = {0: "Normal", 1: "High", 2: "Urgent"}
                priority_colors = {0: "white", 1: "yellow", 2: "red"}
                priority_emojis = {0: "○", 1: "⚡", 2: "🔥"}

                for priority in [2, 1, 0]:  # Show urgent first
                    count = stats['totals']['by_priority'].get(priority, 0)
                    if count > 0:
                        bar_width = int((count / max_priority) * 30) if max_priority > 0 else 0
                        bar = "█" * bar_width

                        bar_text = Text()
                        bar_text.append(f"  {priority_emojis[priority]} ", style="bold")
                        bar_text.append(f"{priority_labels[priority]:8}", style="dim")
                        bar_text.append(bar, style=priority_colors[priority])
                        bar_text.append(f" {count}", style=f"bold {priority_colors[priority]}")
                        chat_log.write(bar_text)

                chat_log.write("")

            # Daily completion chart
            chart_title = Text()
            chart_title.append("📅 Daily Completion Trend:", style="bold cyan")
            chat_log.write(chart_title)
            chat_log.write("")

            # Find max for scaling
            max_completed = max(day['completed'] for day in stats['daily_stats']) if stats['daily_stats'] else 1
            max_completed = max(max_completed, 1)  # At least 1 for scaling

            # Create daily bars
            for day_stats in stats['daily_stats']:
                day_date = day_stats['date']
                completed = day_stats['completed']
                created = day_stats['created']

                # Format date
                is_today = day_date == stats['end_date']
                day_label = "Today" if is_today else day_date.strftime("%a %m/%d")

                # Create bar
                bar_width = int((completed / max_completed) * 35) if max_completed > 0 else 0
                bar = "█" * bar_width

                # Color based on performance
                if completed >= 5:
                    bar_color = "green"
                elif completed >= 3:
                    bar_color = "yellow"
                elif completed > 0:
                    bar_color = "white"
                else:
                    bar_color = "dim"

                day_text = Text()
                day_text.append(f"  {day_label:9} ", style="bold" if is_today else "dim")
                day_text.append(bar if bar else "░", style=bar_color)
                day_text.append(f" {completed}", style=f"bold {bar_color}")

                # Add created count if different
                if created > 0 and created != completed:
                    day_text.append(f" ({created} created)", style="dim")

                chat_log.write(day_text)

            # Footer
            chat_log.write("")
            footer = Text()
            footer.append("═" * 70, style="bold cyan")
            chat_log.write(footer)
            chat_log.write("")

        except Exception as e:
            from terminal_todos.utils.logger import log_error
            error_msg = log_error(e, "Failed to generate stats", show_traceback=True)
            chat_log.write_error(f"❌ {error_msg}")

    async def _cmd_capture(self):
        """Capture mode - extract todos from pasted notes."""
        chat_log = self.query_one(ChatLogWidget)
        input_bar = self.query_one(InputBarWidget)

        chat_log.write_assistant("""# 📝 Capture Mode

Paste your meeting notes, Slack messages, or any text in the multi-line input below.

**When done:** Press **Ctrl+Enter** to submit

**Note:** Timestamps and your name will be automatically filtered out during extraction.

**Example:**
```
10:30 AM Ed Robinson
Let's schedule the design review

10:31 AM Jane Smith
Sounds good, I'll send the invite

Ed Robinson 10:32 AM
Also need to follow up on PR #123
```

Just paste and press **Ctrl+Enter** - the system will extract the action items!
""")

        # Clear any previous capture state
        self.capture_mode = False
        self.capture_buffer = []
        self.pending_note_id = None

        # Switch to multi-line input
        input_bar.switch_to_multiline()

        # Set capture mode flag
        self.capture_mode = True

        chat_log.write_system("📋 Multi-line input active. Paste your notes and press Ctrl+Enter to submit.")

    async def _cmd_search(self, args: str):
        """Search todos semantically."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("Usage: /search <query>")
            return

        chat_log.write_system(f"Searching for: {args}")

        try:
            results = self.todo_service.search_todos(args, k=10)

            if not results:
                chat_log.write_system(f"No todos found matching: {args}")
                return

            chat_log.write(f"[bold]Found {len(results)} todo(s):[/bold]")
            for result in results:
                todo_id = result["todo_id"]
                content = result["content"]
                relevance = result.get("relevance", 0)
                completed = result["metadata"].get("completed", False)

                status_icon = "✓" if completed else "○"
                color = "dim" if completed else "white"
                chat_log.write(
                    f"[{color}]{status_icon} #{todo_id}: {content} (relevance: {relevance:.2f})[/{color}]"
                )

        except Exception as e:
            chat_log.write_error(f"Search failed: {e}")

    async def _cmd_notes(self, args: str):
        """List recent notes."""
        chat_log = self.query_one(ChatLogWidget)

        # Parse limit
        limit = 10
        if args.strip():
            try:
                limit = int(args.strip())
            except ValueError:
                chat_log.write_error("Invalid limit. Must be a number.")
                return

        try:
            notes = self.note_service.list_all(limit=limit)

            if not notes:
                chat_log.write_system("No notes found")
                return

            chat_log.write(f"**Recent Notes ({len(notes)}):**\n")
            for note in notes:
                title_display = note.title or "Untitled"
                preview = note.content[:60] + "..." if len(note.content) > 60 else note.content
                created = note.created_at.strftime("%Y-%m-%d %H:%M")
                chat_log.write_assistant(f"📝 **#{note.id}**: {title_display}\n   *{created}*\n   {preview}\n")

        except Exception as e:
            chat_log.write_error(f"Failed to list notes: {e}")

    async def _cmd_view_note(self, args: str):
        """View the full content of a specific note."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("Usage: /note <id>")
            return

        try:
            note_id = int(args.strip())
            note = self.note_service.get_note(note_id)

            if not note:
                chat_log.write_error(f"Note #{note_id} not found")
                return

            title = note.title or "Untitled"
            created = note.created_at.strftime("%Y-%m-%d %H:%M")

            note_text = f"""# 📝 Note #{note.id}: {title}

*Created: {created}*

---

{note.content}"""
            chat_log.write_assistant(note_text)

        except ValueError:
            chat_log.write_error("Invalid note ID. Must be a number.")
        except Exception as e:
            chat_log.write_error(f"Failed to view note: {e}")

    async def _cmd_delete_note(self, args: str):
        """Delete a note."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("Usage: /delnote <id>")
            return

        try:
            note_id = int(args.strip())
            note = self.note_service.get_note(note_id)

            if not note:
                chat_log.write_error(f"Note #{note_id} not found")
                return

            title = note.title or "Untitled"

            # Delete the note
            deleted = self.note_service.delete_note(note_id)

            if deleted:
                chat_log.write_success(f"✗ Deleted note #{note_id}: {title}")
            else:
                chat_log.write_error(f"Failed to delete note #{note_id}")

        except ValueError:
            chat_log.write_error("Invalid note ID. Must be a number.")
        except Exception as e:
            chat_log.write_error(f"Failed to delete note: {e}")

    async def _cmd_copy_note(self, args: str):
        """Copy a note to the clipboard in markdown format."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("Usage: /copy-note <id>")
            return

        try:
            note_id = int(args.strip())
            note = self.note_service.get_note(note_id)

            if not note:
                chat_log.write_error(f"Note #{note_id} not found")
                return

            # Format note as markdown with all metadata
            title = note.title or "Untitled"
            created = note.created_at.strftime("%Y-%m-%d %H:%M")

            # Build markdown output
            markdown_parts = []
            markdown_parts.append(f"# {title}")
            markdown_parts.append("")
            markdown_parts.append(f"**Created:** {created}")

            # Add category if present
            if note.category:
                markdown_parts.append(f"**Category:** {note.category}")

            # Add tags if present
            if hasattr(note, 'get_tags'):
                tags = note.get_tags()
                if tags:
                    markdown_parts.append(f"**Tags:** {', '.join(tags)}")

            # Add keywords if present
            if hasattr(note, 'get_keywords'):
                keywords = note.get_keywords()
                if keywords:
                    markdown_parts.append(f"**Keywords:** {', '.join(keywords)}")

            # Add topics if present
            if hasattr(note, 'get_topics'):
                topics = note.get_topics()
                if topics:
                    markdown_parts.append(f"**Topics:** {', '.join(topics)}")

            # Add summary if present
            if hasattr(note, 'summary') and note.summary:
                markdown_parts.append("")
                markdown_parts.append(f"**Summary:** {note.summary}")

            # Add content
            markdown_parts.append("")
            markdown_parts.append("---")
            markdown_parts.append("")
            markdown_parts.append(note.content)

            # Join all parts
            markdown_output = "\n".join(markdown_parts)

            # Copy to clipboard
            try:
                import pyperclip
                pyperclip.copy(markdown_output)

                # Show confirmation with preview
                preview = note.content[:100] + "..." if len(note.content) > 100 else note.content
                chat_log.write_success(f"✓ Copied note #{note_id} to clipboard")
                chat_log.write_assistant(f"**Title:** {title}")
                chat_log.write_assistant(f"**Preview:** {preview}")

            except Exception as clipboard_error:
                # Handle clipboard-specific errors
                chat_log.write_error(f"Failed to copy to clipboard: {str(clipboard_error)}")
                chat_log.write_assistant("The note content is shown below:")
                chat_log.write_assistant(f"```markdown\n{markdown_output}\n```")

        except ValueError:
            chat_log.write_error("Invalid note ID. Must be a number.")
        except Exception as e:
            chat_log.write_error(f"Failed to copy note: {str(e)}")

    async def _cmd_email(self, args: str):
        """Generate an email from context or notes."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("Please provide context for the email")
            chat_log.write_system("Usage: /email [context or note reference]")
            return

        # Check if args reference a note ID
        if args.startswith("#") or args.isdigit():
            note_id = args.lstrip("#")
            try:
                note_id = int(note_id)
                # Get note content
                note = self.note_service.get_note(note_id)
                if not note:
                    chat_log.write_error(f"Note #{note_id} not found")
                    return

                context = f"Note: {note.title}\n\n{note.content}"
                if note.summary:
                    context += f"\n\nSummary: {note.summary}"
            except ValueError:
                chat_log.write_error("Invalid note ID")
                return
        else:
            context = args

        # Send to agent for email generation
        chat_log.write_system("🔄 Generating email from context...")
        await self.send_agent_message(
            f"Generate a professional email based on this context: {context}"
        )

    async def _cmd_copy_email(self, args: str):
        """Copy an email draft to clipboard."""
        from terminal_todos.core.email_service import get_email_service
        import pyperclip

        chat_log = self.query_one(ChatLogWidget)

        # Determine email ID
        if args:
            try:
                email_id = int(args.lstrip("#"))
            except ValueError:
                chat_log.write_error("Invalid email ID")
                return
        elif self.last_generated_email_id:
            email_id = self.last_generated_email_id
        else:
            chat_log.write_error(
                "No email specified. Use /copy-email <id> or generate an email first"
            )
            return

        # Get email
        service = get_email_service()
        try:
            email = service.get_email(email_id)

            if not email:
                chat_log.write_error(f"Email #{email_id} not found")
                return

            # Format for clipboard
            email_text = f"Subject: {email.subject}\n\n{email.body}"

            # Copy to clipboard
            try:
                pyperclip.copy(email_text)
                chat_log.write_success(f"✓ Copied email #{email_id} to clipboard")
            except Exception as e:
                chat_log.write_error(f"Failed to copy to clipboard: {str(e)}")
                chat_log.write_system("Email content:")
                chat_log.write_assistant(f"```\n{email_text}\n```")
        finally:
            service.close()

    async def _cmd_list_emails(self, args: str):
        """List recent email drafts."""
        chat_log = self.query_one(ChatLogWidget)

        # Parse limit if provided
        limit = 10
        if args:
            try:
                limit = int(args)
            except ValueError:
                pass

        # Send to agent
        await self.send_agent_message(f"List my {limit} most recent email drafts")

    async def _cmd_resync(self):
        """Re-sync all notes to vector store with updated embeddings."""
        chat_log = self.query_one(ChatLogWidget)

        chat_log.write_assistant("🔄 Re-syncing all notes to vector store...")
        chat_log.write_assistant("This will update search embeddings to include titles, summaries, and metadata.")

        try:
            # Import sync service
            from terminal_todos.core.sync_service import SyncService

            sync_service = SyncService()

            # Run full notes sync
            success_count, error_count = sync_service.full_sync_notes()

            # Close sync service
            sync_service.close()

            if error_count == 0:
                chat_log.write_success(f"✓ Successfully re-synced {success_count} note(s)")
                chat_log.write_assistant("All notes are now searchable by title, summary, and content!")
            else:
                chat_log.write_warning(f"⚠️  Re-synced {success_count} note(s) with {error_count} error(s)")

        except Exception as e:
            from terminal_todos.utils.logger import log_error
            log_error(e, "Failed to re-sync notes", show_traceback=True)
            chat_log.write_error(f"Failed to re-sync notes: {e}")

    async def _cmd_import(self):
        """Import mode - bulk import notes with metadata extraction."""
        chat_log = self.query_one(ChatLogWidget)
        input_bar = self.query_one(InputBarWidget)

        chat_log.write_assistant("""# 📦 Knowledge Import Mode

Paste multiple notes below. You can separate notes using:
- `---` (triple dash)
- `###` (triple hash)
- Three blank lines

**When done:** Press **Ctrl+Enter** to submit

**What happens:**
1. AI will analyze each note
2. Extract: title, summary, category, keywords, topics
3. Show preview with all metadata
4. You confirm before final import

**Example:**
```
Meeting Notes - Sprint Planning
Discussed Q1 roadmap and priorities
...

---

Technical Debt Review
Identified 3 critical issues...
```

Just paste and press **Ctrl+Enter** - the AI will organize everything!
""")

        # Clear any previous state
        self.import_mode = False
        self.import_buffer = []
        self.pending_import = None

        # Switch to multi-line input
        input_bar.switch_to_multiline()

        # Set import mode flag
        self.import_mode = True

        chat_log.write_system("📋 Multi-line input active. Paste your notes and press Ctrl+Enter to submit.")

    async def _process_import(self):
        """Process bulk note import and extract metadata."""
        from rich.text import Text
        from terminal_todos.utils.logger import log_debug, log_error, log_info

        chat_log = self.query_one(ChatLogWidget)
        input_bar = self.query_one(InputBarWidget)

        # Combine captured lines
        bulk_content = "\n".join(self.import_buffer)

        log_debug("Starting import process", {"content_length": len(bulk_content)})

        # Validation
        if not bulk_content or len(bulk_content.strip()) < 10:
            chat_log.write_system("📋 No content captured. Import cancelled.")
            self.import_mode = False
            self.import_buffer = []
            return

        try:
            # Set loading state
            chat_log.set_loading_state(True)
            chat_log.write_loading("Analyzing bulk content", step=1)
            await asyncio.sleep(0.2)

            log_info("Initializing knowledge extractor")

            # Initialize extractor if not exists
            if not hasattr(self, 'knowledge_extractor') or self.knowledge_extractor is None:
                from terminal_todos.extraction.knowledge_extractor import KnowledgeExtractor
                self.knowledge_extractor = KnowledgeExtractor()

            log_info("Extracting metadata from bulk content")

            # Extract metadata
            extraction = self.knowledge_extractor.extract_bulk(bulk_content, auto_split=True)

            log_debug("Extraction complete", {"note_count": extraction.get_note_count()})

            if not extraction.has_notes():
                chat_log.set_loading_state(False)
                chat_log.write_system("ℹ️  No notes could be extracted from the content.")
                return

            chat_log.set_loading_state(False)

            # Show preview
            separator = Text()
            separator.append("━" * 60, style="bold cyan")
            chat_log.write(separator)

            header = Text()
            header.append("📦 REVIEW EXTRACTED NOTES", style="bold cyan")
            header.append(f" ({extraction.get_note_count()} found)", style="cyan")
            chat_log.write(header)

            separator2 = Text()
            separator2.append("━" * 60, style="bold cyan")
            chat_log.write(separator2)

            # Show each note preview
            for i, note in enumerate(extraction.notes, 1):
                # Category with color
                category_color = {
                    "technical": "blue",
                    "meeting": "green",
                    "documentation": "cyan",
                    "project": "magenta",
                    "brainstorm": "yellow",
                    "reference": "white",
                    "decision": "red",
                    "action-items": "yellow",
                }.get(note.category, "white")

                note_text = Text()
                note_text.append(f"{i}. ", style="dim")
                note_text.append(f"[{note.category.upper()}] ", style=f"bold {category_color}")
                note_text.append(note.title, style="bold white")
                chat_log.write(note_text)

                # Summary
                summary_text = Text()
                summary_text.append("   ", style="dim")
                summary_text.append(note.summary, style="dim white")
                chat_log.write(summary_text)

                # Keywords
                if note.keywords:
                    kw_text = Text()
                    kw_text.append("   🏷️  ", style="dim")
                    kw_text.append(", ".join(note.keywords), style="cyan")
                    chat_log.write(kw_text)

                # Topics
                if note.topics:
                    topic_text = Text()
                    topic_text.append("   📌 ", style="dim")
                    topic_text.append(", ".join(note.topics), style="magenta")
                    chat_log.write(topic_text)

                chat_log.write("")  # Blank line

            # Store pending import
            self.pending_import = extraction

            # Ask for tags first
            separator3 = Text()
            separator3.append("━" * 60, style="dim cyan")
            chat_log.write(separator3)

            tags_prompt = Text()
            tags_prompt.append("🏷️  TAG THESE NOTES\n", style="bold cyan")
            tags_prompt.append("\nWhat accounts, clients, or projects are these notes for?\n", style="cyan")
            tags_prompt.append("Enter tags separated by commas (e.g., ", style="dim")
            tags_prompt.append("Client-A, Q1-2026, ProjectBeta", style="italic white")
            tags_prompt.append(")\n", style="dim")
            tags_prompt.append("Or press ", style="dim")
            tags_prompt.append("Enter", style="bold white")
            tags_prompt.append(" to skip.", style="dim")
            chat_log.write(tags_prompt)

            # Set state to wait for tags
            self.waiting_for_import_tags = True
            chat_log.border_title = "Chat & Output - ⏳ Waiting for Tags"

        except Exception as e:
            chat_log.set_loading_state(False)
            from terminal_todos.utils.logger import log_error
            error_msg = log_error(e, "Import processing failed", show_traceback=True)
            chat_log.write_error(f"❌ {error_msg}")

        finally:
            self.import_mode = False
            self.import_buffer = []

    async def _create_pending_import(self):
        """Create notes from pending import after confirmation."""
        from terminal_todos.utils.logger import log_debug, log_error, log_info

        chat_log = self.query_one(ChatLogWidget)

        if not self.pending_import:
            chat_log.write_error("No pending import to create.")
            return

        try:
            chat_log.set_loading_state(True)
            created_count = 0

            log_info(f"Creating pending import with {self.pending_import.get_note_count()} notes")

            chat_log.write_loading(f"Importing {self.pending_import.get_note_count()} notes", step=1)
            await asyncio.sleep(0.2)

            # Prepare notes for bulk creation
            notes_data = []
            for i, extracted_note in enumerate(self.pending_import.notes, 1):
                log_debug(f"Preparing note {i}", {
                    "title": extracted_note.title,
                    "category": extracted_note.category,
                    "has_keywords": bool(extracted_note.keywords),
                    "has_topics": bool(extracted_note.topics),
                    "has_tags": bool(self.pending_import_tags)
                })

                notes_data.append({
                    "content": extracted_note.content,
                    "title": extracted_note.title,
                    "category": extracted_note.category,
                    "keywords": extracted_note.keywords,
                    "topics": extracted_note.topics,
                    "summary": extracted_note.summary,
                    "tags": self.pending_import_tags if self.pending_import_tags else [],
                })

            log_info(f"Calling create_notes_bulk with {len(notes_data)} notes")

            # Bulk create
            created_notes = self.note_service.create_notes_bulk(notes_data)
            created_count = len(created_notes)

            log_info(f"Successfully created {created_count} notes")

            # Show success for each
            for note in created_notes:
                category_display = f"[{note.category.upper()}] " if note.category else ""
                tags_display = f" 🏷️ {', '.join(note.get_tags())}" if note.get_tags() else ""
                chat_log.write_success(f"✓ Imported #{note.id}: {category_display}{note.title}{tags_display}")

            # Clear loading
            chat_log.set_loading_state(False)
            self.pending_import = None
            self.pending_import_tags = None

            if self.pending_import_tags:
                chat_log.write_success(f"✅ Successfully imported {created_count} note(s) with tags: {', '.join(self.pending_import_tags)}!")
            else:
                chat_log.write_success(f"✅ Successfully imported {created_count} note(s)!")

            # Purge import confirmation context
            self.purge_confirmation_context()

        except Exception as e:
            chat_log.set_loading_state(False)
            self.pending_import = None
            self.pending_import_tags = None
            from terminal_todos.utils.logger import log_error
            error_msg = log_error(e, "Note creation failed", show_traceback=True)
            chat_log.write_error(f"❌ {error_msg}")

    async def _launch_interactive_extraction(self, note_ids: list[int]):
        """Launch todo extraction and show numbered list for user selection."""
        chat_log = self.query_one(ChatLogWidget)

        try:
            # Set loading state
            chat_log.set_loading_state(True)
            chat_log.write_loading(f"Extracting todos from {len(note_ids)} note(s)", step=1)
            await asyncio.sleep(0.2)

            # Fetch notes
            notes = []
            for note_id in note_ids:
                note = self.note_service.get_note(note_id)
                if note:
                    notes.append(note)
                else:
                    chat_log.write_error(f"Note #{note_id} not found")

            if not notes:
                chat_log.set_loading_state(False)
                chat_log.write_error("No valid notes found to extract from.")
                return

            # Initialize extractor
            from terminal_todos.extraction.todo_extractor import TodoExtractor
            extractor = TodoExtractor()

            # Combine note content
            combined_content = "\n\n---\n\n".join([
                f"Note: {note.title or 'Untitled'}\n{note.content}"
                for note in notes
            ])

            chat_log.write_loading("Analyzing notes with AI", step=2)
            await asyncio.sleep(0.2)

            # Extract todos
            extraction = extractor.extract(combined_content)

            chat_log.set_loading_state(False)

            if not extraction.todos:
                chat_log.write_system("No actionable todos found in the notes.")
                return

            # Format extracted todos as strings
            extracted_todo_strings = [
                f"{todo.content}"
                for todo in extraction.todos
            ]

            # Store for later creation
            self.pending_extracted_todos = extracted_todo_strings
            self.pending_extracted_priorities = [todo.priority for todo in extraction.todos]
            self.waiting_for_todo_selection = True

            # Write numbered list to chat
            chat_log.write_system(f"\n📋 Found {len(extracted_todo_strings)} actionable todo(s):\n")

            for i, todo in enumerate(extracted_todo_strings):
                priority_label = ""
                if self.pending_extracted_priorities[i] == 1:
                    priority_label = " [HIGH]"
                elif self.pending_extracted_priorities[i] == 2:
                    priority_label = " [URGENT]"

                chat_log.write_system(f"  {i+1}. {todo}{priority_label}")

            chat_log.write_system(f"\nWhich todos would you like to add? (e.g., '1,2,3' or 'all' or 'none')")

        except Exception as e:
            chat_log.set_loading_state(False)
            from terminal_todos.utils.logger import log_error
            error_msg = log_error(e, "Todo extraction failed", show_traceback=True)
            chat_log.write_error(f"❌ {error_msg}")

    async def _cmd_extract_todos(self, args: str):
        """Extract todos from notes with interactive selection (command version)."""
        chat_log = self.query_one(ChatLogWidget)

        if not args:
            chat_log.write_error("Usage: /extract-todos <note_ids>\nExample: /extract-todos 45 67 102")
            return

        # Parse note IDs
        try:
            note_ids = [int(id_str.strip()) for id_str in args.split() if id_str.strip().isdigit()]
        except ValueError:
            chat_log.write_error("Invalid note IDs. Provide space-separated numbers.")
            return

        if not note_ids:
            chat_log.write_error("No valid note IDs provided.")
            return

        # Launch interactive extraction
        await self._launch_interactive_extraction(note_ids)

    async def handle_natural_language(self, message: str):
        """
        Handle natural language input by sending to the agent.

        Args:
            message: User's natural language message
        """
        chat_log = self.query_one(ChatLogWidget)
        input_bar = self.query_one(InputBarWidget)

        # Check if we're waiting for deletion confirmation
        if self.pending_deletion is not None:
            response = message.strip().lower()

            if response in ['yes', 'y']:
                # User confirmed - proceed with deletion
                deletion_info = self.pending_deletion

                if deletion_info["type"] == "single":
                    # Delete single todo
                    todo_id = deletion_info["todo_id"]
                    if self.todo_service.delete_todo(todo_id):
                        chat_log.write_success(f"✗ Deleted todo #{todo_id}")
                        await self.refresh_todos()
                    else:
                        chat_log.write_error(f"Failed to delete todo #{todo_id}")

                elif deletion_info["type"] == "bulk":
                    # Delete bulk todos
                    filter_type = deletion_info["filter"]
                    count = deletion_info["count"]

                    chat_log.write_system(f"⚙️  Deleting {count} todos...")

                    # Get the todos again and delete them
                    if filter_type == "completed":
                        todos = self.todo_service.list_completed()
                    elif filter_type == "no_due_date":
                        todos = self.todo_service.list_no_due_date()
                    elif filter_type == "overdue":
                        todos = self.todo_service.list_overdue()
                    else:
                        todos = []

                    deleted_count = 0
                    for todo in todos:
                        if self.todo_service.delete_todo(todo.id):
                            deleted_count += 1

                    chat_log.write_success(f"✗ Successfully deleted {deleted_count} todo(s)")
                    await self.refresh_todos()

                elif deletion_info["type"] == "multiple":
                    # Delete multiple specific todos
                    todo_ids = deletion_info["todo_ids"]
                    count = deletion_info["count"]

                    chat_log.write_system(f"⚙️  Deleting {count} todo(s)...")

                    deleted_count = 0
                    failed_ids = []

                    for todo_id in todo_ids:
                        if self.todo_service.delete_todo(todo_id):
                            deleted_count += 1
                        else:
                            failed_ids.append(todo_id)

                    if failed_ids:
                        chat_log.write_error(f"Failed to delete: {', '.join(f'#{id}' for id in failed_ids)}")

                    if deleted_count > 0:
                        chat_log.write_success(f"✗ Successfully deleted {deleted_count} todo(s)")

                    await self.refresh_todos()

                # Clear pending deletion
                self.pending_deletion = None

                # Purge confirmation context (removes last 2 turns: request + confirmation)
                self.purge_confirmation_context()

                # Only clear ALL history if deletion was manual (not from ongoing agent conversation)
                if not self.deletion_from_agent:
                    self.clear_conversation_history()
                else:
                    # For agent-initiated deletions, just clean tool execution details
                    # This preserves conversational context while removing tool noise
                    self.clean_tool_execution_from_history()

                # Reset agent tracking flag
                self.deletion_from_agent = False

                return

            elif response in ['no', 'n']:
                # User cancelled
                chat_log.write_system("❌ Deletion cancelled.")
                self.pending_deletion = None

                # Purge confirmation context
                self.purge_confirmation_context()

                # Only clear ALL history if deletion was manual (not from ongoing agent conversation)
                if not self.deletion_from_agent:
                    self.clear_conversation_history()
                else:
                    # For agent-initiated deletions, just clean tool execution details
                    self.clean_tool_execution_from_history()

                # Reset agent tracking flag
                self.deletion_from_agent = False

                return
            else:
                # Invalid response
                chat_log.write_error("⚠️ Invalid response. Please type 'yes' or 'no'.")
                return

        # Check if we're waiting for import tags
        if self.waiting_for_import_tags:
            # Parse tags from input (comma-separated)
            tags_input = message.strip()

            if tags_input:
                # Parse comma-separated tags
                tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                self.pending_import_tags = tags
                chat_log.write_system(f"✓ Tags set: {', '.join(tags)}")
            else:
                # User skipped tags
                self.pending_import_tags = []
                chat_log.write_system("⊘ No tags added (skipped)")

            # Now ask for final confirmation
            from rich.text import Text
            chat_log.write("")
            confirm_text = Text()
            confirm_text.append("📝 Review and confirm:\n", style="bold yellow")
            confirm_text.append(f"  • {self.pending_import.get_note_count()} notes ready to import\n", style="white")
            if self.pending_import_tags:
                confirm_text.append(f"  • Tags: {', '.join(self.pending_import_tags)}\n", style="cyan")
            confirm_text.append("\nType ", style="yellow")
            confirm_text.append("'yes'", style="bold green")
            confirm_text.append(" or ", style="yellow")
            confirm_text.append("'y'", style="bold green")
            confirm_text.append(" to import, or ", style="yellow")
            confirm_text.append("'no'", style="bold red")
            confirm_text.append(" / ", style="yellow")
            confirm_text.append("'n'", style="bold red")
            confirm_text.append(" to cancel.", style="yellow")
            chat_log.write(confirm_text)

            self.waiting_for_import_tags = False
            chat_log.border_title = "Chat & Output - ⏳ Awaiting Confirmation"
            return

        # Check if we're waiting for import confirmation
        if self.pending_import is not None:
            response = message.strip().lower()

            if response in ['yes', 'y']:
                # User confirmed - import the notes
                chat_log.border_title = "Chat & Output"
                chat_log.write_success("✓ Importing notes...")
                await self._create_pending_import()

                # Clear all history after complete interaction
                self.clear_conversation_history()

                return
            elif response in ['no', 'n']:
                # User cancelled
                chat_log.border_title = "Chat & Output"
                chat_log.write_system("❌ Import cancelled. No notes were created.")
                self.pending_import = None
                self.pending_import_tags = None

                # Purge import confirmation context
                self.purge_confirmation_context()

                # Clear all history after complete interaction
                self.clear_conversation_history()

                return
            else:
                # Invalid response
                chat_log.write_error("⚠️ Invalid response. Please type 'yes' or 'no'.")
                return

        # Check if we're in capture mode
        if self.capture_mode:
            # Check for END command or empty message (user pressed enter on empty line)
            if message.strip().upper() == "END" or not message.strip():
                # Process captured notes
                await self._process_capture()
                # Switch back to single-line input
                input_bar.switch_to_singleline()
                return
            else:
                # Add to capture buffer
                self.capture_buffer.append(message)
                # Don't log each line to keep chat clean
                return

        try:
            from terminal_todos.utils.logger import log_error, log_info, log_debug

            log_info(f"handle_natural_language called with: {message[:100]}")

            # Set loading state
            log_debug("Setting loading state")
            chat_log.set_loading_state(True)

            # Show execution header
            log_debug("Writing execution header")
            chat_log.write_execution_header("AGENT EXECUTION TRACE")
            await asyncio.sleep(0.15)

            # Call agent with streaming for progress updates
            log_info("Calling agent with progress")
            result = await self._call_agent_with_progress(message, chat_log)
            log_info("Agent call completed")

            # Clear loading state
            log_debug("Clearing loading state")
            chat_log.set_loading_state(False)

            # Get the agent's response
            if result and "messages" in result:
                log_debug("Extracting agent response from result")
                last_message = result["messages"][-1]
                response_text = last_message.content
                log_info(f"Agent response: {response_text[:100]}...")

                # Check for special interactive extraction marker
                if "__EXTRACT_TODOS_INTERACTIVE__|" in response_text:
                    log_debug("Detected interactive todo extraction marker")

                    # Extract note IDs from marker
                    marker_start = response_text.find("__EXTRACT_TODOS_INTERACTIVE__|")
                    marker_end = response_text.find("__", marker_start + len("__EXTRACT_TODOS_INTERACTIVE__|"))

                    if marker_end != -1:
                        note_ids_str = response_text[marker_start + len("__EXTRACT_TODOS_INTERACTIVE__|"):marker_end]
                        note_ids = [int(id.strip()) for id in note_ids_str.split(",") if id.strip().isdigit()]

                        # Remove the marker from response
                        clean_response = response_text[:marker_start] + response_text[marker_end+2:]
                        clean_response = clean_response.strip()

                        # Display cleaned response
                        if clean_response:
                            chat_log.write_assistant(clean_response)

                        # Launch interactive extraction
                        chat_log.write_system("🔄 Launching interactive todo extraction...")
                        await self._launch_interactive_extraction(note_ids)
                    else:
                        # Malformed marker, just display response
                        chat_log.write_assistant(response_text)

                # Check for focus suggestions marker
                elif "__FOCUS_SUGGESTIONS__|" in response_text:
                    log_debug("Detected focus suggestions marker")

                    # Extract todo IDs from marker
                    marker_start = response_text.find("__FOCUS_SUGGESTIONS__|")
                    marker_end = response_text.find("__", marker_start + len("__FOCUS_SUGGESTIONS__|"))

                    if marker_end != -1:
                        todo_ids_str = response_text[marker_start + len("__FOCUS_SUGGESTIONS__|"):marker_end]
                        todo_ids = [int(id.strip()) for id in todo_ids_str.split(",") if id.strip().isdigit()]

                        # Remove the marker from response
                        clean_response = response_text[:marker_start] + response_text[marker_end+2:]
                        clean_response = clean_response.strip()

                        # Display cleaned response
                        if clean_response:
                            chat_log.write_assistant(clean_response)

                        # Set up for interactive selection
                        self.waiting_for_focus_selection = True
                        self.pending_focus_suggestions = todo_ids
                    else:
                        # Malformed marker, just display response
                        chat_log.write_assistant(response_text)
                else:
                    # Check for email generation
                    if "Generated Email Draft" in response_text and "(ID:" in response_text:
                        log_debug("Detected generated email - extracting ID for auto-copy")

                        # Extract email ID from response
                        import re
                        match = re.search(r'\(ID:\s*(\d+)\)', response_text)
                        if match:
                            email_id = int(match.group(1))
                            self.last_generated_email_id = email_id
                            log_debug(f"Extracted email ID: {email_id}")

                            # Auto-copy to clipboard
                            try:
                                from terminal_todos.core.email_service import get_email_service
                                import pyperclip

                                service = get_email_service()
                                try:
                                    email = service.get_email(email_id)
                                    if email:
                                        email_text = f"Subject: {email.subject}\n\n{email.body}"
                                        pyperclip.copy(email_text)
                                        log_debug("Email auto-copied to clipboard")
                                except Exception as clipboard_error:
                                    log_debug(f"Failed to auto-copy email: {str(clipboard_error)}")
                                finally:
                                    service.close()
                            except Exception as e:
                                log_debug(f"Error during email auto-copy: {str(e)}")

                    # Normal response, display as-is
                    log_debug("Writing agent response to chat")
                    chat_log.write_assistant(response_text)

                # Refresh todos in case they changed
                log_debug("Refreshing todos")
                await self.refresh_todos()
            else:
                log_error(Exception("No result from agent"), "Agent returned empty result", show_traceback=False)

        except Exception as e:
            from terminal_todos.utils.logger import log_error

            # Clear loading state on error
            chat_log.set_loading_state(False)

            # Log comprehensive error info
            log_error(e, "Error in handle_natural_language", show_traceback=True)

            # Better error display
            error_msg = str(e)
            # Only show the first part of the error to avoid clutter
            if "Details:" in error_msg:
                main_error = error_msg.split("Details:")[0]
                chat_log.write_error(f"Agent error: {main_error}")
            else:
                chat_log.write_error(f"Agent error: {error_msg}")

        finally:
            # Clear conversation history after each complete interaction
            # BUT preserve it if:
            # 1. Waiting for user selection (focus or todo extraction)
            # 2. In a note conversation (discussing notes)
            if (not self.waiting_for_focus_selection and
                not self.waiting_for_todo_selection and
                not self.in_note_conversation):
                log_debug("Clearing conversation history after interaction")
                self.clear_conversation_history()
            else:
                if self.waiting_for_focus_selection or self.waiting_for_todo_selection:
                    log_debug("Preserving conversation history - waiting for user selection")
                if self.in_note_conversation:
                    log_debug("Preserving conversation history - in note conversation")

    async def _call_agent_with_progress(self, message: str, chat_log) -> dict:
        """
        Call the LangGraph agent with progress indicators and conversation history.

        Args:
            message: User message
            chat_log: ChatLogWidget for progress updates

        Returns:
            Agent result dictionary
        """
        from langchain_core.messages import ToolMessage
        from terminal_todos.utils.logger import log_debug, log_info

        # Create message
        human_message = HumanMessage(content=message)

        # Add to conversation history
        self.add_to_conversation_history(human_message)

        log_info(f"Calling agent (streaming) with {len(self.conversation_history)} messages in history")

        # Tool name to friendly description mapping
        tool_descriptions = {
            "get_current_date": "📅 Checking today's date",
            "create_todo": "📝 Creating todo",
            "update_todo": "✏️ Updating todo",
            "complete_todo": "✅ Marking todo complete",
            "uncomplete_todo": "🔄 Reopening todo",
            "delete_todo": "🗑️ Deleting todo",
            "list_todos": "📋 Listing todos",
            "list_todos_by_date": "📅 Finding todos by date",
            "search_todos": "🔍 Searching todos",
            "find_todos_to_complete": "🔍 Finding todos to complete",
            "find_todos_to_update": "🔍 Finding todos to update",
            "create_note": "📝 Creating note",
            "list_notes": "📋 Listing notes",
            "search_notes": "🔍 Searching notes",
            "get_note": "📖 Retrieving note",
            "delete_note": "🗑️ Deleting note",
            "get_todo_stats": "📊 Getting statistics",
        }

        try:
            # Stream the agent execution to show progress
            result = None
            seen_tools = set()
            tool_count = 0
            needs_refresh = False
            step_number = 0
            execution_start_shown = False

            # Tools that modify todos and require a refresh
            data_modifying_tools = {
                "create_todo", "update_todo", "complete_todo",
                "uncomplete_todo", "delete_todo"
            }

            # Tools that indicate note-related conversations
            note_related_tools = {
                "search_notes", "get_note", "get_notes_for_analysis",
                "list_notes", "list_notes_by_date", "list_imported_notes",
                "search_notes_by_category", "search_notes_by_tags"
            }

            # Tools that indicate user has shifted away from notes
            todo_related_tools = {
                "create_todo", "update_todo", "complete_todo", "uncomplete_todo",
                "delete_todo", "list_todos", "search_todos", "find_todos_to_complete",
                "find_todos_to_update", "list_todos_by_date", "add_to_focus",
                "remove_from_focus", "list_focused_todos", "suggest_focus_todos"
            }

            # Track if we used any tools (to detect topic shifts)
            used_note_tools = False
            used_todo_tools = False

            # Analyze the request to show initial thinking
            request_lower = message.lower()
            if "complete" in request_lower and "everything" in request_lower:
                chat_log.write_thinking("User wants to complete multiple todos - preparing to process all matching tasks")
            elif "update" in request_lower:
                chat_log.write_thinking("User wants to update a todo - need to find and modify the right item")
            elif "due" in request_lower or "friday" in request_lower or "week" in request_lower:
                chat_log.write_thinking("Request involves dates - will need current date for calculations")
            elif "create" in request_lower or "add" in request_lower:
                chat_log.write_thinking("User wants to create new todo(s)")
            else:
                chat_log.write_thinking("Processing user request")

            await asyncio.sleep(0.15)

            # Stream with full conversation history
            for chunk in self.agent_graph.stream({"messages": self.conversation_history}):
                # Check if this chunk contains tool calls
                if "agent" in chunk:
                    agent_messages = chunk["agent"]["messages"]
                    for msg in agent_messages:
                        # Check for tool calls
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            # Show thinking before tool calls
                            if not execution_start_shown:
                                chat_log.write_thinking("Analyzing request and planning actions")
                                await asyncio.sleep(0.1)
                                execution_start_shown = True

                            for tool_call in msg.tool_calls:
                                tool_name = tool_call.get("name", "")
                                tool_args = tool_call.get("args", {})

                                # Only show each tool once per request
                                if tool_name not in seen_tools:
                                    seen_tools.add(tool_name)
                                    tool_count += 1
                                    step_number += 1

                                    # Show thinking about the tool with context
                                    action_desc = {
                                        "get_current_date": "Need to check today's date for date calculations",
                                        "find_todos_to_update": "Searching for matching todos to update",
                                        "find_todos_to_complete": "Finding todos to mark as complete",
                                        "update_todo": f"Updating todo #{tool_args.get('todo_id', '?')} with new information",
                                        "complete_todo": f"Marking todo #{tool_args.get('todo_id', '?')} as complete",
                                        "create_todo": f"Creating new todo: '{tool_args.get('content', '...')[:40]}'",
                                        "delete_todo": f"Deleting todo #{tool_args.get('todo_id', '?')}",
                                        "list_todos": "Retrieving todo list",
                                        "list_todos_by_date": f"Finding todos for: {tool_args.get('date_string', 'date range')}",
                                        "search_todos": f"Searching for: '{tool_args.get('query', '...')}'",
                                    }.get(tool_name, f"Executing {tool_name}")

                                    chat_log.write_thinking(action_desc)
                                    await asyncio.sleep(0.1)

                                    # Show tool execution with arguments
                                    chat_log.write_tool_execution(tool_name, args=tool_args)
                                    await asyncio.sleep(0.1)

                                    # Mark that we need to refresh if this tool modifies data
                                    if tool_name in data_modifying_tools:
                                        needs_refresh = True

                                    # Track if deletion came from agent
                                    if tool_name == "delete_todo":
                                        self.deletion_from_agent = True

                                    # Track tool usage for conversation mode detection
                                    if tool_name in note_related_tools:
                                        used_note_tools = True
                                        log_debug(f"Detected note-related tool: {tool_name}")

                                    if tool_name in todo_related_tools:
                                        used_todo_tools = True
                                        log_debug(f"Detected todo-related tool: {tool_name}")

                                    # Force UI refresh
                                    self.refresh()

                # Check if tools were executed (and refresh todos if they were)
                if "tools" in chunk:
                    # Get tool results
                    if "messages" in chunk["tools"]:
                        tool_messages = chunk["tools"]["messages"]
                        for tool_msg in tool_messages:
                            if hasattr(tool_msg, "content"):
                                # Show tool result
                                result_content = tool_msg.content
                                tool_msg_name = getattr(tool_msg, "name", "unknown")
                                chat_log.write_tool_execution(tool_msg_name, result=result_content)
                                await asyncio.sleep(0.1)

                    # Refresh if needed
                    if needs_refresh:
                        chat_log.write_execution_step("Refreshing UI with updated data")
                        await asyncio.sleep(0.1)
                        await self.refresh_todos()
                        needs_refresh = False

                # Store final result
                result = chunk

            # Show thinking before final response
            if tool_count > 0:
                chat_log.write_thinking("Formulating response based on results")
                await asyncio.sleep(0.1)

                # Do a final refresh to catch any missed updates
                await self.refresh_todos()

                # Create execution summary
                summary_parts = []
                if "update_todo" in seen_tools:
                    summary_parts.append("✓ Updated todo(s)")
                if "complete_todo" in seen_tools:
                    summary_parts.append("✓ Completed todo(s)")
                if "create_todo" in seen_tools:
                    summary_parts.append("✓ Created todo(s)")
                if "delete_todo" in seen_tools:
                    summary_parts.append("✓ Deleted todo(s)")

                summary = " | ".join(summary_parts) if summary_parts else f"Executed {tool_count} operation(s)"

                # Show completion with separator
                chat_log.write_execution_step("Execution complete", details=summary)
            else:
                # Simple query without tools
                chat_log.write_thinking("No tools needed - providing direct response")
                await asyncio.sleep(0.1)

            # Write closing separator
            from rich.text import Text
            separator = Text()
            separator.append("─" * 60, style="dim blue")
            chat_log.write(separator)

            await asyncio.sleep(0.1)

            # Return the final result
            if result:
                # Extract assistant's response and add to history
                if "messages" in result:
                    messages = result["messages"]
                    if messages:
                        last_message = messages[-1]
                        # Only add if it's not already in history
                        if last_message not in self.conversation_history:
                            # Strip tool_calls before adding to prevent re-execution
                            msg_type = last_message.__class__.__name__
                            if msg_type == "AIMessage" and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                                from langchain_core.messages import AIMessage
                                clean_message = AIMessage(content=last_message.content)
                                self.add_to_conversation_history(clean_message)
                                log_debug(f"Added AI response to history (stripped tool_calls): {clean_message.content[:100]}...")
                            else:
                                self.add_to_conversation_history(last_message)
                                log_debug(f"Added AI response to history from streaming: {last_message.content[:100]}...")

                # Update conversation mode based on tool usage
                if used_note_tools:
                    # User is discussing notes - enter/stay in note conversation mode
                    self.in_note_conversation = True
                    log_debug("Entering note conversation mode - history will be preserved")
                elif used_todo_tools and self.in_note_conversation:
                    # User has shifted from notes to todos - exit note conversation mode
                    self.in_note_conversation = False
                    log_debug("Exiting note conversation mode - user shifted to todos")

                # Clean up tool execution messages to prevent re-execution
                # This removes ToolMessages but keeps conversational context (AIMessage text)
                self.clean_tool_execution_from_history()

                # The last chunk should have the complete state
                if "agent" in result:
                    return result["agent"]
                else:
                    return result
            else:
                # Fallback to invoke if streaming doesn't work
                fallback_result = self.agent_graph.invoke({"messages": self.conversation_history})

                # Add AI response to history from fallback
                if fallback_result and "messages" in fallback_result:
                    messages = fallback_result["messages"]
                    if messages:
                        last_message = messages[-1]
                        if last_message not in self.conversation_history:
                            # Strip tool_calls before adding to prevent re-execution
                            msg_type = last_message.__class__.__name__
                            if msg_type == "AIMessage" and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                                from langchain_core.messages import AIMessage
                                clean_message = AIMessage(content=last_message.content)
                                self.add_to_conversation_history(clean_message)
                            else:
                                self.add_to_conversation_history(last_message)

                # Clean up tool execution messages
                # This removes ToolMessages but keeps conversational context (AIMessage text)
                self.clean_tool_execution_from_history()

                return fallback_result

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise Exception(f"Agent error: {str(e)}\nDetails:\n{error_details}")

    async def _call_agent(self, message: str) -> dict:
        """
        Call the LangGraph agent with full conversation history.

        Args:
            message: User message

        Returns:
            Agent result dictionary
        """
        from terminal_todos.utils.logger import log_debug, log_info

        # Create message
        human_message = HumanMessage(content=message)

        # Add to conversation history
        self.add_to_conversation_history(human_message)

        log_info(f"Calling agent with {len(self.conversation_history)} messages in history")

        try:
            # Call agent with full conversation history
            result = self.agent_graph.invoke({"messages": self.conversation_history})

            # Extract assistant's response and add to history
            if result and "messages" in result:
                # Get the last message (should be the AI's response)
                messages = result["messages"]
                if messages:
                    last_message = messages[-1]
                    # Only add if it's not already in history (avoid duplicates)
                    if last_message not in self.conversation_history:
                        # Strip tool_calls before adding to prevent re-execution
                        msg_type = last_message.__class__.__name__
                        if msg_type == "AIMessage" and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                            from langchain_core.messages import AIMessage
                            clean_message = AIMessage(content=last_message.content)
                            self.add_to_conversation_history(clean_message)
                            log_debug(f"Added AI response to history (stripped tool_calls): {clean_message.content[:100]}...")
                        else:
                            self.add_to_conversation_history(last_message)
                            log_debug(f"Added AI response to history: {last_message.content[:100]}...")

            # Clean up tool execution messages to prevent re-execution
            # This removes ToolMessages but keeps conversational context (AIMessage text)
            self.clean_tool_execution_from_history()

            return result
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise Exception(f"Agent error: {str(e)}\nDetails:\n{error_details}")

    # Removed _create_pending_todos - now using handle_todo_selection for all extractions

    async def _process_capture(self):
        """Process captured notes and extract todos."""
        from rich.text import Text

        chat_log = self.query_one(ChatLogWidget)
        input_bar = self.query_one(InputBarWidget)

        # Combine captured lines
        note_content = "\n".join(self.capture_buffer)

        # Comprehensive validation - check for empty or whitespace-only content
        if not note_content or not note_content.strip():
            chat_log.write_system("📋 No content was captured. Capture mode cancelled.")
            self.capture_mode = False
            self.capture_buffer = []
            return

        # Remove "END" markers that might have been typed
        clean_content = note_content.strip()
        if clean_content.upper() == "END":
            chat_log.write_system("📋 No content was captured (only END marker found). Capture mode cancelled.")
            self.capture_mode = False
            self.capture_buffer = []
            return

        # Check minimum content length (at least 10 characters of actual content)
        if len(clean_content) < 10:
            chat_log.write_system(f"📋 Captured content too short ({len(clean_content)} characters). Minimum 10 characters required. Capture cancelled.")
            self.capture_mode = False
            self.capture_buffer = []
            return

        # Show what was captured for transparency
        lines = clean_content.split('\n')
        line_count = len(lines)
        chat_log.write_system(f"📋 Captured {line_count} line(s) of content ({len(clean_content)} characters)")

        try:
            # Set loading state
            chat_log.set_loading_state(True)
            chat_log.write_loading("Analyzing captured content", step=1)
            await asyncio.sleep(0.2)

            # Extract todos using AI
            extraction = self.extractor.extract(clean_content)

            chat_log.write_loading("Saving note", step=2)
            await asyncio.sleep(0.2)

            # Save the note
            note = self.note_service.create_note(
                content=note_content,
                title=extraction.title,
                note_type=extraction.note_type
            )

            chat_log.write_success(f"✓ Saved note #{note.id}: **{extraction.title}**")

            # Show extracted todos for review
            if extraction.has_todos():
                chat_log.set_loading_state(False)

                # Write separator and header
                separator = Text()
                separator.append("━" * 60, style="bold cyan")
                chat_log.write(separator)

                header = Text()
                header.append("📋 REVIEW EXTRACTED TODOS", style="bold cyan")
                header.append(f" ({extraction.get_todo_count()} found)", style="cyan")
                chat_log.write(header)

                separator2 = Text()
                separator2.append("━" * 60, style="bold cyan")
                chat_log.write(separator2)

                # Show each extracted todo for review
                for i, extracted_todo in enumerate(extraction.todos, 1):
                    priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(
                        extracted_todo.priority, ""
                    )
                    priority_color = {0: "white", 1: "yellow", 2: "red"}.get(extracted_todo.priority, "white")

                    todo_text = Text()
                    todo_text.append(f"{i}. ", style="dim")
                    todo_text.append(extracted_todo.content, style=priority_color)
                    if priority_label:
                        todo_text.append(priority_label, style=f"bold {priority_color}")
                    chat_log.write(todo_text)

                # Store extracted todos for selection (same as /extract-todos)
                self.pending_extracted_todos = [todo.content for todo in extraction.todos]
                self.pending_extracted_priorities = [todo.priority for todo in extraction.todos]
                self.pending_note_id = note.id  # Store note ID for linking todos
                self.waiting_for_todo_selection = True

                # Ask for selection
                chat_log.write_system("")
                confirm_text = Text()
                confirm_text.append("📝 Which todos would you like to add?\n", style="bold yellow")
                confirm_text.append("Type ", style="yellow")
                confirm_text.append("'all'", style="bold green")
                confirm_text.append(" to add all, ", style="yellow")
                confirm_text.append("'1,2,3'", style="bold cyan")
                confirm_text.append(" for specific ones, or ", style="yellow")
                confirm_text.append("'none'", style="bold red")
                confirm_text.append(" to cancel.", style="yellow")
                chat_log.write(confirm_text)

                # Write closing separator
                separator3 = Text()
                separator3.append("━" * 60, style="bold cyan")
                chat_log.write(separator3)

                # Update border to show we're waiting for selection
                chat_log.border_title = "Chat & Output - ⏳ Awaiting Selection"

            else:
                chat_log.set_loading_state(False)
                chat_log.write_system("ℹ️  No action items found in the notes")

        except Exception as e:
            chat_log.set_loading_state(False)
            import traceback
            error_details = traceback.format_exc()
            chat_log.write_error(f"❌ Extraction failed: {str(e)}")
            # Log full error for debugging
            print(f"Extraction error details:\n{error_details}")

        finally:
            # Reset capture mode
            self.capture_mode = False
            self.capture_buffer = []

    async def refresh_todos(self):
        """Refresh the todo list with fresh data from database."""
        try:
            # Close and recreate the service to ensure fresh data
            self.todo_service.close()
            from terminal_todos.core.todo_service import TodoService
            self.todo_service = TodoService()

            # Get fresh todos from database
            todos = self.todo_service.list_all()

            # Update the widget
            todo_list = self.query_one(TodoListWidget)
            todo_list.update_todos(todos)

            # Force UI refresh
            todo_list.refresh()
            self.refresh()

        except Exception as e:
            chat_log = self.query_one(ChatLogWidget)
            chat_log.write_error(f"Failed to refresh todos: {e}")

    def action_command_mode(self):
        """Focus the input for command mode."""
        input_bar = self.query_one(InputBarWidget)
        input_bar.focus_input()
        input_widget = input_bar.get_input()
        if not input_widget.value.startswith("/"):
            input_widget.value = "/"

    async def action_clear_chat(self):
        """Clear the chat log."""
        chat_log = self.query_one(ChatLogWidget)
        chat_log.clear_log()

    async def action_refresh_todos(self):
        """Refresh the todo list."""
        await self.refresh_todos()
        chat_log = self.query_one(ChatLogWidget)
        chat_log.write_system("Todos refreshed")

    async def action_submit_multiline(self):
        """Submit multi-line input (Ctrl+Enter)."""
        input_bar = self.query_one(InputBarWidget)

        # Only works in multi-line mode
        if not input_bar.multiline_mode:
            return

        user_input = input_bar.get_text().strip()

        # Get chat log
        chat_log = self.query_one(ChatLogWidget)

        # In capture mode, this submits the captured content
        if self.capture_mode:
            # Validate that there's actual content
            if not user_input:
                chat_log.write_system("📋 No content entered. Capture mode cancelled.")
                input_bar.switch_to_singleline()
                self.capture_mode = False
                self.capture_buffer = []
                return

            # Check if user only typed "END"
            if user_input.upper() == "END":
                chat_log.write_system("📋 No content captured (only END marker found). Capture mode cancelled.")
                input_bar.switch_to_singleline()
                self.capture_mode = False
                self.capture_buffer = []
                return

            # Check minimum length
            if len(user_input) < 10:
                chat_log.write_system(f"📋 Content too short ({len(user_input)} characters). Minimum 10 characters required. Capture cancelled.")
                input_bar.switch_to_singleline()
                self.capture_mode = False
                self.capture_buffer = []
                return

            # Show what was captured
            lines = user_input.split('\n')
            line_count = len(lines)

            # Display preview of captured content
            preview = "\n".join(lines[:5])  # Show first 5 lines
            if line_count > 5:
                preview += f"\n... ({line_count - 5} more lines)"

            chat_log.write_user(f"**Captured {line_count} lines:**\n```\n{preview}\n```", use_markdown=True)

            # Clear input
            input_bar.clear_input()

            # Split by newlines and add to buffer
            self.capture_buffer.extend(lines)
            await self._process_capture()

            # Switch back to single-line
            input_bar.switch_to_singleline()
        # In import mode, this submits the bulk content
        elif self.import_mode:
            # Validate that there's actual content
            if not user_input:
                chat_log.write_system("📋 No content entered. Import mode cancelled.")
                input_bar.switch_to_singleline()
                self.import_mode = False
                self.import_buffer = []
                return

            # Check minimum length
            if len(user_input) < 10:
                chat_log.write_system(f"📋 Content too short ({len(user_input)} characters). Minimum 10 characters required. Import cancelled.")
                input_bar.switch_to_singleline()
                self.import_mode = False
                self.import_buffer = []
                return

            # Show what was captured
            lines = user_input.split('\n')
            line_count = len(lines)

            # Display preview of captured content
            preview = "\n".join(lines[:5])  # Show first 5 lines
            if line_count > 5:
                preview += f"\n... ({line_count - 5} more lines)"

            chat_log.write_user(f"**Captured {line_count} lines for import:**\n```\n{preview}\n```", use_markdown=True)

            # Clear input
            input_bar.clear_input()

            # Split by newlines and add to buffer
            self.import_buffer.extend(lines)
            await self._process_import()

            # Switch back to single-line
            input_bar.switch_to_singleline()
        else:
            # Normal multi-line message (shouldn't normally happen, but handle it)
            chat_log.write_user(user_input)
            input_bar.clear_input()
            await self.handle_natural_language(user_input)

    def action_quit(self):
        """Quit the application with cleanup."""
        self._cleanup()
        self.exit()

    def _cleanup(self):
        """Clean up services before exit."""
        try:
            # Close services to prevent tqdm cleanup errors
            if self.todo_service:
                self.todo_service.close()
            if self.note_service:
                self.note_service.close()
        except Exception:
            # Ignore cleanup errors
            pass


def run_app():
    """Run the TUI application."""
    app = TodosApp()
    app.run()
