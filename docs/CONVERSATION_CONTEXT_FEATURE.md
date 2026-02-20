# Conversation Context Management Feature

## Overview

Added full conversation history management to enable the agent to maintain context across multiple turns of conversation. This fixes the issue where the agent would forget previous context and ask for clarification on follow-up messages.

## Problem Solved

**Before:**
```
User: "delete all todos that do not have a due date"
Agent: "Found 5 todos without due dates: [list]. Would you like me to delete them?"
User: "delete"
Agent: "It seems like you want to delete something, but I need more information..."
```

**After:**
```
User: "delete all todos that do not have a due date"
Agent: "Found 5 todos without due dates: [list]. Would you like me to delete them?"
User: "delete"
Agent: "Deleting the 5 todos without due dates..." [remembers context]
```

## Implementation Details

### 1. Conversation History State

Added to `TerminalTodosApp.__init__()`:
```python
self.conversation_history = []  # List of BaseMessage objects
self.max_history_messages = 20  # Keep last N messages to avoid token limits
```

### 2. History Management Methods

**`add_to_conversation_history(message)`**
- Appends message to history
- Auto-truncates to `max_history_messages` to avoid token limit issues
- Logs operations when verbose logging is enabled

**`clear_conversation_history()`**
- Resets conversation history to empty list
- Useful when starting a new topic or after a break

**`get_conversation_summary()`**
- Returns string summary: "N total messages (X user, Y assistant)"
- Useful for debugging and user feedback

### 3. Updated Agent Invocation

**Both agent methods updated:**
- `_call_agent()` - Synchronous invocation
- `_call_agent_with_progress()` - Streaming invocation with progress

**Changes:**
1. Add user message to history before calling agent
2. Pass full `self.conversation_history` instead of just `[human_message]`
3. Extract AI response from result and add to history
4. Avoid duplicates when adding messages

**Example (simplified):**
```python
# Before
result = self.agent_graph.invoke({"messages": [human_message]})

# After
self.add_to_conversation_history(human_message)
result = self.agent_graph.invoke({"messages": self.conversation_history})
# Extract and add AI response to history
```

### 4. New Slash Commands

**`/history`**
- Shows conversation history summary
- Example output: "📝 Conversation History: 8 total messages (4 user, 4 assistant)"

**`/clear-history`**
- Clears conversation history completely
- Agent will start fresh on next message
- Useful when switching contexts or starting new task

**`/clear` (updated)**
- Now only clears visual chat log
- Does NOT clear conversation history
- History persists for context continuity

## How It Works

### Message Flow

1. **User sends message** → Added to `conversation_history`
2. **Agent invoked with full history** → LangGraph receives all previous messages
3. **Agent processes with context** → Can reference previous turns
4. **AI response extracted** → Added to `conversation_history`
5. **Display to user** → Visual output shown in chat log

### LangGraph Integration

LangGraph's `AgentState` uses `add_messages` annotation:
```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

This handles message accumulation automatically within a single graph invocation. By passing the full history, we maintain context across multiple invocations.

### Memory Management

- **Max Messages:** Default 20 messages (10 turns of conversation)
- **Auto-Truncation:** Oldest messages removed when limit exceeded
- **Token Awareness:** Prevents hitting API token limits
- **Manual Control:** `/clear-history` command for explicit reset

## Usage Examples

### Example 1: Multi-Turn Deletion

```
User: show me all todos without due dates
Agent: Found 5 todos without due dates:
  - Todo #12: Review PR
  - Todo #15: Email client
  ...

User: delete them
Agent: [Understands "them" refers to the 5 todos from previous message]
      Deleting 5 todos...
```

### Example 2: Follow-Up Questions

```
User: what's my progress on the API project?
Agent: You have 3 open todos for the API project:
  - Implement authentication
  - Add rate limiting
  - Write API docs

User: mark the first one as done
Agent: [Knows "first one" = "Implement authentication" from previous context]
      ✓ Marked "Implement authentication" as complete
```

### Example 3: Context Switching

```
User: show me meeting todos
Agent: You have 2 meeting-related todos...

User: /clear-history
System: ✓ Conversation history cleared - agent will start fresh

