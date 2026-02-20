"""LangGraph tools for the agent."""

from datetime import datetime
from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

try:
    import dateparser
    HAS_DATEPARSER = True
except ImportError:
    HAS_DATEPARSER = False

from terminal_todos.core.note_service import NoteService
from terminal_todos.core.todo_service import TodoService


# Pydantic schemas for structured output
class EmailDraft(BaseModel):
    """Schema for generated email draft."""

    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content with proper formatting")
    recipient: str = Field(description="Intended recipient name or placeholder")
    template_type: str = Field(
        description="Type of email: 'follow_up', 'enablement', 'custom'"
    )


# Global service instances (will be initialized in graph)
_todo_service: Optional[TodoService] = None
_note_service: Optional[NoteService] = None


def init_tools(todo_service: TodoService, note_service: NoteService):
    """Initialize global service instances for tools."""
    global _todo_service, _note_service
    _todo_service = todo_service
    _note_service = note_service


def get_todo_service() -> TodoService:
    """
    Get the todo service instance.

    Creates a new instance each time to avoid thread-safety issues with database sessions.
    """
    # Always create fresh instance to avoid file descriptor issues across threads
    return TodoService()


def get_note_service() -> NoteService:
    """
    Get the note service instance.

    Creates a new instance each time to avoid thread-safety issues with database sessions.
    """
    # Always create fresh instance to avoid file descriptor issues across threads
    return NoteService()


@tool
def create_todo(content: str, priority: int = 0, due_date: Optional[str] = None) -> str:
    """
    Create a new todo item.

    ⚠️ IMPORTANT: Only call this tool if the user EXPLICITLY requests to create a todo in their CURRENT message.
    DO NOT call this if they just said "thanks", "ok", or are acknowledging a previous action.

    Only set priority or due_date if the user EXPLICITLY mentions them.
    By default, create todos WITHOUT priority or due dates - the user can add them later.

    Args:
        content: The todo description/task
        priority: Priority level - ONLY set if user explicitly says "high priority", "urgent", etc.
                  0=normal (default), 1=high, 2=urgent
        due_date: Due date - ONLY set if user explicitly provides a date like "by friday", "next week", etc.
                  Accepts ISO format (YYYY-MM-DD) or natural language. Leave None by default.

    Returns:
        Confirmation message with the todo ID
    """
    service = get_todo_service()

    try:
        # Parse due date if provided
        parsed_due_date = None
        if due_date:
            if HAS_DATEPARSER:
                try:
                    # Try dateparser for natural language with future preference
                    parsed_due_date = dateparser.parse(due_date, settings={'PREFER_DATES_FROM': 'future'})
                except:
                    pass

            if not parsed_due_date:
                try:
                    # Try ISO format
                    parsed_due_date = datetime.fromisoformat(due_date)
                except:
                    pass

            # Normalize to midnight for consistency
            if parsed_due_date:
                parsed_due_date = datetime(parsed_due_date.year, parsed_due_date.month, parsed_due_date.day, 0, 0, 0)

        todo = service.create_todo(content=content, priority=priority, due_date=parsed_due_date)

        priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}
        due_label = f" due {parsed_due_date.strftime('%Y-%m-%d')}" if parsed_due_date else ""
        return f"✓ Created todo #{todo.id}: {content}{priority_label.get(priority, '')}{due_label}"
    finally:
        # Clean up service to close database connections
        try:
            service.close()
        except:
            pass


@tool
def list_todos(status: str = "active") -> str:
    """
    List todos by status.

    Args:
        status: Filter by status - "active", "completed", or "all"

    Returns:
        Formatted list of todos
    """
    service = get_todo_service()

    if status == "active":
        todos = service.list_active()
        title = "Active Todos"
    elif status == "completed":
        todos = service.list_completed()
        title = "Completed Todos"
    else:
        todos = service.list_all()
        title = "All Todos"

    if not todos:
        return f"No {status} todos found."

    lines = [f"{title} ({len(todos)}):"]
    for todo in todos:
        status_icon = "✓" if todo.completed else "○"
        priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(todo.priority, "")
        lines.append(f"{status_icon} #{todo.id}: {todo.content}{priority_label}")

    return "\n".join(lines)


@tool
def search_todos(query: str, limit: int = 10) -> str:
    """
    Search todos semantically.

    Args:
        query: Search query
        limit: Maximum number of results

    Returns:
        Formatted search results
    """
    service = get_todo_service()
    results = service.search_todos(query, k=limit, completed=None)

    if not results:
        return f"No todos found matching: {query}"

    lines = [f"Found {len(results)} todo(s) matching '{query}':"]
    for result in results:
        todo_id = result["todo_id"]
        content = result["content"]
        relevance = result.get("relevance", 0)
        completed = result["metadata"].get("completed", False)

        status_icon = "✓" if completed else "○"
        lines.append(f"{status_icon} #{todo_id}: {content} (relevance: {relevance:.2f})")

    return "\n".join(lines)


@tool
def complete_todo(todo_id: int) -> str:
    """
    Mark a todo as completed.

    ⚠️ IMPORTANT: Only call this tool if the user EXPLICITLY requests to complete/mark done in their CURRENT message.
    DO NOT call this if they just said "thanks", "ok", or are acknowledging a previous completion.

    Args:
        todo_id: The ID of the todo to complete

    Returns:
        Confirmation message
    """
    service = get_todo_service()

    try:
        todo = service.complete_todo(todo_id)

        if not todo:
            return f"❌ Todo #{todo_id} not found"

        return f"✓ Marked todo #{todo_id} as complete: {todo.content}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def uncomplete_todo(todo_id: int) -> str:
    """
    Mark a todo as not completed (reopen it).

    Args:
        todo_id: The ID of the todo to reopen

    Returns:
        Confirmation message
    """
    service = get_todo_service()
    todo = service.uncomplete_todo(todo_id)

    if not todo:
        return f"❌ Todo #{todo_id} not found"

    return f"○ Reopened todo #{todo_id}: {todo.content}"


