"""Chat log widget for the right pane."""

from textual.widgets import RichLog
from textual.worker import Worker, WorkerState
from datetime import datetime
from rich.text import Text
from rich.markdown import Markdown
from rich.console import Group
import asyncio


class ChatLogWidget(RichLog):
    """Widget for displaying chat messages and command output."""

    def __init__(self, **kwargs):
        super().__init__(markup=True, wrap=True, **kwargs)
        self.border_title = "Chat & Output"
        self.can_focus = False
        self.auto_scroll = True
        self.highlight = True
        self._loading_worker = None
        self._loading_count = 0

    def write_user(self, message: str, use_markdown: bool = False):
        """Write a user message to the chat log."""
        timestamp = datetime.now().strftime("%H:%M")

        if use_markdown:
            # Create header with timestamp
            header = Text()
            header.append(f"[{timestamp}] You: ", style="bold cyan")

            # Render message as markdown
            markdown = Markdown(message)

            # Group header and markdown content
            group = Group(header, markdown)
            self.write(group)
        else:
            # Plain text (default)
            text = Text()
            text.append(f"[{timestamp}] You: ", style="bold cyan")
            text.append(message)
            self.write(text)

    def write_assistant(self, message: str):
        """Write an assistant message to the chat log with markdown support."""
        timestamp = datetime.now().strftime("%H:%M")

        # Create header with timestamp
        header = Text()
        header.append(f"[{timestamp}] Assistant: ", style="bold green")

        # Render message as markdown
        markdown = Markdown(message)

        # Group header and markdown content
        group = Group(header, markdown)
        self.write(group)

    def write_system(self, message: str):
        """Write a system message to the chat log."""
        timestamp = datetime.now().strftime("%H:%M")
        text = Text()
        text.append(f"[{timestamp}] System: ", style="dim")
        text.append(message, style="dim")
        self.write(text)

    def write_error(self, message: str):
        """Write an error message to the chat log."""
        timestamp = datetime.now().strftime("%H:%M")
        text = Text()
        text.append(f"[{timestamp}] Error: ", style="bold red")
        text.append(message, style="red")
        self.write(text)

    def write_success(self, message: str):
        """Write a success message to the chat log."""
        timestamp = datetime.now().strftime("%H:%M")
        text = Text()
        text.append(f"[{timestamp}] ✓ ", style="bold green")
        text.append(message)
        self.write(text)

    def write_command_result(self, command: str, result: str):
        """Write the result of a command execution."""
        cmd_text = Text()
        cmd_text.append(f"> {command}", style="dim")
        self.write(cmd_text)
        self.write(result)

    def clear_log(self):
        """Clear the chat log."""
        self.clear()
        self.write_system("Chat log cleared")

    def write_loading(self, message: str, step: int = 0, total: int = 0):
        """Write a loading status message with visual indicator."""
        timestamp = datetime.now().strftime("%H:%M")

        # Create animated dots based on step
        dots = "." * ((step % 3) + 1)

        text = Text()
        text.append(f"[{timestamp}] ", style="dim")

        # Progress indicator if we have step info
        if total > 0:
            text.append(f"[{step}/{total}] ", style="bold cyan")

        text.append("⚙️  ", style="bold blue")
        text.append(message, style="bold blue")
        text.append(f"{dots}", style="bold blue")

        self.write(text)

    def set_loading_state(self, is_loading: bool):
        """Update border title to show loading state."""
        if is_loading:
            self.border_title = "Chat & Output - ⚙️  Processing..."
        else:
            self.border_title = "Chat & Output"

    def write_thinking(self, message: str, substep: str = None):
        """Write an agent thinking/reasoning message with special formatting."""
        timestamp = datetime.now().strftime("%H:%M")

        text = Text()
        text.append(f"[{timestamp}] ", style="dim")
        text.append("💭 ", style="magenta")
        text.append("Agent: ", style="bold magenta")
        text.append(message, style="italic magenta")

        if substep:
            text.append(f"\n    → {substep}", style="dim magenta")

        self.write(text)

    def write_tool_execution(self, tool_name: str, args: dict = None, result: str = None):
        """Write a tool execution message showing inputs and outputs."""
        timestamp = datetime.now().strftime("%H:%M")

        text = Text()
        text.append(f"[{timestamp}] ", style="dim")
        text.append("🔧 ", style="cyan")
        text.append(f"Tool: {tool_name}", style="bold cyan")

        # Show arguments if provided
        if args:
            args_str = ", ".join([f"{k}={repr(v)[:50]}" for k, v in args.items() if k != "self"])
            if args_str:
                text.append(f"\n    ▸ Input: {args_str}", style="dim cyan")

        # Show result preview if provided
        if result:
            # Truncate long results
            result_preview = result[:100] + "..." if len(result) > 100 else result
            # Remove newlines for preview
            result_preview = result_preview.replace("\n", " ")
            text.append(f"\n    ◂ Output: {result_preview}", style="dim green")

        self.write(text)

    def write_execution_step(self, step_name: str, details: str = None):
        """Write an execution step in a structured format."""
        timestamp = datetime.now().strftime("%H:%M")

        text = Text()
        text.append(f"[{timestamp}] ", style="dim")
        text.append("▶ ", style="yellow")
        text.append(step_name, style="bold yellow")

        if details:
            text.append(f"\n    {details}", style="dim yellow")

        self.write(text)

    def write_execution_header(self, message: str):
        """Write an execution header with separator."""
        text = Text()
        text.append("─" * 60, style="dim blue")
        self.write(text)

        timestamp = datetime.now().strftime("%H:%M")
        header = Text()
        header.append(f"[{timestamp}] ", style="dim")
        header.append("🤖 ", style="bold blue")
        header.append(message, style="bold blue")
        self.write(header)

        text2 = Text()
        text2.append("─" * 60, style="dim blue")
        self.write(text2)