User: show me API todos
Agent: [No memory of previous meeting discussion]
      You have 3 API-related todos...
```

## Verbose Logging Output

When `VERBOSE_LOGGING=true` in `.env`:

```
ℹ️  INFO: Calling agent (streaming) with 6 messages in history
🔍 DEBUG: Conversation history now has 7 messages
🔍 DEBUG: Added AI response to history from streaming: You have 5 todos without due dates. Would you like me to delete them?...
```

## Configuration

### Adjusting History Size

In `TerminalTodosApp.__init__()`:
```python
self.max_history_messages = 20  # Increase or decrease as needed
```

**Considerations:**
- **Higher limit** = More context, but higher API costs and potential token limits
- **Lower limit** = Less context, but cheaper and faster
- **Recommended:** 20 messages (10 conversation turns) balances context and efficiency

### Disabling Truncation

Set to a very high number to effectively disable:
```python
self.max_history_messages = 1000  # Effectively unlimited for most sessions
```

## Testing the Feature

### Test Scenario 1: Context Preservation

1. Start app: `terminal-todos`
2. Say: "list all todos without due dates"
3. Wait for response with list
4. Say: "delete them all"
5. **Expected:** Agent understands "them" refers to previous list

### Test Scenario 2: History Commands

1. Start app
2. Have a conversation (3-4 turns)
3. Type: `/history`
4. **Expected:** Shows message count (e.g., "8 total messages (4 user, 4 assistant)")
5. Type: `/clear-history`
6. **Expected:** "✓ Conversation history cleared"
7. Type: `/history`
8. **Expected:** "0 total messages (0 user, 0 assistant)"

### Test Scenario 3: Memory Truncation

1. Set `VERBOSE_LOGGING=true` in `.env`
2. Set `max_history_messages = 4` (for testing)
3. Have 3 conversation turns (6 messages)
4. **Expected in logs:** "Truncated conversation history, removed 2 old messages"

## Technical Notes

- **Thread Safety:** Not required - Textual is single-threaded
- **Persistence:** History is in-memory only, cleared on app restart
- **Message Types:** Handles `HumanMessage`, `AIMessage`, and `ToolMessage`
- **Deduplication:** Checks `message not in history` to avoid duplicates

## Future Enhancements

Potential improvements (not implemented):

1. **Persistent History:** Save to database, reload on app start
2. **Smart Truncation:** Remove older tool calls but keep conversation
3. **Context Summarization:** Compress old messages using LLM summarization
4. **Multiple Conversations:** Support named conversation threads
5. **Export History:** Save conversation to file for reference
6. **Token Counting:** More precise limits based on actual token usage

## Debugging Tips

If context isn't working:

1. **Enable verbose logging:**
   ```bash
   echo "VERBOSE_LOGGING=true" >> .env
   ```

2. **Check history state:**
   ```
   /history
   ```

3. **Look for log output:**
   - "Calling agent with N messages in history"
   - "Added AI response to history"
   - "Truncated conversation history"

4. **Verify message structure:**
   - Messages should alternate: Human → AI → Human → AI
   - Tool messages appear between AI messages

5. **Clear if stuck:**
   ```
   /clear-history
   ```

## Context Purging

To prevent cross-contamination between operations, the system automatically purges confirmation context after completing transactional operations.

**What gets purged:**
- Deletion confirmations
- Todo extraction confirmations
- Import confirmations

**When it's purged:**
- After user confirms (yes)
- After user cancels (no)

**What stays:**
- General conversation
- Initial requests
- Query results

**Example:**
```
User: "delete todos without due dates"
Agent: "Found 5. Delete? [yes/no]"
User: "yes"
[Deletion completes]
[PURGE - Removes last 2 turns]

User: "I completed todo 9"
[Agent has NO memory of deletion, focuses on completion]
```

See [CONTEXT_PURGING.md](CONTEXT_PURGING.md) for complete documentation.

## Summary

This feature enables natural, multi-turn conversations with the agent by maintaining full conversation context while automatically purging transactional confirmations. The agent can now understand pronouns ("them", "it", "that"), follow-up questions, and references to previous messages, while preventing confirmation workflows from polluting future interactions.