@tool
def update_todo(
    todo_id: int,
    content: Optional[str] = None,
    priority: Optional[int] = None,
    due_date: Optional[str] = None
) -> str:
    """
    Update a todo's properties.

    ⚠️ IMPORTANT: Only call this tool if the user EXPLICITLY requests to update in their CURRENT message.
    DO NOT call this if they just said "thanks", "ok", or are acknowledging a previous update.

    Args:
        todo_id: The ID of the todo to update
        content: New content/description (optional)
        priority: New priority level 0=normal, 1=high, 2=urgent (optional)
        due_date: New due date in ISO format or natural language (optional)

    Returns:
        Confirmation message
    """
    service = get_todo_service()

    try:
        # Get the todo first
        todo = service.get_todo(todo_id)
        if not todo:
            return f"❌ Todo #{todo_id} not found"

        updates = []

        # Update content
        if content is not None:
            todo.content = content
            service.session.commit()
            updates.append(f"content to '{content}'")

        # Update priority
        if priority is not None:
            todo.priority = priority
            service.session.commit()
            priority_label = {0: "normal", 1: "high", 2: "urgent"}.get(priority, "normal")
            updates.append(f"priority to {priority_label}")

        # Update due date
        if due_date is not None:
            parsed_due_date = None

            if HAS_DATEPARSER:
                try:
                    # Try dateparser for natural language with future preference
                    parsed_due_date = dateparser.parse(due_date, settings={'PREFER_DATES_FROM': 'future'})
                except:
                    pass

            if not parsed_due_date:
                try:
                    # Try ISO format
                    parsed_due_date = datetime.fromisoformat(due_date)
                except:
                    pass

            if parsed_due_date:
                # Normalize to midnight for consistency
                parsed_due_date = datetime(parsed_due_date.year, parsed_due_date.month, parsed_due_date.day, 0, 0, 0)
                todo.due_date = parsed_due_date
                service.session.commit()
                updates.append(f"due date to {parsed_due_date.strftime('%Y-%m-%d')}")
            else:
                return f"❌ Could not parse due date '{due_date}'. Try ISO format (YYYY-MM-DD) or natural language like 'friday' or 'next week'."

        if updates:
            # Sync to vector store
            service.sync_service.sync_todo(todo_id)

            update_str = ", ".join(updates)
            return f"✓ Updated todo #{todo_id}: Changed {update_str}"
        else:
            return f"⚠️ No updates specified for todo #{todo_id}"

    except Exception as e:
        try:
            service.session.rollback()
        except:
            pass
        return f"❌ Failed to update todo #{todo_id}: {str(e)}"
    finally:
        # Clean up service to close database connections
        try:
            service.close()
        except:
            pass


@tool
def find_todos_to_update(description: str) -> str:
    """
    Find todos by description to update. Use this when user wants to update/modify a todo.

    Args:
        description: Description of the todo to update

    Returns:
        Matching todos with IDs. If user already specified what to update, proceed directly to update_todo.
    """
    service = get_todo_service()

    try:
        results = service.search_todos(description, k=5, completed=None)

        if not results:
            return f"❌ I couldn't find any todos matching '{description}'. Would you like to list all your todos?"

        if len(results) == 1:
            # Single match - return the ID so agent can proceed with update
            todo_id = results[0]["todo_id"]
            content = results[0]["content"]
            priority = results[0]["metadata"].get("priority", 0)

            # Get the full todo for more details
            todo = service.get_todo(todo_id)
            due_info = ""
            if todo and todo.due_date:
                due_info = f", due {todo.due_date.strftime('%Y-%m-%d')}"

            priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(priority, "")
            return f"Found todo #{todo_id}: {content}{priority_label}{due_info}"
        else:
            # Multiple matches - ask for clarification
            lines = [f"I found {len(results)} todos matching '{description}':"]
            for i, result in enumerate(results, 1):
                todo_id = result["todo_id"]
                content = result["content"]
                relevance = result.get("relevance", 0)
                lines.append(f"{i}. #{todo_id}: {content} (match: {relevance:.0%})")
            lines.append("\nWhich one would you like to update? (say the number or specify by ID like '#5')")
            return "\n".join(lines)
    finally:
        try:
            service.close()
        except:
            pass


@tool
def find_todos_to_complete(description: str) -> str:
    """
    Find todos by description to mark as complete. Use this when user says they completed something.

    Args:
        description: Description of what was completed

    Returns:
        List of matching todos with IDs for confirmation
    """
    service = get_todo_service()

    try:
        results = service.search_todos(description, k=5, completed=False)

        if not results:
            return f"I couldn't find any active todos matching '{description}'. Would you like to list all your active todos?"

        if len(results) == 1:
            # Single match - suggest completing it
            todo_id = results[0]["todo_id"]
            content = results[0]["content"]
            return f"Found 1 todo: #{todo_id}: {content}. Should I mark this as complete?"
        else:
            # Multiple matches - ask for confirmation
            lines = [f"I found {len(results)} todos matching '{description}':"]
            for i, result in enumerate(results, 1):
                todo_id = result["todo_id"]
                content = result["content"]
                relevance = result.get("relevance", 0)
                lines.append(f"{i}. #{todo_id}: {content} (match: {relevance:.0%})")
            lines.append("\nWhich one(s) did you complete? (say the number or 'all')")
            return "\n".join(lines)
    finally:
        try:
            service.close()
        except:
            pass


@tool
def delete_todo(todo_id: int) -> str:
    """
    Delete a todo permanently.

    ⚠️ IMPORTANT: Only call this tool if the user EXPLICITLY requests to delete in their CURRENT message.
    DO NOT call this tool if the user just says "thanks", "ok", or other acknowledgments after a deletion.

    Args:
        todo_id: The ID of the todo to delete

    Returns:
        Confirmation message
    """
    service = get_todo_service()

    try:
        # Get todo info before deleting
        todo = service.get_todo(todo_id)
        if not todo:
            return f"❌ Todo #{todo_id} not found"

        content = todo.content
        deleted = service.delete_todo(todo_id)

        if deleted:
            return f"✗ Deleted todo #{todo_id}: {content}"
        else:
            return f"❌ Failed to delete todo #{todo_id}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def delete_todos_bulk(
    filter_type: str,
    confirm: bool = False
) -> str:
    """
    Delete multiple todos based on filter criteria.

    ⚠️ CRITICAL: This is a destructive operation. Always list the todos first and ask for user confirmation before deleting.

    DO NOT call this tool if the user just says "thanks", "ok", or other acknowledgments after a deletion.
    Only call with confirm=True if the user EXPLICITLY says "yes" or "confirm" to your confirmation request.

    Args:
        filter_type: Type of filter to apply. Options:
            - "no_due_date": Delete all todos without a due date
            - "completed": Delete all completed todos
            - "overdue": Delete all overdue todos
            - "all_active": Delete ALL active (non-completed) todos
        confirm: Must be True to actually delete. Use False to just preview what would be deleted.

    Returns:
        Confirmation message or preview
    """
    service = get_todo_service()

    try:
        # Get todos based on filter
        if filter_type == "no_due_date":
            todos = service.list_no_due_date()
            filter_desc = "todos without due dates"
        elif filter_type == "completed":
            todos = service.list_completed()
            filter_desc = "completed todos"
        elif filter_type == "overdue":
            todos = service.list_overdue()
            filter_desc = "overdue todos"
        elif filter_type == "all_active":
            todos = service.list_active()
            filter_desc = "ALL active todos"
        else:
            return f"❌ Invalid filter type: {filter_type}. Use: no_due_date, completed, overdue, or all_active"

        if not todos:
            return f"No {filter_desc} found to delete."

        # Preview mode - just show what would be deleted
        if not confirm:
            lines = [f"Found {len(todos)} {filter_desc} that would be deleted:"]
            for i, todo in enumerate(todos[:10], 1):  # Show max 10
                lines.append(f"{i}. #{todo.id}: {todo.content}")
            if len(todos) > 10:
                lines.append(f"... and {len(todos) - 10} more")
            lines.append("")
            lines.append("⚠️ To confirm deletion, user must explicitly agree to delete these todos.")
            return "\n".join(lines)

        # Confirmed deletion
        deleted_count = 0
        deleted_todos = []

        for todo in todos:
            content = todo.content
            if service.delete_todo(todo.id):
                deleted_count += 1
                deleted_todos.append(f"#{todo.id}: {content}")

        if deleted_count > 0:
            result = f"✗ Successfully deleted {deleted_count} {filter_desc}:\n"
            # Show first 5 deleted
            for item in deleted_todos[:5]:
                result += f"  - {item}\n"
            if len(deleted_todos) > 5:
                result += f"  ... and {len(deleted_todos) - 5} more"
            return result
        else:
            return f"❌ Failed to delete any todos"

    finally:
        try:
            service.close()
        except:
            pass


