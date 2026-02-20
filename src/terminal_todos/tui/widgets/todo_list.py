"""Todo list widget for the left pane."""

from datetime import datetime, date, timedelta
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Static, Label
from textual.reactive import reactive

from terminal_todos.db.models import Todo


class FocusSection(Vertical):
    """Styled container for the focus list section."""

    DEFAULT_CSS = """
    FocusSection {
        border: double white;
        background: #1a1a1a;
        padding: 1;
        margin-bottom: 1;
        height: auto;
    }

    FocusSection > .focus-header {
        text-align: center;
        text-style: bold;
        color: white;
        padding-bottom: 1;
    }

    FocusSection TodoItem {
        background: transparent;
        height: auto;
        width: 100%;
        color: white;
        padding: 0 1;
    }
    """

    def __init__(self, focused_todos: list, **kwargs):
        super().__init__(**kwargs)
        self.focused_todos = focused_todos

    def compose(self) -> ComposeResult:
        """Compose the focus section with header and todos."""
        count = len(self.focused_todos)
        header = Label(f"⭐ FOCUS ({count}) ⭐")
        header.add_class("focus-header")
        yield header

        # Yield each focused todo
        sorted_todos = sorted(self.focused_todos, key=lambda t: t.focus_order)
        for todo in sorted_todos:
            todo_item = TodoItem(todo)
            yield todo_item


class TodoItem(Static):
    """A single todo item display."""

    def __init__(self, todo: Todo, **kwargs):
        super().__init__(**kwargs)
        self.todo = todo
        self.update_display()

    def update_display(self):
        """Update the display text for this todo."""
        status_icon = "✓" if self.todo.completed else "○"
        priority_label = {0: "", 1: " ❗", 2: " ❗❗"}.get(
            self.todo.priority, ""
        )

        # Format due date
        due_label = ""
        if self.todo.due_date:
            due_date = self.todo.due_date.date() if isinstance(self.todo.due_date, datetime) else self.todo.due_date
            today = date.today()

            if due_date == today:
                due_label = " 📅 today"
            elif due_date == today + timedelta(days=1):
                due_label = " 📅 tomorrow"
            elif due_date < today:
                days_overdue = (today - due_date).days
                # Different emojis based on severity
                if days_overdue == 1:
                    emoji = "⏰"
                elif days_overdue <= 7:
                    emoji = "⚠️"
                else:
                    emoji = "🚨"
                due_label = f" {emoji} {days_overdue}d overdue"
            else:
                due_label = f" 📅 {due_date.strftime('%m/%d')}"

        # Style based on completion
        if self.todo.completed:
            self.styles.color = "gray"
            self.update(f"[dim]{status_icon} #{self.todo.id}: {self.todo.content}{priority_label}{due_label}[/dim]")
        else:
            # All active todos are white - use emojis for distinction
            self.styles.color = "white"

            self.update(f"{status_icon} #{self.todo.id}: {self.todo.content}{priority_label}{due_label}")

    def refresh_todo(self, todo: Todo):
        """Refresh with updated todo data."""
        self.todo = todo
        self.update_display()


class TodoListWidget(VerticalScroll):
    """Widget for displaying the list of todos."""

    todos = reactive(list)
    show_completed = reactive(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Todos"
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """Compose the todo list."""
        yield Label("Loading todos...")

    def update_todos(self, todos: list[Todo]):
        """Update the displayed todos."""
        self.todos = todos
        self._render_todos()

    def _render_todos(self):
        """Render the todo list grouped by date."""
        # Clear existing children
        self.remove_children()

        if not self.todos:
            self.mount(Label("[dim]No todos yet. Create one with /todo[/dim]"))
            return

        # Filter based on show_completed
        filtered_todos = self.todos
        if not self.show_completed:
            filtered_todos = [t for t in self.todos if not t.completed]

        # Show counts
        active_count = sum(1 for t in self.todos if not t.completed)
        completed_count = sum(1 for t in self.todos if t.completed)
        self.border_title = f"Todos ({active_count} active, {completed_count} done)"

        if not filtered_todos:
            self.mount(Label("[dim]No todos to display[/dim]"))
            return

        # Separate focused vs non-focused todos
        focused = []
        non_focused = []

        for todo in filtered_todos:
            if not todo.completed and todo.focus_order is not None:
                focused.append(todo)
            else:
                non_focused.append(todo)

        # Group non-focused todos by date category
        today = date.today()
        overdue = []
        due_today = []
        due_tomorrow = []
        due_this_week = []
        no_due_date = []
        completed = []

        for todo in non_focused:
            if todo.completed:
                completed.append(todo)
            elif todo.due_date:
                todo_date = todo.due_date.date() if isinstance(todo.due_date, datetime) else todo.due_date

                if todo_date < today:
                    overdue.append(todo)
                elif todo_date == today:
                    due_today.append(todo)
                elif todo_date == today + timedelta(days=1):
                    due_tomorrow.append(todo)
                elif todo_date <= today + timedelta(days=7):
                    due_this_week.append(todo)
                else:
                    no_due_date.append(todo)
            else:
                no_due_date.append(todo)

        # Render FOCUS section first (if any)
        if focused:
            self.mount(FocusSection(focused))
            self.mount(Label("[dim]" + "─" * 40 + "[/dim]"))  # Visual separator

        # Render other sections
        if overdue:
            self.mount(Label("[bold white]🚨 OVERDUE[/bold white]"))
            for todo in sorted(overdue, key=lambda t: (t.due_date, -t.priority)):
                self.mount(TodoItem(todo))
            self.mount(Label(""))  # Spacer

        if due_today:
            self.mount(Label("[bold white]📅 TODAY[/bold white]"))
            for todo in sorted(due_today, key=lambda t: -t.priority):
                self.mount(TodoItem(todo))
            self.mount(Label(""))  # Spacer

        if due_tomorrow:
            self.mount(Label("[bold cyan]📅 TOMORROW[/bold cyan]"))
            for todo in sorted(due_tomorrow, key=lambda t: -t.priority):
                self.mount(TodoItem(todo))
            self.mount(Label(""))  # Spacer

        if due_this_week:
            self.mount(Label("[bold]📅 THIS WEEK[/bold]"))
            for todo in sorted(due_this_week, key=lambda t: (t.due_date, -t.priority)):
                self.mount(TodoItem(todo))
            self.mount(Label(""))  # Spacer

        if no_due_date:
            self.mount(Label("[dim]📋 NO DUE DATE[/dim]"))
            for todo in sorted(no_due_date, key=lambda t: -t.priority):
                self.mount(TodoItem(todo))
            self.mount(Label(""))  # Spacer

        if completed and self.show_completed:
            self.mount(Label("[dim]✓ COMPLETED[/dim]"))
            for todo in completed[:10]:  # Show only last 10 completed
                self.mount(TodoItem(todo))

    def toggle_completed_visibility(self):
        """Toggle showing/hiding completed todos."""
        self.show_completed = not self.show_completed
        self._render_todos()

    def get_todo_by_index(self, index: int) -> Todo | None:
        """Get todo at the given index (0-based)."""
        if 0 <= index < len(self.todos):
            return self.todos[index]
        return None
