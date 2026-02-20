# New Features Added

## 🎉 Latest Updates (2026-01-14)

### 8. **Multi-Line Input for Capture Mode** 📋
- Single-line input by default for quick messages
- Automatically switches to multi-line when you use `/capture`
- Perfect for pasting large blocks of meeting notes or Slack messages
- Press **Ctrl+Enter** to submit your captured notes
- Automatically switches back to single-line after processing

### 8a. **Slack Message Filtering** 💬
- Automatically filters out timestamps from pasted Slack messages
- Filters out your name (set via `USER_NAME` environment variable)
- Just paste raw Slack conversation - the AI knows what to ignore
- Focuses only on actual action items and content

**How to set your name:**
Add to your `.env` file:
```
USER_NAME=Ed Robinson
```

The extraction will automatically ignore lines with your name and timestamps!

### 9. **Notes Management Commands** 📝
New slash commands for working with your saved notes:
- `/notes [limit]` - List recent notes (default: 10)
- `/note <id>` - View full content of a specific note
- `/delnote <id>` - Delete a note by ID

### 10. **Agent Note Management** 🤖
The AI agent can now help you manage notes:
- "show me my notes"
- "what's in note 5?"
- "delete note 3"
- Agent has access to `list_notes`, `get_note`, and `delete_note` tools

### 11. **Conversational Todo Editing** ✏️
You can now update todos conversationally:
- "update the design review todo and make it due friday"
- "change the PR review to high priority"
- "update todo 5 and make it due next week"
- Agent finds the todo, confirms with you, then updates it

**What can be updated:**
- Content/description
- Due date (natural language like "friday", "next week")
- Priority (normal, high, urgent)

**New tools:**
- `find_todos_to_update` - Searches for todos to update
- `update_todo` - Updates todo properties

### 12. **Improved Agent Guidance** 💡
- Agent now explicitly tells you when it can't do something
- Suggests alternative actions within its capabilities
- Example: "I can't send emails, but I can set a due date reminder"
- Better clarity on system limitations

### 13. **Markdown Rendering in Chat** 📄
- All assistant responses now render markdown properly
- **Bold**, *italic*, `code blocks`, lists, headers all work
- Beautiful formatting for notes and long responses
- Makes reading complex information much easier

## ✅ Previously Implemented Features

### 1. **Text Wrap in Chat Window** ✨
- Chat messages now wrap properly instead of truncating
- Long responses from the AI agent are easier to read
- Multi-line messages display correctly

### 2. **Semantic Search with Confirmation** 🔍
When you say "I completed the design review" or "I finished the API work":
- Agent uses semantic search to find matching todos
- Shows you the matches with relevance scores
- Asks for confirmation before marking as complete
- Handles multiple matches intelligently

**Examples:**
```
I finished the design review
→ Agent finds matching todos and confirms before completing

I completed all the PR reviews
→ Agent shows all matching PR-related todos and asks which ones
```

### 3. **Due Dates & Calendar Functionality** 📅

#### Setting Due Dates
You can now set due dates using natural language:
```
create a todo to review the design doc due tomorrow
add a task to send the report due next friday
remind me to call the client due january 20th
```

#### Date Groups in Left Pane
Todos are now organized by date sections:
- **⚠️ OVERDUE** (red) - Past due dates
- **📅 TODAY** (yellow) - Due today
- **📅 TOMORROW** (cyan) - Due tomorrow
- **📅 THIS WEEK** - Due within 7 days
- **📋 NO DUE DATE** - No deadline set
- **✓ COMPLETED** - Finished tasks

#### Visual Due Date Indicators
Each todo shows its due date status:
- `📅 today` - Due today
- `📅 tomorrow` - Due tomorrow
- `📅 01/15` - Due on a specific date
- `⚠️ 3d overdue` - 3 days overdue

#### Overdue Highlighting
- Overdue todos appear in **red**
- High priority todos appear in **yellow**
- Urgent todos appear in **red**
- Regular todos appear in **white**

### 4. **Enhanced Agent Tools** 🤖

#### New Tool: `find_todos_to_complete`
- Searches for todos when you say you completed something
- Returns matches with relevance scores
- Asks for confirmation before completing