@tool
def list_focused_todos() -> str:
    """
    List all todos currently in the focus list.

    The focus list is a special section at the top of the todo pane where users
    can pin important todos regardless of due date.

    Returns:
        Formatted list of focused todos
    """
    service = get_todo_service()

    try:
        focused = service.list_focused()

        if not focused:
            return "No todos in focus list. You can add todos with the add_to_focus tool."

        lines = [f"⭐ Focus List ({len(focused)} items):"]
        for todo in focused:
            priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(todo.priority, "")

            due_label = ""
            if todo.due_date:
                from datetime import datetime
                due_date = todo.due_date.date() if isinstance(todo.due_date, datetime) else todo.due_date
                due_label = f" (due {due_date.strftime('%m/%d')})"

            lines.append(f"○ #{todo.id}: {todo.content}{priority_label}{due_label}")

        return "\n".join(lines)
    finally:
        service.close()


@tool
def add_to_focus(todo_id: int) -> str:
    """
    Add a todo to the focus list.

    The focus list appears at the top of the todo pane and is designed for
    5-10 most important todos that need attention regardless of due date.

    ⚠️ Only use this when user EXPLICITLY asks to "add to focus", "pin",
    "focus on", or "prioritize" a specific todo.

    Args:
        todo_id: The ID of the todo to add to focus

    Returns:
        Confirmation message
    """
    service = get_todo_service()

    try:
        # Check current count
        count = service.get_focus_count()
        if count >= 10:
            warning = f"\n⚠️  Note: You now have {count + 1} focused todos. Consider keeping it to 5-10 for best focus."
        elif count >= 5:
            warning = ""
        else:
            warning = ""

        todo = service.add_to_focus(todo_id)

        if not todo:
            return f"✗ Todo #{todo_id} not found"

        return f"⭐ Added to focus: #{todo.id} {todo.content}{warning}"
    finally:
        service.close()


@tool
def remove_from_focus(todo_id: int) -> str:
    """
    Remove a todo from the focus list.

    The todo will return to its normal section based on due date.

    Args:
        todo_id: The ID of the todo to remove from focus

    Returns:
        Confirmation message
    """
    service = get_todo_service()

    try:
        todo = service.remove_from_focus(todo_id)

        if not todo:
            return f"✗ Todo #{todo_id} not found"

        return f"Removed from focus: #{todo.id} {todo.content}"
    finally:
        service.close()


@tool
def clear_focus_list() -> str:
    """
    Clear all todos from the focus list.

    ⚠️ Only use this when user EXPLICITLY asks to "clear focus" or "remove all from focus".
    Always confirm with user before calling this.

    Returns:
        Confirmation message with count
    """
    service = get_todo_service()

    try:
        count = service.clear_focus()
        return f"✓ Cleared {count} todo(s) from focus list"
    finally:
        service.close()


@tool
def suggest_focus_todos() -> str:
    """
    Analyze all active todos and suggest which ones should be added to the focus list.

    This tool uses AI analysis of:
    - Due dates (overdue, today, this week)
    - Priority levels (urgent, high, normal)
    - Creation dates (older todos that might need attention)
    - Current focus list status (only suggests non-focused items)

    Returns a numbered list of suggested todos with reasoning.
    The system will then prompt the user to select which suggestions to add to focus.

    Returns:
        Formatted list with numbered suggestions and special marker for interactive selection
    """
    from datetime import datetime, date, timedelta

    service = get_todo_service()

    try:
        # Get all active todos that aren't already in focus
        all_active = service.list_active(limit=1000)
        focused = service.list_focused()
        focused_ids = {t.id for t in focused}

        # Filter to only non-focused todos
        candidates = [t for t in all_active if t.id not in focused_ids]

        if not candidates:
            return "No todos available to suggest. All active todos are either already in focus or you have no active todos."

        # Score each todo
        today = date.today()
        suggestions = []

        for todo in candidates:
            score = 0
            reasons = []

            # Due date scoring
            if todo.due_date:
                todo_date = todo.due_date.date() if isinstance(todo.due_date, datetime) else todo.due_date

                if todo_date < today:
                    days_overdue = (today - todo_date).days
                    score += 100
                    reasons.append(f"{days_overdue}d overdue")
                elif todo_date == today:
                    score += 80
                    reasons.append("due today")
                elif todo_date == today + timedelta(days=1):
                    score += 60
                    reasons.append("due tomorrow")
                elif todo_date <= today + timedelta(days=3):
                    score += 40
                    reasons.append("due within 3 days")
                elif todo_date <= today + timedelta(days=7):
                    score += 20
                    reasons.append("due this week")

            # Priority scoring
            if todo.priority >= 2:
                score += 50
                reasons.append("urgent priority")
            elif todo.priority == 1:
                score += 30
                reasons.append("high priority")

            # Age scoring (older todos might need attention)
            age_days = (datetime.utcnow() - todo.created_at).days
            if age_days > 30:
                score += 25
                reasons.append(f"{age_days}d old")
            elif age_days > 14:
                score += 15
                reasons.append(f"{age_days}d old")
            elif age_days > 7:
                score += 5

            suggestions.append({
                'todo': todo,
                'score': score,
                'reasons': reasons
            })

        # Sort by score (highest first) and take top 10
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        top_suggestions = suggestions[:10]

        if not top_suggestions:
            return "No strong suggestions found. Your todos look well-organized!"

        # Format output
        lines = [f"📊 Suggested todos for focus (top {len(top_suggestions)}):\n"]

        for i, item in enumerate(top_suggestions, 1):
            todo = item['todo']
            reasons = item['reasons']
            reason_str = ", ".join(reasons) if reasons else "good candidate"

            priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(todo.priority, "")
            due_label = ""
            if todo.due_date:
                todo_date = todo.due_date.date() if isinstance(todo.due_date, datetime) else todo.due_date
                due_label = f" (due {todo_date.strftime('%m/%d')})"

            lines.append(f"{i}. #{todo.id}: {todo.content}{priority_label}{due_label}")
            lines.append(f"   Why: {reason_str}")

        lines.append("\n💡 Select todos to add to focus by typing their numbers (e.g., '1,2,3' or 'all')")

        # Add special marker for interactive selection
        todo_ids = [str(item['todo'].id) for item in top_suggestions]
        result = "\n".join(lines)
        result += f"\n__FOCUS_SUGGESTIONS__|{','.join(todo_ids)}__"

        return result

    finally:
        service.close()


