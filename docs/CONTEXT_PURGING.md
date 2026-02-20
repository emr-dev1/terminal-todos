# Conversation Context Purging

## Overview

Automatic purging of confirmation and transactional context from conversation history to prevent cross-contamination between different operations.

## Problem Solved

**Before Purging:**
```
User: "delete all todos without a due date"
Agent: "Found 5 todos. Delete them? [yes/no]"
User: "yes"
Agent: *Deletes 5 todos*

User: "I completed todo 9"
Agent: *Still has deletion context in memory*
       *May get confused about what "them" or "it" refers to*
       *Unnecessarily long context*
```

**After Purging:**
```
User: "delete all todos without a due date"
Agent: "Found 5 todos. Delete them? [yes/no]"
User: "yes"
Agent: *Deletes 5 todos*
       *PURGES the deletion confirmation exchange*

User: "I completed todo 9"
Agent: *Fresh context, no deletion talk*
       *Focused only on completion request*
```

## How It Works

### Automatic Purging

After certain operations complete, the system automatically removes the last 2 conversation turns:

1. **Turn 1:** User's request + Agent's tool execution + Agent's confirmation question
2. **Turn 2:** User's confirmation response

This removes transactional context while preserving earlier conversation.

### Operations That Trigger Purging

#### 1. Todo Extraction Confirmation
**When:** After `/capture` completes or is cancelled
**What's purged:**
- The extraction results preview
- User's yes/no confirmation
- Tool calls for creating todos

**Example:**
```
[Kept] User: "Here are my meeting notes..."
[Kept] Agent: "I found 3 todos from your notes"
[PURGED] Agent: "Create these todos? [yes/no]"
[PURGED] User: "yes"
[PURGED] System: "✓ Created 3 todos"
```

#### 2. Deletion Confirmation
**When:** After deletion completes or is cancelled
**What's purged:**
- The deletion preview
- User's yes/no confirmation
- Tool calls for deleting todos

**Example:**
```
[Kept] User: "delete todos without due dates"
[Kept] Agent: "Found 5 todos without due dates: ..."
[PURGED] Agent: "Delete these 5 todos? [yes/no]"
[PURGED] User: "yes"
[PURGED] System: "✗ Deleted 5 todos"
```

#### 3. Import Confirmation
**When:** After `/import` completes or is cancelled
**What's purged:**
- The note preview with metadata
- Tag input exchange
- User's final yes/no confirmation
- Bulk import operation

**Example:**
```
[Kept] Nothing (import is initiated via command)
[PURGED] System: "📦 REVIEW EXTRACTED NOTES (3 found)"
[PURGED] User: "Client-A, ProjectBeta"
[PURGED] System: "Review and confirm"
[PURGED] User: "yes"
[PURGED] System: "✅ Imported 3 notes"
```

## Technical Implementation

### Methods

**`purge_recent_conversation(num_turns: int = 1)`**
- Removes the last N conversation turns
- A turn = HumanMessage + [ToolMessages] + AIMessage
- Walks backwards through history
- Removes all messages in those turns

**`purge_confirmation_context()`**
- Convenience method that purges 2 turns
- Specifically designed for confirmation workflows
- Called automatically after confirmations

### Message Structure

A conversation turn consists of:
```
1. HumanMessage - User's input
2. [ToolMessage(s)] - Optional tool executions
3. AIMessage - Agent's response
```

Purging removes all these message types for the specified turns.

### Code Locations

Purging is called in:
- `handle_natural_language()` after extraction confirmation (line ~1012, 1023)
- `handle_natural_language()` after deletion confirmation (line ~1077, 1087)
- `_create_pending_import()` after import completes (line ~984)
- `handle_natural_language()` after import confirmation cancelled (line ~1154)

## What Gets Kept

### General Conversation
```
User: "what's on my todo list?"
Agent: "You have 5 open todos..."
User: "show me completed todos"
Agent: "Here are your 10 completed todos..."
```
✅ **Kept** - General queries and responses stay in history

### Recent Context (Before Confirmation)
```
User: "delete old todos"
Agent: *Searches and finds todos*
Agent: "Found 3 old todos..."
```
✅ **Kept** - The initial request and search results are preserved

### Only Purged: Confirmation Exchange
```
Agent: "Delete these? [yes/no]"
User: "yes"
System: "Deleted 3 todos"
```
❌ **Purged** - Only the confirmation exchange is removed

