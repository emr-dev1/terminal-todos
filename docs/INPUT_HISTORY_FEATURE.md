# Input History Navigation Feature

## Overview

Added command/message history navigation in the input bar using arrow keys, similar to Claude Code and terminal shell history. Users can press Up/Down arrows to cycle through previously sent messages.

## Features

### Arrow Key Navigation

**Up Arrow (↑)**
- Navigate to older messages in history
- Saves current input as "draft" when first pressed
- Cycles from newest to oldest

**Down Arrow (↓)**
- Navigate to newer messages in history
- Restores saved "draft" when reaching the end
- Returns to empty state if no draft was saved

### Behavior

**Smart Duplicate Handling**
- Doesn't add duplicate messages if the same as the last one
- Example: Typing "list todos" twice only stores it once

**Draft Preservation**
- When you start typing and press Up, your current text is saved
- Press Down repeatedly to return to your draft
- Draft is cleared after submitting a message

**Cursor Positioning**
- Cursor automatically moves to end of line when navigating
- Allows immediate editing of recalled messages

**History Persistence**
- History is preserved when switching between single/multi-line modes
- Only cleared when app restarts

## Implementation Details

### New Component: `HistoryInput`

Custom Input widget that extends Textual's `Input` class:

```python
class HistoryInput(Input):
    def __init__(self):
        self.message_history: List[str] = []
        self.history_index: int = -1  # -1 = not navigating
        self.current_draft: str = ""  # Saves current input
```

**State Variables:**
- `message_history` - List of all sent messages (oldest to newest)
- `history_index` - Current position in history (-1 means not navigating)
- `current_draft` - Temporary storage for current unsent input

### Key Methods

**`add_to_history(message: str)`**
- Adds message to history after submission
- Prevents duplicate consecutive entries
- Resets navigation state

**`_on_key(event: events.Key)`**
- Intercepts Up/Down arrow key presses
- Manages navigation through history
- Handles draft saving/restoration
- Prevents default key handling when navigating

### Integration with InputBarWidget

**`add_to_history(message: str)`**
- Public method on `InputBarWidget`
- Forwards to underlying `HistoryInput`
- Gracefully handles multiline mode (no-op)

**Multiline Mode Handling**
- History preserved when switching to multiline
- Restored when switching back to single-line
- Uses `preserve_history` parameter in `switch_to_singleline()`

### App Integration

In `on_input_submitted()`:
```python
# Add to history (for arrow key navigation)
input_bar.add_to_history(user_input)

# Clear input
input_bar.clear_input()
```

## Usage Examples

### Example 1: Basic Navigation

```
> list todos            [Press Enter]
> search meeting        [Press Enter]
> create todo review PR [Press Enter]
> [Press Up]            → "create todo review PR"
> [Press Up]            → "search meeting"
> [Press Up]            → "list todos"
> [Press Up]            → "list todos" (at oldest)
> [Press Down]          → "search meeting"
> [Press Down]          → "create todo review PR"
> [Press Down]          → "" (back to empty)
```

### Example 2: Draft Preservation

```
> list todos            [Press Enter]
> [Type: "show me t"]   (not submitted)
> [Press Up]            → Switches to "list todos", saves "show me t"
> [Press Down]          → Returns to "show me t" (draft restored)
```

### Example 3: Editing Recalled Messages

```
> create todo review design doc    [Press Enter]
> [Press Up]                        → "create todo review design doc"
> [Edit to:]  "create todo review API doc"
> [Press Enter]                     → Submits edited version
```

### Example 4: Duplicate Prevention

```
> /list            [Press Enter]
> /list            [Press Enter]  (duplicate, not added)
> [Press Up]       → "/list"
> [Press Up]       → "/list" (no second copy)
```

## Technical Details

### Event Handling

**Key Interception:**
```python
def _on_key(self, event: events.Key) -> None:
    if event.key == "up":
        # Handle up navigation
        event.prevent_default()  # Don't move cursor up
        event.stop()             # Don't propagate event
```

**Cursor Management:**
```python
self.value = self.message_history[self.history_index]
self.cursor_position = len(self.value)  # Move to end
```

### History State Machine

```
Initial State: history_index = -1 (not navigating)

On first Up press:
  - Save current input to current_draft
  - Set history_index = len(history) (conceptually "after last")
  - Decrement and show message

On subsequent Up press:
  - Decrement history_index (if > 0)
  - Show older message

On Down press:
  - Increment history_index
  - If >= len(history):
    - Restore current_draft
    - Reset to -1
  - Else:
    - Show newer message

On submit:
  - Reset history_index to -1
  - Clear current_draft
```