@tool
def create_note(content: str, title: Optional[str] = None) -> str:
    """
    Create a new note.

    ⚠️ IMPORTANT: Only call this tool if the user EXPLICITLY requests to create a note in their CURRENT message.
    DO NOT call this if they just said "thanks", "ok", or are acknowledging a previous action.

    Args:
        content: The note content
        title: Optional title for the note

    Returns:
        Confirmation message with the note ID
    """
    service = get_note_service()
    note = service.create_note(content=content, title=title)

    title_display = f": {title}" if title else ""
    return f"✓ Created note #{note.id}{title_display}"


@tool
def list_notes(limit: int = 10) -> str:
    """
    List recent notes.

    Args:
        limit: Maximum number of notes to list

    Returns:
        Formatted list of notes
    """
    service = get_note_service()
    notes = service.list_all(limit=limit)

    if not notes:
        return "No notes found."

    lines = [f"📋 Recent Notes ({len(notes)}):\n"]
    for note in notes:
        title_display = note.title or "Untitled"
        preview = note.content[:150] + "..." if len(note.content) > 150 else note.content
        lines.append(f"📝 Note #{note.id}: {title_display}")

        # Add category and tags if available
        if note.category:
            lines.append(f"   Category: [{note.category.upper()}]")

        tags = note.get_tags() if hasattr(note, 'get_tags') else []
        if tags:
            lines.append(f"   Tags: 🏷️  {', '.join(tags)}")

        lines.append(f"   Preview: {preview}")
        lines.append("")  # Blank line between notes

    return "\n".join(lines)


@tool
def search_notes(query: str, limit: int = 10) -> str:
    """
    Search notes semantically using natural language.

    Use this tool when the user asks about notes in ANY of these ways:
    - "do I have notes on client meetings?"
    - "show me notes about meetings"
    - "find notes related to API design"
    - "what notes do I have about authentication?"
    - "notes for project alpha"

    This uses semantic search, so it finds relevant notes even if they don't
    contain the exact words. For example, searching "client meetings" will find notes
    tagged with client names or mentioning meeting-related content.

    Args:
        query: Natural language search query
        limit: Maximum number of results (default 10)

    Returns:
        Formatted search results with note IDs, titles, categories, tags, and previews
    """
    service = get_note_service()
    results = service.search_notes(query, k=limit)

    if not results:
        return f"❌ No notes found matching: '{query}'\n\nTry:\n• Using different keywords\n• Broadening your search\n• Asking 'list notes' to see all notes"

    lines = [f"🔍 Found {len(results)} note(s) matching '{query}':\n"]

    for result in results:
        note_id = result["note_id"]
        title = result.get("title", "Untitled")
        content = result["content"]
        metadata = result.get("metadata", {})

        # Extract metadata
        category = metadata.get("category", "")
        tags = metadata.get("tags", "")
        keywords = metadata.get("keywords", "")

        # Format preview (first 150 chars)
        preview = content[:150] + "..." if len(content) > 150 else content

        # Build formatted entry - Use actual note ID prominently
        lines.append(f"📝 Note #{note_id}: {title}")

        if category:
            lines.append(f"   Category: [{category.upper()}]")

        if tags:
            lines.append(f"   Tags: 🏷️  {tags}")

        if keywords:
            lines.append(f"   Keywords: {keywords}")

        lines.append(f"   Preview: {preview}")
        lines.append("")  # Blank line between notes

    lines.append(f"💡 To see full content of a note, use: get_note(note_id)")
    lines.append(f"💡 To analyze these notes in detail, use: get_notes_for_analysis(\"{query}\")")

    return "\n".join(lines)


@tool
def delete_note(note_id: int) -> str:
    """
    Delete a note permanently.

    ⚠️ IMPORTANT: Only call this tool if the user EXPLICITLY requests to delete in their CURRENT message.
    DO NOT call this if they just said "thanks", "ok", or are acknowledging a previous deletion.

    Args:
        note_id: The ID of the note to delete

    Returns:
        Confirmation message
    """
    service = get_note_service()

    # Get note info before deleting
    note = service.get_note(note_id)
    if not note:
        return f"❌ Note #{note_id} not found"

    title = note.title or "Untitled"
    deleted = service.delete_note(note_id)

    if deleted:
        return f"✗ Deleted note #{note_id}: {title}"
    else:
        return f"❌ Failed to delete note #{note_id}"


@tool
def get_note(note_id: int) -> str:
    """
    Get the full content of a specific note.

    Args:
        note_id: The ID of the note to retrieve

    Returns:
        The note content with title
    """
    service = get_note_service()
    note = service.get_note(note_id)

    if not note:
        return f"❌ Note #{note_id} not found"

    title = note.title or "Untitled"
    created = note.created_at.strftime("%Y-%m-%d %H:%M")

    return f"""📝 Note #{note.id}: {title}
Created: {created}

{note.content}"""


@tool
def get_current_date() -> str:
    """
    Get the current date and time.

    Use this tool when you need to know what today's date is, especially when:
    - User mentions relative dates like "this friday", "next week", "tomorrow"
    - You need to calculate due dates
    - You need to know what day of the week it is today

    Returns:
        Current date and time with day of week
    """
    from datetime import datetime

    now = datetime.now()

    # Return comprehensive date info
    return f"""Current Date & Time:
• Today: {now.strftime('%A, %B %d, %Y')}
• Time: {now.strftime('%I:%M %p')}
• Day of week: {now.strftime('%A')}
• ISO format: {now.strftime('%Y-%m-%d')}

Use this information to calculate relative dates like "this friday", "next week", etc."""


@tool
def get_todo_stats() -> str:
    """
    Get statistics about todos.

    Returns:
        Formatted statistics
    """
    service = get_todo_service()
    counts = service.get_todo_count()

    return f"""📊 Todo Statistics:
• Active: {counts['active']}
• Completed: {counts['completed']}
• Total: {counts['total']}"""