## Benefits

### 1. Context Isolation
Each new request starts with clean context about completed operations

### 2. Reduced Token Usage
Fewer messages in history = lower API costs

### 3. Improved Agent Focus
Agent doesn't get distracted by irrelevant past confirmations

### 4. Better UX
Users can chain operations without worrying about context pollution

## Example Scenarios

### Scenario 1: Multiple Deletions

```
User: "delete todos without due dates"
Agent: "Found 5 todos. Delete? [yes/no]"
User: "yes"
System: ✗ Deleted 5 todos
[PURGE - Removes last 2 turns]

User: "delete completed todos"
Agent: "Found 8 completed todos. Delete? [yes/no]"
        ^-- No memory of previous deletion
User: "yes"
System: ✗ Deleted 8 todos
[PURGE - Removes last 2 turns]
```

### Scenario 2: Deletion Then Update

```
User: "delete overdue todos"
Agent: "Found 2 overdue. Delete? [yes/no]"
User: "yes"
System: ✗ Deleted 2 todos
[PURGE]

User: "mark todo 5 as complete"
Agent: ✓ Marked todo #5 as complete
        ^-- No confusion about "todo 5" vs deleted todos
```

### Scenario 3: Import Then Query

```
User: /import
[Paste notes]
System: "Review 3 notes. Tags?"
User: "Client-A"
System: "Confirm import?"
User: "yes"
System: ✅ Imported 3 notes
[PURGE]

User: "show me my notes"
Agent: [Lists all notes]
        ^-- No import context bleeding into query
```

## Manual Purging

### Using `/clear-history` Command

Clears ALL conversation history:
```
/clear-history
```

Use when:
- Switching to completely different topic
- After a series of operations
- When context feels "polluted"

### Difference from `/clear`

- `/clear` - Only clears visual chat log (history preserved)
- `/clear-history` - Clears conversation history (chat log preserved)

## Debugging

### With Verbose Logging Enabled

When `VERBOSE_LOGGING=true`, you'll see:

```
INFO: Purging confirmation context from conversation history
DEBUG: Purged message from history
  - type: HumanMessage
  - content_preview: yes
DEBUG: Purged message from history
  - type: AIMessage
  - content_preview: Found 5 todos without due dates. Would you like...
INFO: Purged 2 conversation turn(s), removed 4 messages
```

### Check History State

Use `/history` command:
```
> /history
📝 Conversation History: 6 total messages (3 user, 3 assistant)
```

After purging, the count should decrease.

## Configuration

### Adjust Purge Depth

To purge more or fewer turns:

```python
# In confirmation handlers, change:
self.purge_confirmation_context()  # Purges 2 turns

# To:
self.purge_recent_conversation(num_turns=3)  # Purges 3 turns
```

### Disable Purging

Comment out purge calls in:
- Line ~1012 (extraction yes)
- Line ~1023 (extraction no)
- Line ~1077 (deletion yes)
- Line ~1087 (deletion no)
- Line ~984 (import success)
- Line ~1154 (import cancel)

## Future Enhancements

Potential improvements (not implemented):

1. **Selective Purging**
   - Keep user request but purge agent response
   - More granular control

2. **Smart Purging**
   - Analyze message relevance
   - Keep important context
   - Purge only noise

3. **Configurable Purging**
   - Per-operation purge settings
   - User preference for retention
   - Automatic vs manual mode

4. **Purge History Log**
   - Track what was purged
   - Undo purge if needed
   - Review purged context

## Best Practices

### When to Purge

✅ **Do purge after:**
- Confirmation workflows complete
- Destructive operations (delete, update many)
- Bulk operations (import, bulk create)
- User explicitly confirms action

❌ **Don't purge after:**
- Simple queries (list, search)
- Single todo operations (mark one complete)
- Informational requests
- Failed operations (errors)

### Conversation Flow

```
[General conversation]
  ↓
[Transactional operation starts]
  ↓
[Confirmation exchange]
  ↓
[Action completes]
  ↓
[PURGE - Clean slate]
  ↓
[Next operation - Fresh context]
```

## Summary

Automatic context purging ensures that confirmation workflows don't pollute future interactions. After completing a deletion, import, or extraction, the system removes that transactional context, allowing the next request to be processed with clean, relevant history.

This improves:
- Agent accuracy and focus
- User experience (no cross-contamination)
- Token efficiency (smaller context)
- Conversation clarity (less noise)
