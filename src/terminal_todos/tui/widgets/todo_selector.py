"""Interactive todo selector widget with checkbox list."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Static
from textual.binding import Binding
from textual.message import Message


class TodoSelectorWidget(Container):
    """Interactive widget for selecting todos - appears inline above input."""

    DEFAULT_CSS = """
    TodoSelectorWidget {
        height: auto;
        max-height: 20;
        background: $panel;
        border: thick $success;
        padding: 1;
        margin: 0 1;
    }

    TodoSelectorWidget #selector-header {
        text-align: center;
        color: $success;
        text-style: bold;
        margin-bottom: 1;
    }

    TodoSelectorWidget #selector-instructions {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    TodoSelectorWidget #selector-list {
        height: auto;
        max-height: 15;
        border: solid $primary;
        padding: 0 1;
    }

    TodoSelectorWidget .todo-item {
        padding: 0;
    }

    TodoSelectorWidget #selector-footer {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("up", "move_up", "Move Up", priority=True),
        Binding("down", "move_down", "Move Down", priority=True),
        Binding("space", "toggle", "Toggle", priority=True),
        Binding("a", "select_all", "Select All", priority=True),
        Binding("n", "select_none", "Select None", priority=True),
        Binding("enter", "submit", "Add Selected", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, extracted_todos: list[str], **kwargs):
        super().__init__(**kwargs)
        self.extracted_todos = extracted_todos
        self.selections = [True] * len(extracted_todos)  # All selected by default
        self.current_index = 0

    def compose(self) -> ComposeResult:
        """Compose the selector interface."""
        with Vertical():
            # Header
            yield Static(
                f"📋 SELECT TODOS TO ADD ({len(self.extracted_todos)} found)",
                id="selector-header"
            )

            # Instructions
            yield Static(
                "↑↓ Navigate • SPACE Toggle • ENTER Add • ESC Cancel",
                id="selector-instructions"
            )

            # Scrollable todo list
            with VerticalScroll(id="selector-list"):
                for i, todo in enumerate(self.extracted_todos):
                    yield Static("", id=f"todo-{i}", classes="todo-item")

            # Footer with count
            yield Static(
                "",
                id="selector-footer"
            )

    def on_mount(self):
        """Initialize display when mounted."""
        self.update_all_todos()
        self.can_focus = True
        self.focus()

    def update_all_todos(self):
        """Update display for all todo items."""
        for i in range(len(self.extracted_todos)):
            self.update_todo_display(i)

        # Update footer with count
        try:
            footer = self.query_one("#selector-footer", Static)
            selected_count = sum(self.selections)
            footer.update(f"[bold]{selected_count}[/bold] of {len(self.extracted_todos)} selected • Press ENTER to add")
        except:
            pass

    def update_todo_display(self, index: int):
        """Update display for a single todo item."""
        try:
            todo_widget = self.query_one(f"#todo-{index}", Static)
            checkbox = "☑" if self.selections[index] else "☐"
            todo_text = self.extracted_todos[index]

            # Highlight current item with arrow
            if index == self.current_index:
                todo_widget.update(f"[bold cyan]▶ {checkbox} {todo_text}[/bold cyan]")
            else:
                todo_widget.update(f"  {checkbox} {todo_text}")
        except:
            pass

    def action_move_up(self):
        """Move selection up."""
        if self.current_index > 0:
            old_index = self.current_index
            self.current_index -= 1
            self.update_todo_display(old_index)
            self.update_todo_display(self.current_index)

            # Scroll into view
            try:
                todo_widget = self.query_one(f"#todo-{self.current_index}", Static)
                todo_widget.scroll_visible()
            except:
                pass

    def action_move_down(self):
        """Move selection down."""
        if self.current_index < len(self.extracted_todos) - 1:
            old_index = self.current_index
            self.current_index += 1
            self.update_todo_display(old_index)
            self.update_todo_display(self.current_index)

            # Scroll into view
            try:
                todo_widget = self.query_one(f"#todo-{self.current_index}", Static)
                todo_widget.scroll_visible()
            except:
                pass

    def action_toggle(self):
        """Toggle the current todo selection."""
        self.selections[self.current_index] = not self.selections[self.current_index]
        self.update_all_todos()

    def action_select_all(self):
        """Select all todos."""
        self.selections = [True] * len(self.extracted_todos)
        self.update_all_todos()

    def action_select_none(self):
        """Deselect all todos."""
        self.selections = [False] * len(self.extracted_todos)
        self.update_all_todos()

    def action_submit(self):
        """Submit selected todos."""
        selected = [
            self.extracted_todos[i]
            for i in range(len(self.extracted_todos))
            if self.selections[i]
        ]
        self.post_message(self.Submitted(selected))

    def action_cancel(self):
        """Cancel the selection."""
        self.post_message(self.Cancelled())

    # Custom messages
    class Submitted(Message):
        """Message posted when user submits selected todos."""
        def __init__(self, selected_todos: list[str]):
            super().__init__()
            self.selected_todos = selected_todos

    class Cancelled(Message):
        """Message posted when user cancels."""
        pass