@tool
def list_todos_by_date(date_string: str, include_completed: bool = False) -> str:
    """
    List todos due on a specific date or date range.

    Use this when the user asks about todos due on a specific date like:
    - "what's due this friday?" - shows todos for the next Friday
    - "show me todos for next week" - shows todos for next 7 days
    - "what do I need to do tomorrow?" - shows tomorrow's todos
    - "what do I have to get done the rest of the week?" - shows from today to end of week (Sunday)

    Args:
        date_string: Natural language date (e.g., "this friday", "tomorrow", "rest of the week", "next week", "2026-01-20")
        include_completed: Whether to include completed todos (default False)

    Returns:
        Formatted list of todos with the calculated date confirmed
    """
    service = get_todo_service()

    try:
        from datetime import datetime, timedelta

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        date_lower = date_string.lower()

        # Handle special cases first
        if "rest of the week" in date_lower or "rest of week" in date_lower:
            # From today to Sunday
            start_date = today
            days_until_sunday = (6 - today.weekday()) % 7
            if days_until_sunday == 0:  # If today is Sunday, go to next Sunday
                days_until_sunday = 7
            end_date = today + timedelta(days=days_until_sunday + 1)  # +1 to include Sunday
            date_label = f"rest of this week ({today.strftime('%b %d')} - {(end_date - timedelta(days=1)).strftime('%b %d')})"

        elif "this week" in date_lower:
            # Monday to Sunday of current week
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=7)
            date_label = f"this week ({start_date.strftime('%b %d')} - {(end_date - timedelta(days=1)).strftime('%b %d')})"

        elif "next week" in date_lower:
            # Next Monday to Sunday
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            start_date = today + timedelta(days=days_until_monday)
            end_date = start_date + timedelta(days=7)
            date_label = f"next week ({start_date.strftime('%b %d')} - {(end_date - timedelta(days=1)).strftime('%b %d')})"

        elif any(day in date_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            # Specific day of week - find next occurrence
            target_days = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6
            }

            target_day = None
            for day_name, day_num in target_days.items():
                if day_name in date_lower:
                    target_day = day_num
                    break

            if target_day is not None:
                days_ahead = target_day - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7

                parsed_date = today + timedelta(days=days_ahead)
                start_date = parsed_date
                end_date = parsed_date + timedelta(days=1)
                date_label = parsed_date.strftime('%A, %B %d, %Y')
            else:
                return f"❌ Could not determine which day of the week from '{date_string}'"

        elif "tomorrow" in date_lower:
            start_date = today + timedelta(days=1)
            end_date = start_date + timedelta(days=1)
            date_label = start_date.strftime('%A, %B %d, %Y')

        elif "today" in date_lower:
            start_date = today
            end_date = today + timedelta(days=1)
            date_label = today.strftime('%A, %B %d, %Y')

        elif "month" in date_lower:
            if "next" in date_lower:
                # Next month
                if today.month == 12:
                    start_date = datetime(today.year + 1, 1, 1)
                else:
                    start_date = datetime(today.year, today.month + 1, 1)
            else:
                # This month
                start_date = datetime(today.year, today.month, 1)

            # Get last day of month
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day - 1) + timedelta(days=1)
            date_label = start_date.strftime('%B %Y')

        else:
            # Try dateparser or ISO format
            parsed_date = None

            if HAS_DATEPARSER:
                try:
                    parsed_date = dateparser.parse(date_string, settings={'PREFER_DATES_FROM': 'future'})
                except:
                    pass

            if not parsed_date:
                try:
                    parsed_date = datetime.fromisoformat(date_string)
                except:
                    return f"❌ Could not parse date '{date_string}'. Try formats like 'this friday', 'tomorrow', 'rest of the week', or ISO format (YYYY-MM-DD)."

            start_date = datetime(parsed_date.year, parsed_date.month, parsed_date.day, 0, 0, 0)
            end_date = start_date + timedelta(days=1)
            date_label = parsed_date.strftime('%A, %B %d, %Y')

        todos = service.list_by_date_range(start_date, end_date, include_completed)

        if not todos:
            status_text = "todos" if include_completed else "active todos"
            return f"No {status_text} due {date_label}."

        status_text = "" if include_completed else " active"
        lines = [f"Found {len(todos)}{status_text} todo(s) due {date_label}:"]

        for todo in todos:
            status_icon = "✓" if todo.completed else "○"
            priority_label = {0: "", 1: " [HIGH]", 2: " [URGENT]"}.get(todo.priority, "")
            due_display = todo.due_date.strftime('%b %d') if todo.due_date else ""
            lines.append(f"{status_icon} #{todo.id}: {todo.content}{priority_label} ({due_display})")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error listing todos by date: {str(e)}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def list_completed_by_date(date_string: str = "today", limit: int = 100) -> str:
    """
    List todos completed on a specific date or date range.

    Use this when the user asks what they accomplished/completed:
    - "what did I do today?" - shows today's completions
    - "what did I complete yesterday?" - shows yesterday's completions
    - "show me what I finished this week" - shows this week's completions
    - "what did I accomplish last week?" - shows last week's completions

    Args:
        date_string: Natural language date (e.g., "today", "yesterday", "this week", "2026-02-12")
        limit: Maximum number of todos to return (default 100)

    Returns:
        Formatted list of completed todos with completion timestamps
    """
    service = get_todo_service()

    try:
        from datetime import datetime, timedelta
        import dateparser

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        date_lower = date_string.lower()

        # Handle special cases
        if "rest of the week" in date_lower or "rest of week" in date_lower:
            # From today to Sunday
            start_date = today
            days_until_sunday = (6 - today.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            end_date = today + timedelta(days=days_until_sunday + 1)
            date_label = f"rest of this week"

        elif "this week" in date_lower:
            # Monday to Sunday of current week
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=7)
            date_label = f"this week"

        elif "last week" in date_lower:
            # Previous Monday to Sunday
            days_since_monday = today.weekday()
            this_monday = today - timedelta(days=days_since_monday)
            start_date = this_monday - timedelta(days=7)
            end_date = this_monday
            date_label = f"last week"

        elif "yesterday" in date_lower:
            start_date = today - timedelta(days=1)
            end_date = today
            date_label = "yesterday"

        elif "today" in date_lower:
            start_date = today
            end_date = today + timedelta(days=1)
            date_label = "today"

        else:
            # Try parsing with dateparser or ISO format
            parsed_date = None

            try:
                parsed_date = dateparser.parse(date_string)
            except:
                pass

            if not parsed_date:
                try:
                    parsed_date = datetime.fromisoformat(date_string)
                except:
                    return f"❌ Could not parse date '{date_string}'. Try formats like 'today', 'yesterday', 'this week', or ISO format (YYYY-MM-DD)."

            start_date = datetime(parsed_date.year, parsed_date.month, parsed_date.day, 0, 0, 0)
            end_date = start_date + timedelta(days=1)
            date_label = parsed_date.strftime('%A, %B %d, %Y')

        # Query completed todos by completion date
        todos = service.list_completed_by_date_range(start_date, end_date, limit=limit)

        if not todos:
            return f"✨ No todos completed {date_label}."

        lines = [f"✅ You completed {len(todos)} todo(s) {date_label}:\n"]

        for todo in todos:
            priority_label = {0: "", 1: " ❗", 2: " ❗❗"}.get(todo.priority, "")

            # Show completion time
            if todo.completed_at:
                completed_time = todo.completed_at.strftime('%I:%M %p')
                lines.append(f"✓ #{todo.id}: {todo.content}{priority_label} (completed at {completed_time})")
            else:
                lines.append(f"✓ #{todo.id}: {todo.content}{priority_label}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error listing completed todos: {str(e)}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def import_notes_bulk(content: str, auto_split: bool = True) -> str:
    """
    Import bulk notes with AI categorization and metadata extraction (preview only).

    This tool is for knowledge transfer scenarios where a coworker shares
    multiple notes that need to be organized and imported.

    Args:
        content: Bulk note content (may contain multiple notes separated by ---, ###, or blank lines)
        auto_split: Automatically split by delimiters (default True)

    Returns:
        Summary of extracted notes for user review
    """
    from terminal_todos.extraction.knowledge_extractor import KnowledgeExtractor

    service = get_note_service()

    try:
        extractor = KnowledgeExtractor()

        # Extract metadata
        extraction = extractor.extract_bulk(content, auto_split=auto_split)

        if not extraction.has_notes():
            return "❌ No notes could be extracted from the provided content."

        # Format preview
        lines = [f"📦 Extracted {extraction.get_note_count()} note(s) for import:\n"]

        for i, note in enumerate(extraction.notes, 1):
            lines.append(f"{i}. [{note.category.upper()}] {note.title}")
            lines.append(f"   Summary: {note.summary}")
            if note.keywords:
                lines.append(f"   Keywords: {', '.join(note.keywords)}")
            if note.topics:
                lines.append(f"   Topics: {', '.join(note.topics)}")
            lines.append("")

        lines.append("⚠️  This is a preview. Use /import command in TUI for actual import with confirmation.")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Failed to extract notes: {str(e)}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def search_notes_by_category(category: str, limit: int = 10) -> str:
    """
    Search notes filtered by category.

    Args:
        category: Category to filter by (technical, meeting, documentation, project, brainstorm, reference, decision, action-items)
        limit: Maximum number of results

    Returns:
        Formatted search results
    """
    service = get_note_service()

    try:
        # Use vector store directly for category filtering
        results = service.sync_service.vector_store.search_notes(
            query=category,  # Use category as query
            k=limit,
            category=category
        )

        if not results:
            return f"No notes found in category '{category}'"

        lines = [f"🔍 Found {len(results)} note(s) in category '{category}':\n"]
        for result in results:
            note_id = result["note_id"]
            title = result.get("title", "Untitled")
            cat = result["metadata"].get("category", "")

            lines.append(f"📝 Note #{note_id}: {title}")
            lines.append(f"   Category: [{cat.upper()}]")
            lines.append("")  # Blank line between notes

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Search failed: {str(e)}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def get_notes_for_analysis(query: str, limit: int = 5) -> str:
    """
    Retrieve full content of notes matching a query for analysis (RAG mode).

    Use this tool when the user wants to ANALYZE notes or ask QUESTIONS about them:
    - "what do my client notes say about authentication?"
    - "summarize my meeting notes from last week"
    - "tell me about my API design notes"
    - "what are the key points in my notes about X?"
    - "according to my notes, what was decided about Y?"

    This returns FULL note content so you can read them and answer the user's question.

    Args:
        query: Search query to find relevant notes
        limit: Maximum number of notes to retrieve (default 5, max 10)

    Returns:
        Full content of matching notes for you to analyze and answer questions
    """
    service = get_note_service()

    # Limit to max 10 to avoid context overflow
    limit = min(limit, 10)

    results = service.search_notes(query, k=limit)

    if not results:
        return f"❌ No notes found matching: '{query}'"

    lines = [f"📚 Retrieved {len(results)} note(s) for analysis:\n"]
    lines.append("=" * 80 + "\n")

    for i, result in enumerate(results, 1):
        note_id = result["note_id"]

        # Get full note from database
        note = service.get_note(note_id)
        if not note:
            continue

        title = note.title or "Untitled"
        created = note.created_at.strftime("%Y-%m-%d %H:%M")
        category = note.category or ""
        tags = ", ".join(note.get_tags()) if note.get_tags() else ""
        keywords = ", ".join(note.get_keywords()) if note.get_keywords() else ""

        lines.append(f"NOTE {i}: #{note_id} - {title}")
        lines.append(f"Created: {created}")

        if category:
            lines.append(f"Category: [{category.upper()}]")

        if tags:
            lines.append(f"Tags: 🏷️  {tags}")

        if keywords:
            lines.append(f"Keywords: {keywords}")

        lines.append(f"\nContent:\n{note.content}")
        lines.append("\n" + "=" * 80 + "\n")

    lines.append(f"\n💡 Analyze the notes above and answer the user's question. Cite specific note IDs when referencing information.")

    return "\n".join(lines)


@tool
def search_notes_by_tags(tags: str, limit: int = 10) -> str:
    """
    Search notes filtered by tags (accounts, clients, projects).

    Args:
        tags: Comma-separated tags to search for (e.g., "Client-A,ProjectBeta")
        limit: Maximum number of results

    Returns:
        Formatted search results with matching tags
    """
    service = get_note_service()

    try:
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

        if not tag_list:
            return "❌ No tags provided. Please provide comma-separated tags."

        # Get all notes from vector store with a broad query
        results = service.sync_service.vector_store.search_notes(
            query=" ".join(tag_list),  # Use tags as query
            k=limit * 3  # Get more results for post-filtering
        )

        # Filter results by tags
        filtered_results = []
        for result in results:
            note_tags = result["metadata"].get("tags", "")
            if note_tags:
                note_tag_list = note_tags.split(",")
                # Check if any requested tag matches
                if any(tag in note_tag_list for tag in tag_list):
                    filtered_results.append(result)

        # Trim to requested limit
        filtered_results = filtered_results[:limit]

        if not filtered_results:
            return f"No notes found with tags: {', '.join(tag_list)}"

        lines = [f"🔍 Found {len(filtered_results)} note(s) with matching tags:\n"]
        for result in filtered_results:
            note_id = result["note_id"]
            title = result.get("title", "Untitled")
            cat = result["metadata"].get("category", "")
            note_tags = result["metadata"].get("tags", "")

            lines.append(f"📝 Note #{note_id}: {title}")

            if cat:
                lines.append(f"   Category: [{cat.upper()}]")

            if note_tags:
                lines.append(f"   Tags: 🏷️  {note_tags}")

            lines.append("")  # Blank line between notes

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Search failed: {str(e)}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def list_notes_by_date(date_string: str, limit: int = 100) -> str:
    """
    List notes created on a specific date or date range.

    Use this when the user asks about notes created on a specific date like:
    - "what notes did I create today?"
    - "show me notes from yesterday"
    - "notes created this week"
    - "what notes did I make on friday?"
    - "show me notes from january 15th"

    Args:
        date_string: Natural language date (e.g., "today", "yesterday", "this week", "last week", "2026-01-15")
        limit: Maximum number of notes to return (default 100)

    Returns:
        Formatted list of notes with the calculated date confirmed
    """
    service = get_note_service()

    try:
        from datetime import datetime, timedelta

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        date_lower = date_string.lower()

        # Handle special cases first
        if "today" in date_lower:
            start_date = today
            end_date = today + timedelta(days=1)
            date_label = today.strftime('%A, %B %d, %Y')

        elif "yesterday" in date_lower:
            start_date = today - timedelta(days=1)
            end_date = today
            date_label = (today - timedelta(days=1)).strftime('%A, %B %d, %Y')

        elif "this week" in date_lower:
            # Monday to Sunday of current week
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=7)
            date_label = f"this week ({start_date.strftime('%b %d')} - {(end_date - timedelta(days=1)).strftime('%b %d')})"

        elif "last week" in date_lower:
            # Previous Monday to Sunday
            days_since_monday = today.weekday()
            this_monday = today - timedelta(days=days_since_monday)
            start_date = this_monday - timedelta(days=7)
            end_date = this_monday
            date_label = f"last week ({start_date.strftime('%b %d')} - {(end_date - timedelta(days=1)).strftime('%b %d')})"

        elif "this month" in date_lower:
            # First day of current month to today
            start_date = datetime(today.year, today.month, 1)
            # Last day of current month
            if today.month == 12:
                end_date = datetime(today.year + 1, 1, 1)
            else:
                end_date = datetime(today.year, today.month + 1, 1)
            date_label = today.strftime('%B %Y')

        elif "last month" in date_lower:
            # First day to last day of previous month
            if today.month == 1:
                start_date = datetime(today.year - 1, 12, 1)
                end_date = datetime(today.year, 1, 1)
                date_label = start_date.strftime('%B %Y')
            else:
                start_date = datetime(today.year, today.month - 1, 1)
                end_date = datetime(today.year, today.month, 1)
                date_label = start_date.strftime('%B %Y')

        elif any(day in date_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            # Specific day of week - find most recent occurrence (including today)
            target_days = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6
            }

            target_day = None
            for day_name, day_num in target_days.items():
                if day_name in date_lower:
                    target_day = day_num
                    break

            if target_day is not None:
                days_ago = (today.weekday() - target_day) % 7
                if days_ago == 0:
                    # Today is the target day
                    parsed_date = today
                else:
                    # Find most recent occurrence
                    parsed_date = today - timedelta(days=days_ago)

                start_date = parsed_date
                end_date = parsed_date + timedelta(days=1)
                date_label = parsed_date.strftime('%A, %B %d, %Y')
            else:
                return f"❌ Could not determine which day of the week from '{date_string}'"

        else:
            # Try dateparser or ISO format
            parsed_date = None

            if HAS_DATEPARSER:
                try:
                    parsed_date = dateparser.parse(date_string, settings={'PREFER_DATES_FROM': 'past'})
                except:
                    pass

            if not parsed_date:
                try:
                    parsed_date = datetime.fromisoformat(date_string)
                except:
                    return f"❌ Could not parse date '{date_string}'. Try formats like 'today', 'yesterday', 'this week', 'last week', or ISO format (YYYY-MM-DD)."

            start_date = datetime(parsed_date.year, parsed_date.month, parsed_date.day, 0, 0, 0)
            end_date = start_date + timedelta(days=1)
            date_label = parsed_date.strftime('%A, %B %d, %Y')

        notes = service.list_by_date_range(start_date, end_date, limit=limit)

        if not notes:
            return f"No notes created {date_label}."

        lines = [f"📋 Found {len(notes)} note(s) created {date_label}:\n"]

        for note in notes:
            title_display = note.title or "Untitled"
            preview = note.content[:100] + "..." if len(note.content) > 100 else note.content
            created_time = note.created_at.strftime('%I:%M %p')

            lines.append(f"📝 Note #{note.id}: {title_display}")
            lines.append(f"   Created: {created_time}")

            # Add category and tags if available
            if note.category:
                lines.append(f"   Category: [{note.category.upper()}]")

            tags = note.get_tags() if hasattr(note, 'get_tags') else []
            if tags:
                lines.append(f"   Tags: 🏷️  {', '.join(tags)}")

            lines.append(f"   Preview: {preview}")
            lines.append("")  # Blank line between notes

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Error listing notes by date: {str(e)}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def list_imported_notes(limit: int = 20) -> str:
    """
    List all imported notes (notes created via bulk import).

    Use this tool when the user asks about imported notes:
    - "show me my imported notes"
    - "what notes have I imported?"
    - "list all imported notes"

    Args:
        limit: Maximum number of notes to list (default 20)

    Returns:
        Formatted list of imported notes
    """
    service = get_note_service()

    try:
        # Get all notes and filter by note_type="imported"
        all_notes = service.list_all(limit=limit * 2)  # Get more for filtering
        imported_notes = [note for note in all_notes if note.note_type == "imported"]
        imported_notes = imported_notes[:limit]  # Trim to limit

        if not imported_notes:
            return "No imported notes found. You can import notes using the /import command."

        lines = [f"📦 Imported Notes ({len(imported_notes)}):\n"]
        for note in imported_notes:
            title_display = note.title or "Untitled"
            preview = note.content[:150] + "..." if len(note.content) > 150 else note.content
            lines.append(f"📝 Note #{note.id}: {title_display}")

            # Add category and tags if available
            if note.category:
                lines.append(f"   Category: [{note.category.upper()}]")

            tags = note.get_tags() if hasattr(note, 'get_tags') else []
            if tags:
                lines.append(f"   Tags: 🏷️  {', '.join(tags)}")

            # Show import date
            if note.created_at:
                lines.append(f"   Imported: {note.created_at.strftime('%Y-%m-%d %H:%M')}")

            lines.append(f"   Preview: {preview}")
            lines.append("")  # Blank line between notes

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Failed to list imported notes: {str(e)}"
    finally:
        try:
            service.close()
        except:
            pass


