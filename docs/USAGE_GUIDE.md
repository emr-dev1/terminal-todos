# Terminal Todos - Usage Guide

## 🚀 Quick Start

After installing and setting up your `.env` file with your OpenAI API key, run:

```bash
terminal-todos
```

You'll see a three-pane interface:
- **Left**: Your todo list (active and completed)
- **Right**: Chat log and AI responses
- **Bottom**: Input bar

## 💬 Natural Language Examples

The primary way to use Terminal Todos is through natural language. Just type your request!

### Creating Todos

```
create a todo to review the design document
add a task to send the weekly update email
remind me to call the client tomorrow
```

### Viewing Todos

```
what do I need to do today?
show me all my active todos
what's on my plate?
list my completed tasks
```

### Completing Todos

```
mark the design review as done
I finished the email task
complete todo number 3
```

### Searching

```
show me todos about the API
what tasks do I have related to meetings?
find todos with "urgent" priority
```

### Getting Statistics

```
how many todos do I have?
what's my progress?
show me my todo stats
```

## 📝 Capture Mode - Extract Todos from Notes

This is the killer feature! Paste your meeting notes and let AI extract action items.

### Example: Meeting Notes

1. Type `/capture`
2. Paste your notes:

```
Meeting with Product Team - Jan 15, 2026

Discussed Q1 roadmap and priorities:
- Need to finalize API specifications by end of week
- Schedule design review session with team members
- Update documentation for new features
- Sarah will send out meeting notes
- Follow up with engineering team on timeline

Decisions:
- Moving forward with REST approach
- Using JWT for authentication

Action items:
- Review and approve final mockups (high priority)
- Set up CI/CD pipeline
- Create tickets in Jira for each feature
```

3. Type `END`

**Result**: AI extracts 6 todos with appropriate priorities:
- ○ #1: Finalize API specifications by end of week [HIGH]
- ○ #2: Schedule design review session with team members
- ○ #3: Update documentation for new features
- ○ #4: Follow up with engineering team on timeline
- ○ #5: Review and approve final mockups [URGENT]
- ○ #6: Set up CI/CD pipeline
- ○ #7: Create tickets in Jira for each feature

### Example: Quick Notes

```
/capture
Random thoughts:
- Need to refactor the authentication module
- Consider adding caching layer
- Talk to team about performance issues
END
```

**Result**: 3 todos extracted!

## 🔍 Semantic Search

Search using natural meaning, not just keywords:

### Using `/search` command

```bash
/search design          # Finds: "Review UI mockups", "Design meeting", "Finalize designs"
/search urgent          # Finds high-priority items
/search meeting         # Finds: "Schedule review", "Prepare presentation", "Send notes"
```

### Using Natural Language

```
show me todos about the API redesign
find tasks related to documentation
what todos mention performance?
```

The AI understands context and finds semantically similar items!

## ⚡ Quick Commands Reference

### Creating & Managing

| What you want | Command | Natural Language |
|---------------|---------|------------------|
| Create todo | `/todo Review PR #123` | "create a todo to review PR 123" |
| Mark done | `/done 5` | "mark todo 5 as done" |
| List todos | `/list open` | "show me open todos" |
| Search | `/search API` | "find todos about API" |
| Get stats | `/stats` | "how many todos do I have?" |

### Capture & Extract

```bash
/capture
# Paste your notes (multiple lines)
# Type END when done
END
```

### Utility

```bash
/clear          # Clear chat log
/help           # Show help
/quit           # Exit app
```

## ⌨️ Keyboard Shortcuts

- `Ctrl+R` - Refresh todo list
- `Ctrl+L` - Clear chat log
- `Ctrl+C` or `Ctrl+Q` - Quit application
- `/` - Start typing a command

## 🎯 Tips & Best Practices

### 1. Use Natural Language for Everything

Instead of memorizing commands, just talk to the app:
- ❌ Don't: `/todo Buy milk /done 3 /list open`
- ✅ Do: "add buy milk to my list, also mark todo 3 as done, then show me what's left"

### 2. Capture Notes Regularly

After every meeting or brainstorm session:
```
/capture
[paste notes]
END
```

The AI will extract action items with priorities automatically!

### 3. Use Semantic Search

Don't worry about exact wording:
- Search "urgent" to find high-priority items
- Search "meeting" to find meeting-related tasks
- Search "deadline" to find time-sensitive work

### 4. Ask for Context

```
what did we decide about the API?
show me notes from yesterday's meeting
what's the status of the redesign project?
```

### 5. Batch Operations

```
create todos for: review docs, test feature, update readme
mark todos 5, 6, and 7 as complete
```

## 🐛 Troubleshooting

### Agent not responding?

Check your `.env` file has valid `OPENAI_API_KEY`:
```bash
cat .env
# Should show: OPENAI_API_KEY=sk-...
```

### Todos not updating?

Refresh with `Ctrl+R` or type:
```
refresh my todo list
```

### Extraction not working?

Make sure you:
1. Type `/capture`
2. Paste your notes
3. Type `END` on a new line (case insensitive)

### Search returns nothing?

Try:
- More specific queries
- Natural language: "show me todos about X"
- List all todos first with `/list all`

## 🎓 Advanced Usage

### Priority Management

The AI automatically assigns priorities when extracting todos:
- **[URGENT]** - Immediate deadlines, blocking issues
- **[HIGH]** - Important tasks, near-term deadlines
- **Normal** - Regular tasks (no label)

You can also specify when creating:
```
create a high priority todo to fix the critical bug
add an urgent task to deploy the hotfix
```

### Working with Notes

Every `/capture` saves both:
- The original note (searchable)
- Extracted todos (linked to the note)

Search notes later:
```
what did we discuss about authentication?
show me notes from last week
```

### Complex Queries

The agent can handle complex requests:
```
show me all high priority todos that aren't completed yet
what todos are related to the API project and still open?
give me a summary of what I accomplished today
```

## 🎉 Example Session

```bash
$ terminal-todos

# Create some todos naturally
> create todos for: review PR 123, update docs, send team update