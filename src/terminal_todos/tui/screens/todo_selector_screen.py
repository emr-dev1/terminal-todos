"""Modal screen for interactive todo selection."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, VerticalScroll, Horizontal
from textual.widgets import Static, Button
from textual.binding import Binding


class TodoSelectorScreen(ModalScreen[list[str] | None]):
    """Modal screen for selecting extracted todos to add."""

    BINDINGS = [
        Binding("up", "move_up", "Move Up", priority=True),
        Binding("down", "move_down", "Move Down", priority=True),
        Binding("space", "toggle", "Toggle Selection", show=False),
        Binding("a", "select_all", "Select All", show=False),
        Binding("n", "select_none", "Select None", show=False),
        Binding("enter", "submit", "Submit", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    TodoSelectorScreen {
        align: center middle;
    }

    #modal-container {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 80%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    #header {
        text-align: center;
        margin-bottom: 1;
    }

    #instructions {
        text-align: center;
        margin-bottom: 1;
        color: $text-muted;
    }

    #todo-list {
        height: auto;
        max-height: 30;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    .todo-item {
        padding: 0 1;
    }

    #action-buttons {
        height: auto;
        align: center middle;
    }

    #action-buttons Button {
        margin: 0 1;
    }

    #footer-help {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, extracted_todos: list[str], **kwargs):
        super().__init__(**kwargs)
        self.extracted_todos = extracted_todos
        self.selections = [True] * len(extracted_todos)  # All selected by default
        self.current_index = 0

    def compose(self) -> ComposeResult:
        """Compose the modal selector interface."""
        with Container(id="modal-container"):
            with Vertical():
                # Header
                yield Static(
                    f"[bold cyan]📋 Select Todos to Add ({len(self.extracted_todos)} found)[/bold cyan]",
                    id="header"
                )

                # Instructions
                yield Static(
                    "[dim]Use ↑↓ arrows to navigate • Space to toggle • Enter to add selected • Esc to cancel[/dim]",
                    id="instructions"
                )

                # Scrollable todo list
                with VerticalScroll(id="todo-list"):
                    for i, todo in enumerate(self.extracted_todos):
                        yield Static("", id=f"todo-{i}", classes="todo-item")

                # Action buttons
                with Horizontal(id="action-buttons"):
                    yield Button(
                        f"✓ Add Selected ({sum(self.selections)})",
                        variant="success",
                        id="submit-btn"
                    )
                    yield Button("✗ Cancel", variant="error", id="cancel-btn")

                # Footer help
                yield Static(
                    "[dim]Shortcuts: [/dim][bold]A[/bold][dim] Select All • [/dim][bold]N[/bold][dim] Select None[/dim]",
                    id="footer-help"
                )

    def on_mount(self):
        """Initialize display when mounted."""
        self.update_all_todos()

    def update_all_todos(self):
        """Update display for all todo items."""
        for i in range(len(self.extracted_todos)):
            self.update_todo_display(i)

        # Update button count
        try:
            submit_btn = self.query_one("#submit-btn", Button)
            submit_btn.label = f"✓ Add Selected ({sum(self.selections)})"
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
        self.dismiss(selected)

    def action_cancel(self):
        """Cancel the selection."""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button clicks."""
        event.stop()
        if event.button.id == "submit-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