@tool
def extract_todos_from_notes(note_ids: list[int]) -> str:
    """
    Extract actionable todos from specific notes using AI.

    This will analyze the notes and display a numbered list of extracted todos.
    The user will then respond with numbers (e.g., "1,2,3" or "all") to select
    which todos to create.

    Use this tool when the user asks to extract or find todos in their notes:
    - "extract todos from note 14"
    - "get todos from notes 45 and 67"
    - "find action items in note 102"
    - "what todos are in my meeting note"

    ⚠️ IMPORTANT: Only call this if the user EXPLICITLY asks to extract/find todos.
    DO NOT call this if they just want to read or view notes.

    Args:
        note_ids: List of note IDs to extract todos from (e.g., [14], [45, 67, 102])

    Returns:
        Confirmation that extraction will start
    """
    # This is a special tool that triggers the extraction flow
    # The app will detect this marker and show the numbered list

    if not note_ids:
        return "❌ No note IDs provided. Please specify which notes to extract from."

    # Convert to comma-separated string for the marker
    note_ids_str = ",".join(str(id) for id in note_ids)

    # Return a special marker that the app will detect
    return f"__EXTRACT_TODOS_INTERACTIVE__|{note_ids_str}__"


def detect_email_instructions_in_note(note) -> dict:
    """
    Detect email-related action items in note content.

    Returns dict with:
        - has_instruction: bool
        - action_type: str ('send_resources', 'follow_up', 'introduction', etc.)
        - recipient: str or None
        - mentioned_items: list[str]
    """
    import re

    content = note.content.lower()
    keywords = note.get_keywords() if hasattr(note, "get_keywords") else []

    # Action phrase patterns
    send_patterns = [
        r"send\s+(?:over\s+)?(?:the\s+)?(\w+)",
        r"share\s+(?:the\s+)?(\w+)",
        r"email\s+(?:them\s+)?(?:the\s+)?(\w+)",
    ]

    follow_up_patterns = [
        r"follow\s+up\s+(?:with\s+)?(\w+)?",
        r"reach\s+out\s+(?:to\s+)?(\w+)?",
    ]

    result = {
        "has_instruction": False,
        "action_type": None,
        "recipient": None,
        "mentioned_items": [],
    }

    # Check for send/share patterns
    for pattern in send_patterns:
        matches = re.findall(pattern, content)
        if matches:
            result["has_instruction"] = True
            result["action_type"] = "send_resources"
            result["mentioned_items"].extend(matches)

    # Check for follow-up patterns
    for pattern in follow_up_patterns:
        matches = re.findall(pattern, content)
        if matches:
            result["has_instruction"] = True
            if not result["action_type"]:
                result["action_type"] = "follow_up"
            if matches[0]:
                result["recipient"] = matches[0]

    # Check keywords for email-related terms
    email_keywords = {"email", "send", "share", "follow-up", "reach-out"}
    if any(kw in email_keywords for kw in keywords):
        result["has_instruction"] = True
        if not result["action_type"]:
            result["action_type"] = "custom"

    return result