#### Updated: `create_todo`
- Now supports `due_date` parameter
- Accepts natural language dates ("tomorrow", "next week", "jan 20")
- Also accepts ISO format dates (YYYY-MM-DD)

### 5. **Natural Language Date Parsing** 🗓️
Uses `dateparser` library to understand dates:
- **Relative**: "tomorrow", "next week", "in 3 days"
- **Specific**: "january 20th", "jan 20", "2026-01-20"
- **Day names**: "monday", "next friday"

### 6. **Smart Todo Organization** 📊
The left pane now groups todos logically:
1. Shows overdue items first (most urgent)
2. Then today's tasks
3. Then tomorrow's tasks
4. Then this week's tasks
5. Then items without due dates
6. Finally completed items (last 10)

### 7. **Database Migration** 🔧
- Automatically adds `due_date` column to existing databases
- Migration runs on startup
- No data loss - your existing todos are preserved

## How to Use

### Natural Language Examples

**Creating todos with due dates:**
```
create a todo to review the design due tomorrow
add a task to send the weekly report due next friday
remind me to call the client on january 20th
```

**Completing todos:**
```
I finished the design review
→ Agent: "Found 1 todo: #5: Review design mockups. Should I mark this as complete?"
→ You: "yes"
→ Agent marks it complete ✓

I completed the API work
→ Agent: "I found 3 todos matching 'API work': ..."
→ You: "1 and 2"
→ Agent completes those specific ones
```

**Updating todos (NEW):**
```
update the design review and make it due friday
→ Agent: "✓ Updated todo #5: Changed due date to 2026-01-17"

change the PR review to high priority
→ Agent: "✓ Updated todo #3: Changed priority to high"

update todo 5 and change the description to "Complete design review with feedback"
→ Agent: "✓ Updated todo #5: Changed content to 'Complete design review with feedback'"
```

**Managing notes (NEW):**
```
show me my notes
→ Agent lists recent notes with previews

what's in note 5?
→ Agent shows full content of note #5

delete note 3
→ Agent: "✗ Deleted note #3: Meeting Notes"
```

**Viewing by date:**
```
what do I need to do today?
show me overdue tasks
what's due this week?
```

### Slash Commands

**Create with due date:**
```
/todo Review PR #123 due tomorrow
```

**Work with notes:**
```
/notes          # List recent notes
/notes 20       # List 20 notes
/note 5         # View note #5
/delnote 3      # Delete note #3
```

**Capture mode (multi-line input):**
```
/capture              # Enters multi-line mode

[Paste raw Slack messages or notes:]
10:30 AM Ed Robinson
Let's schedule the design review

10:31 AM Jane Smith
Sounds good, I'll send the invite

Ed Robinson 10:32 AM
Also need to follow up on PR #123

[Press Ctrl+Enter to submit]

→ Filters out timestamps and "Ed Robinson"
→ Extracts action items: "Schedule design review", "Follow up on PR #123"
→ Returns to single-line input
```

**Search:**
```
/search design review
```

## Technical Details

### Database Schema
- Added `due_date` column (DateTime, nullable) to `todos` table
- Migration v2 automatically updates existing databases

### New Repository Methods
- `list_due_today()` - Get today's todos
- `list_due_this_week()` - Get this week's todos
- `list_overdue()` - Get overdue todos
- `list_no_due_date()` - Get todos without due dates
- `update_due_date()` - Update a todo's due date

### New Service Methods
- `TodoService.create_todo()` - Now accepts `due_date` parameter
- `TodoService.update_due_date()` - Update due dates
- Date-based query methods matching repository

### New Dependencies
- `dateparser>=1.2.0` - Natural language date parsing

## Installation

If you haven't updated your dependencies:
```bash
conda activate terminal-todos
pip install -e .
```

The `dateparser` library will be installed automatically.

## Notes

- **Overdue tasks** are highlighted in red for visibility
- **Today's tasks** are highlighted in yellow
- **Due dates** are shown with emoji indicators for quick scanning
- **Grouping** helps you focus on what's most important
- **Confirmation flow** prevents accidentally completing the wrong tasks
- **Natural language** makes it easy to set dates without remembering formats

Enjoy your enhanced terminal todos app! 🎉