### Edge Cases Handled

1. **Empty History**
   - Up arrow does nothing if no history exists
   - Down arrow does nothing if not navigating

2. **At History Boundaries**
   - Up at oldest: stays at oldest
   - Down at newest: restores draft and exits navigation

3. **Multiline Mode**
   - Arrow keys not intercepted in multiline (TextArea)
   - History preserved for when returning to single-line

4. **History Preservation**
   - When switching modes, history is copied to new widget
   - Prevents loss of history during mode changes

## Configuration

### Adjusting History Size

Currently unlimited history. To add a limit:

```python
class HistoryInput(Input):
    MAX_HISTORY_SIZE = 100  # Add this

    def add_to_history(self, message: str):
        if message and message.strip():
            if not self.message_history or self.message_history[-1] != message:
                self.message_history.append(message)

                # Add this limit
                if len(self.message_history) > self.MAX_HISTORY_SIZE:
                    self.message_history.pop(0)  # Remove oldest
```

### Disabling Feature

To disable history navigation (keep the widget but no history):

```python
# In compose():
yield Input(  # Use regular Input instead of HistoryInput
    placeholder="Type a message or /command...",
    id="user-input",
)
```

## Keyboard Shortcuts Reference

| Key | Action |
|-----|--------|
| ↑ (Up) | Navigate to previous (older) message |
| ↓ (Down) | Navigate to next (newer) message |
| Enter | Submit current message |
| Escape | (Standard Textual behavior - no special handling) |

## Comparison with Shell History

### Similar To Bash/Zsh
- Up/Down navigation
- Duplicate prevention
- Cursor positioning at end

### Different From Shells
- No persistent history (cleared on restart)
- No history search (Ctrl+R equivalent)
- No history file (~/.bash_history)
- No history expansion (!!, !$, etc.)
- No history size limit by default

### Similar To Claude Code
- Up/Down navigation pattern
- Draft preservation
- In-memory only (no persistence)

## Future Enhancements

Potential improvements (not implemented):

1. **Persistent History**
   - Save to file (~/.terminal-todos/history)
   - Load on startup
   - Configurable max size

2. **History Search**
   - Ctrl+R for reverse search
   - Fuzzy matching
   - Search as you type

3. **Smart Filtering**
   - Filter by command type (/commands vs natural language)
   - Filter by date/time
   - Show only successful commands

4. **History Management Commands**
   - `/history` - Show full history list
   - `/clear-input-history` - Clear message history
   - `/history-size` - Show count

5. **Session History**
   - Group by app session
   - Export history to file
   - Import from file

6. **Context-Aware History**
   - Different history for different modes
   - Prioritize relevant commands based on context

## Testing

### Manual Test Cases

**Test 1: Basic Navigation**
```
1. Send 3 different messages
2. Press Up 3 times
3. Should show messages in reverse order
4. Press Down 3 times
5. Should return to empty input
```

**Test 2: Draft Preservation**
```
1. Send a message
2. Start typing a new message (don't submit)
3. Press Up (should show old message)
4. Press Down (should restore your draft)
```

**Test 3: Duplicate Prevention**
```
1. Send "test" twice
2. Press Up once
3. Should only show "test" once in history
```

**Test 4: Multiline Mode**
```
1. Send 2 messages
2. Enter /capture (multiline mode)
3. Exit multiline mode
4. Press Up
5. Should still show previous messages
```

**Test 5: Cursor Positioning**
```
1. Send a long message
2. Press Up
3. Cursor should be at end (not beginning)
4. Can immediately backspace or add text
```

## Debugging

If history isn't working:

1. **Check if HistoryInput is being used:**
   ```python
   input_widget = app.query_one("#user-input")
   print(type(input_widget))  # Should be HistoryInput
   ```

2. **Check history contents:**
   ```python
   print(input_widget.message_history)
   ```

3. **Check navigation state:**
   ```python
   print(f"Index: {input_widget.history_index}")
   print(f"Draft: {input_widget.current_draft}")
   ```

4. **Verify add_to_history is called:**
   - Add logging in `on_input_submitted`
   - Should see history additions after each submit

## Summary

This feature provides intuitive command history navigation using arrow keys, making it easy to:
- Rerun previous commands
- Edit and resubmit variations of commands
- Avoid retyping long messages
- Work faster with repeated operations

The implementation closely matches the behavior of Claude Code's input history, providing a familiar and efficient user experience.