@tool
def generate_email(
    context: str, recipient: Optional[str] = None, email_type: Optional[str] = None
) -> str:
    """
    Generate a professional email draft based on context.

    Use this when the user wants to:
    - Generate an email
    - Draft an email
    - Create an email message
    - Follow up with someone via email
    - Send an email about something

    Args:
        context: The context for the email (can be note content, meeting notes, or direct instructions)
        recipient: Optional recipient name or role
        email_type: Optional email type hint ('follow_up', 'enablement', 'introduction', etc.)

    Returns:
        Formatted email draft with subject and body
    """
    from terminal_todos.core.email_service import get_email_service
    from langchain_anthropic import ChatAnthropic

    # Initialize LLM for email generation
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0.7)

    # Create structured output LLM
    structured_llm = llm.with_structured_output(EmailDraft)

    # Build prompt using system templates and context
    prompt = f"""Generate a professional email based on the following context.

Context:
{context}

Recipient: {recipient if recipient else "To be determined"}
Email Type: {email_type if email_type else "auto-detect from context"}

Guidelines:
- Use professional but warm tone
- Include clear subject line
- Structure with greeting, body paragraphs, and closing
- Include action items or next steps if applicable
- Reference any resources or materials mentioned in context
- Keep formatting clean and readable

Generate a complete, ready-to-send email draft."""

    try:
        # Generate email using LLM
        email_draft = structured_llm.invoke(prompt)

        # Save to database
        email_service = get_email_service()
        try:
            saved_email = email_service.create_email(
                subject=email_draft.subject,
                body=email_draft.body,
                recipient=email_draft.recipient,
                template_type=email_draft.template_type,
            )

            # Format for display
            output = f"""✉️ **Generated Email Draft** (ID: {saved_email.id})

**Subject:** {email_draft.subject}
**To:** {email_draft.recipient}
**Type:** {email_draft.template_type}

---

{email_draft.body}

---

✓ Email copied to clipboard and saved as draft #{saved_email.id}
💡 Use `/copy-email` to copy again or `/list-emails` to see all drafts"""

            return output
        finally:
            email_service.close()

    except Exception as e:
        return f"❌ Error generating email: {str(e)}"


