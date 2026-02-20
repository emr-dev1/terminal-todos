# 🔧 Conversational Todo Updates - Fixes Applied

## ✅ What Was Fixed

### 1. **Clearer Agent Instructions** 📝
Updated the system prompt to make the update workflow crystal clear:

**Before:** Agent wasn't sure when to proceed vs. when to ask for confirmation
**After:** Explicit instructions with examples showing:
- If user specifies what to change → proceed immediately
- If user doesn't specify → ask what to change

**Example Flow:**
```
User: "Update the presentation slides todo to be due this friday"
Agent:
  1. Calls find_todos_to_update("presentation slides")
  2. Gets: "Found todo #7: Complete presentation slides"
  3. Immediately calls update_todo(7, due_date="this friday")
  4. Returns: "✓ Updated todo #7: Changed due date to 2026-01-17"
```

### 2. **Improved Tool Response Format** 🛠️
The `find_todos_to_update` tool now returns clearer responses:

**Before:** "Found 1 todo: #5: presentation slides. What would you like to update?"
**After:** "Found todo #5: Complete presentation slides for client presentation"

This makes it obvious to the agent what the ID is and allows it to proceed directly.

### 3. **Fixed Database Session Issues** 💾
**Root Cause:** Shared database sessions across tool calls causing "fds_to_keep" errors

**The Fix:**
- Each tool now creates a **fresh** service instance
- All tools wrapped in `try/finally` blocks
- Services always closed after use
- No more shared sessions = no more file descriptor errors

**Applied to tools:**
- create_todo
- update_todo
- complete_todo
- find_todos_to_update
- find_todos_to_complete
- All note tools

### 4. **Better Date Parsing** 📅
- Handles both natural language ("this friday", "next week") and ISO format
- Graceful fallback if dateparser isn't available
- Clear error messages when dates can't be parsed

## 🎯 Now You Can Say:

### Creating with due dates:
```
"Can you add a todo for me to complete the presentation slides by this friday"
→ ✓ Created todo with due date
```

### Updating due dates:
```
"Update the presentation slides todo to be due next monday"
→ Finds todo → Updates immediately → Confirms

"Change the design review to be due this friday"
→ ✓ Updated due date
```

### Updating priority:
```
"Change the PR review to high priority"
→ ✓ Updated priority to high

"Make the client meeting urgent"
→ ✓ Updated priority to urgent
```

### Updating content:
```
"Update the design review todo to say 'Complete design review with feedback'"
→ ✓ Updated content
```

### Complex updates:
```
"Update the presentation slides to be high priority and due this friday"
→ ✓ Updated priority and due date
```

## 🔑 Key Changes

### System Prompt (`src/terminal_todos/agent/prompts.py`)
- Added explicit workflow for updates with user-specified changes
- Added concrete examples showing the expected flow
- Clarified when to confirm vs. proceed immediately

### Tool Improvements (`src/terminal_todos/agent/tools.py`)
- `find_todos_to_update`: Returns structured ID in clear format
- `get_todo_service()`: Always creates fresh instances
- All tools: Wrapped in try/finally for cleanup
- Better error messages throughout

### Result
✅ No more "fds_to_keep" errors
✅ Smooth conversational updates
✅ Agent proceeds immediately when changes are specified
✅ Proper confirmation flow when needed
✅ All database sessions properly cleaned up

## 🧪 Test These Scenarios:

1. **Simple due date update:**
   - "Update the slides todo to be due friday"

2. **Priority update:**
   - "Make the client meeting high priority"

3. **Content update:**
   - "Change the PR review todo to say 'Review PR #123 with comments'"

4. **Multiple updates:**
   - "Update the design review to be urgent and due next week"

5. **Ambiguous match:**
   - "Update the meeting todo to be due friday"
   - (Agent should show you multiple matches if there are several)

All of these should now work smoothly without errors!
