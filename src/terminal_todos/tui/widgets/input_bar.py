"""Input bar widget for user input."""

from textual.widgets import Input, TextArea
from textual.containers import Container
from textual.app import ComposeResult
from textual import events
from typing import List


class HistoryInput(Input):
    """Input widget with command history navigation using arrow keys."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_history: List[str] = []  # Stores all sent messages
        self.history_index: int = -1  # Current position in history (-1 = not navigating)
        self.current_draft: str = ""  # Saves current input when navigating history

    def add_to_history(self, message: str):
        """
        Add a message to the history.

        Args:
            message: The message to add
        """
        if message and message.strip():
            # Don't add duplicate if same as last message
            if not self.message_history or self.message_history[-1] != message:
                self.message_history.append(message)

            # Reset navigation state
            self.history_index = -1
            self.current_draft = ""

    def _on_key(self, event: events.Key) -> None:
        """Handle key presses for history navigation."""
        if event.key == "up":
            # Navigate to older messages
            if self.message_history:
                if self.history_index == -1:
                    # Starting navigation - save current input
                    self.current_draft = self.value
                    self.history_index = len(self.message_history)

                # Move to previous message
                if self.history_index > 0:
                    self.history_index -= 1
                    self.value = self.message_history[self.history_index]
                    # Move cursor to end
                    self.cursor_position = len(self.value)

                event.prevent_default()
                event.stop()

        elif event.key == "down":
            # Navigate to newer messages
            if self.history_index != -1:
                self.history_index += 1

                if self.history_index >= len(self.message_history):
                    # Reached end - restore draft
                    self.value = self.current_draft
                    self.history_index = -1
                    self.current_draft = ""
                else:
                    # Show next message
                    self.value = self.message_history[self.history_index]

                # Move cursor to end
                self.cursor_position = len(self.value)

                event.prevent_default()
                event.stop()


class InputBarWidget(Container):
    """Widget for user input at the bottom of the screen."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline_mode = False

    def add_to_history(self, message: str):
        """
        Add a message to the input history.

        Args:
            message: The message to add to history
        """
        try:
            input_widget = self.query_one("#user-input", HistoryInput)
            input_widget.add_to_history(message)
        except:
            # In multiline mode, history not available
            pass

    def compose(self) -> ComposeResult:
        """Compose the input bar."""
        yield HistoryInput(
            placeholder="Type a message or /command...",
            id="user-input",
        )

    def get_input(self):
        """Get the input widget (HistoryInput or TextArea)."""
        try:
            return self.query_one("#user-input", HistoryInput)
        except:
            return self.query_one("#user-input-multiline", TextArea)

    def clear_input(self):
        """Clear the input field."""
        try:
            input_widget = self.query_one("#user-input", HistoryInput)
            input_widget.value = ""
        except:
            text_area = self.query_one("#user-input-multiline", TextArea)
            text_area.text = ""

    def set_input(self, text: str):
        """Set the input field value."""
        try:
            input_widget = self.query_one("#user-input", HistoryInput)
            input_widget.value = text
        except:
            text_area = self.query_one("#user-input-multiline", TextArea)
            text_area.text = text

    def focus_input(self):
        """Focus the input field."""
        try:
            input_widget = self.query_one("#user-input", HistoryInput)
            input_widget.focus()
        except:
            text_area = self.query_one("#user-input-multiline", TextArea)
            text_area.focus()

    def get_text(self) -> str:
        """Get the current text from the input."""
        try:
            input_widget = self.query_one("#user-input", HistoryInput)
            return input_widget.value
        except:
            text_area = self.query_one("#user-input-multiline", TextArea)
            return text_area.text

    def switch_to_multiline(self):
        """Switch to multi-line input mode."""
        if self.multiline_mode:
            return

        # Remove single-line input
        try:
            input_widget = self.query_one("#user-input", HistoryInput)
            input_widget.remove()
        except:
            pass

        # Add multi-line text area with proper configuration
        text_area = TextArea(
            id="user-input-multiline",
            show_line_numbers=False,
        )
        # Don't set language to avoid syntax highlighting issues
        text_area.show_line_numbers = False
        self.mount(text_area)
        self.call_after_refresh(text_area.focus)
        self.multiline_mode = True

    def switch_to_singleline(self, preserve_history: bool = True):
        """
        Switch back to single-line input mode.

        Args:
            preserve_history: If True, preserve message history in new input widget
        """
        if not self.multiline_mode:
            return

        # Save history from old input if it exists
        old_history = []
        if preserve_history:
            try:
                old_input = self.query_one("#user-input", HistoryInput)
                old_history = old_input.message_history.copy()
            except:
                pass

        # Remove multi-line text area
        try:
            text_area = self.query_one("#user-input-multiline", TextArea)
            text_area.remove()
        except:
            pass

        # Add single-line input back with history
        input_widget = HistoryInput(
            placeholder="Type a message or /command...",
            id="user-input",
        )
        self.mount(input_widget)

        # Restore history
        if old_history:
            input_widget.message_history = old_history

        input_widget.focus()
        self.multiline_mode = False