@tool
def list_email_drafts(limit: int = 10) -> str:
    """
    List recent email drafts.

    Use this when the user wants to:
    - See their email drafts
    - List emails
    - Show recent emails
    - View email history

    Args:
        limit: Maximum number of emails to retrieve (default 10)

    Returns:
        Formatted list of recent email drafts
    """
    from terminal_todos.core.email_service import get_email_service

    service = get_email_service()
    try:
        emails = service.list_recent_emails(limit)

        if not emails:
            return "📭 No email drafts found."

        output = [f"📧 **Recent Email Drafts** ({len(emails)}):\n"]

        for email in emails:
            created = email.created_at.strftime("%Y-%m-%d %H:%M")
            output.append(f"#{email.id} - {email.subject}")
            output.append(
                f"   To: {email.recipient or 'N/A'} | {email.template_type or 'custom'} | {created}\n"
            )

        return "\n".join(output)
    finally:
        service.close()


@tool
def get_email_draft(email_id: int) -> str:
    """
    Retrieve a specific email draft by ID.

    Use this when the user wants to:
    - View a specific email
    - Show email details
    - Get an email draft

    Args:
        email_id: The ID of the email draft to retrieve

    Returns:
        Formatted email content
    """
    from terminal_todos.core.email_service import get_email_service

    service = get_email_service()
    try:
        email = service.get_email(email_id)

        if not email:
            return f"❌ Email draft #{email_id} not found."

        output = f"""✉️ **Email Draft #{email.id}**

**Subject:** {email.subject}
**To:** {email.recipient or 'N/A'}
**Type:** {email.template_type or 'custom'}
**Created:** {email.created_at.strftime("%Y-%m-%d %H:%M")}

---

{email.body}

---

💡 Use `/copy-email {email_id}` to copy this email to clipboard"""

        return output
    finally:
        service.close()


# List of all tools
ALL_TOOLS = [
    get_current_date,
    create_todo,
    list_todos,
    list_todos_by_date,
    list_completed_by_date,
    list_focused_todos,
    search_todos,
    find_todos_to_complete,
    find_todos_to_update,
    complete_todo,
    uncomplete_todo,
    update_todo,
    delete_todo,
    delete_todos_bulk,
    add_to_focus,
    remove_from_focus,
    clear_focus_list,
    suggest_focus_todos,
    create_note,
    list_notes,
    list_notes_by_date,
    list_imported_notes,
    search_notes,
    get_note,
    delete_note,
    get_todo_stats,
    import_notes_bulk,
    search_notes_by_category,
    search_notes_by_tags,
    get_notes_for_analysis,
    extract_todos_from_notes,
    generate_email,
    list_email_drafts,
    get_email_draft,
]
