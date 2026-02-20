# Terminal Todos

A powerful terminal-based notes and todos application with AI-powered extraction, semantic search, and conversational agent features.

## Features

- 📝 **Rich Terminal UI** - Beautiful TUI built with Textual
- 🤖 **AI Todo Extraction** - Automatically extract todos from meeting notes using OpenAI
- 🔍 **Semantic Search** - Find todos and notes using natural language
- 💬 **Conversational Agent** - Chat with an AI agent to manage your todos
- 🗄️ **Local-First** - All data stored locally in SQLite + ChromaDB
- ⚡ **Fast** - Instant search with local embeddings (no API calls for search)

## Setup

### Quick Install (Recommended)

One-click installation after cloning from GitHub:

```bash
./install.sh
```

This will:
- Create conda environment (if needed)
- Install all dependencies
- Set up .env file
- Add `todos` alias to your shell

Then just:
```bash
source ~/.zshrc        # Reload shell config
nano .env              # Add your OpenAI API key
todos                  # Launch!
```

### Manual Installation

For more control, see [SETUP.md](SETUP.md) for detailed step-by-step instructions.

### Prerequisites

- Python 3.12 (conda/miniconda) - See [Miniconda Setup Guide](docs/MINICONDA_SETUP.md)
- OpenAI API key

### Running the App

```bash
terminal-todos
```

Or:

```bash
python -m terminal_todos
```

## Usage

### 🌟 Natural Language Mode (Primary Interface)

**Just type naturally** - no need for commands! The AI agent understands your intent:

```
what do I need to do today?
create a todo to review the design doc
mark the PR review as done
show me todos about meetings
what's my progress on the API work?
```

The agent will:
- ✅ Create, complete, and manage todos for you
- 🔍 Search through your todos intelligently
- 📊 Provide summaries and statistics
- 💬 Answer questions about your work

### 📝 Capture Notes & Extract Todos

Use `/capture` to paste meeting notes and automatically extract action items:

1. Type `/capture`
2. Paste your notes (can be multiple lines)
3. Type `END` on a new line
4. AI extracts todos with priorities

**Example:**
```
/capture
Meeting with design team:
- Send mockups to team by Friday
- Review accessibility requirements
- Schedule follow-up next week
END
```

**Result:** 3 todos created automatically with appropriate priorities!

### 🔍 Semantic Search

Find todos using natural language (not just keywords):

```bash
/search meeting        # Finds todos about meetings
/search urgent API     # Finds urgent API-related work
/search email          # Finds email-related tasks
```

### ⚡ Quick Commands

For direct operations, use slash commands:

| Command | Description | Example |
|---------|-------------|---------|
| `/capture` | Extract todos from notes | `/capture` → paste → `END` |
| `/search <query>` | Semantic search | `/search design review` |
| `/todo <text>` | Create a single todo | `/todo Review PR #123` |
| `/list [open\|done\|all]` | List todos | `/list open` |
| `/done <id>` | Mark todo complete | `/done 5` |
| `/stats` | Show statistics | `/stats` |
| `/clear` | Clear chat log | `/clear` |
| `/help` | Show help | `/help` |
| `/quit` | Exit app | `/quit` |

### ⌨️ Keyboard Shortcuts

- `Ctrl+R` - Refresh todo list
- `Ctrl+L` - Clear chat log
- `Ctrl+C` or `Ctrl+Q` - Quit
- `/` - Focus input (command mode)

#### Note Management
```bash
/note <text>      # Save a note
/note-search <query>  # Search notes
```

## Architecture

### Technology Stack

- **TUI**: [Textual](https://textual.textualize.io/) - Rich terminal UI framework
- **Database**: SQLite with SQLAlchemy ORM
- **Vector Store**: ChromaDB with local embeddings
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`)
- **Agent**: LangGraph with OpenAI (gpt-4o)
- **LLM**: OpenAI for extraction and agent

### Project Structure

```
terminal-todos/
├── src/terminal_todos/        # Main package
│   ├── db/                    # Database layer (SQLAlchemy)
│   ├── vector/                # Vector store (ChromaDB)
│   ├── core/                  # Business logic & sync
│   ├── extraction/            # AI extraction
│   ├── agent/                 # LangGraph agent
│   └── tui/                   # Textual UI
│       └── widgets/           # UI components
├── pyproject.toml             # Project configuration
└── .env                       # Environment variables
```

### Data Storage

All data is stored locally in:
- **Database**: `~/.terminal-todos/data/todos.db` (SQLite)
- **Vector Store**: `~/.terminal-todos/data/chroma/` (ChromaDB)

### How It Works

1. **Todos** are stored in SQLite (source of truth)
2. **Embeddings** are automatically synced to ChromaDB for semantic search
3. **Agent** uses LangGraph to decide when to call tools (CRUD operations)
4. **Extraction** uses OpenAI structured output to extract todos from notes

## Development

### Phase Status

- ✅ Phase 1: Project Bootstrap & Configuration
- ✅ Phase 2: Database Layer (SQLAlchemy)
- ✅ Phase 3: Vector Store & Embeddings
- ✅ Phase 4: Core Business Logic & Sync
- ✅ Phase 5: AI Todo Extraction
- ✅ Phase 6: LangGraph Agent
- ✅ Phase 7: Basic TUI with Textual
- ✅ Phase 8: Slash Commands (`/capture`, `/search`)
- ✅ Phase 9: Agent Integration in TUI (Natural Language Mode)
- 🚧 Phase 10: Safety & Polish (confirmation dialogs)
- ✅ Phase 11: Documentation

### Testing the Backend

You can test individual components without the TUI:

#### Database & Services

```python
from terminal_todos.core.todo_service import TodoService

service = TodoService()

# Create todo
todo = service.create_todo("Test task")

# List todos
todos = service.list_active()

# Search semantically
results = service.search_todos("test")
```

#### AI Extraction

```python
from terminal_todos.extraction.todo_extractor import TodoExtractor

extractor = TodoExtractor()
note = """
Meeting notes:
- Send recap email to team
- Schedule follow-up for next week
"""

extraction = extractor.extract(note)
print(f"Title: {extraction.title}")
for todo in extraction.todos:
    print(f"- {todo.content}")
```

#### Agent

```python
from terminal_todos.agent.graph import get_agent_graph
from langchain_core.messages import HumanMessage

graph = get_agent_graph()

result = graph.invoke({
    "messages": [HumanMessage(content="what todos do I have?")]
})

print(result["messages"][-1].content)
```

## Troubleshooting

### Error Logs & Debugging

**Error Log File:** `~/.terminal-todos/data/error.log`

All errors are automatically logged to this file with full stack traces, regardless of verbose setting.

**View recent errors:**
```bash
tail -50 ~/.terminal-todos/data/error.log
```

**Enable verbose logging for detailed execution tracking:**

1. **Add to your `.env` file:**
   ```
   VERBOSE_LOGGING=true
   ```

2. **Run the application:**
   ```bash
   terminal-todos
   ```

3. **All operations will be logged** to both the error log file and stderr

**What gets logged:**
- All exceptions with full stack traces
- Input processing flow
- Agent execution details
- Database operations
- Vector store sync
- Import/export operations

See [docs/ERROR_LOGGING.md](docs/ERROR_LOGGING.md) for complete logging documentation.

### Issue: "OPENAI_API_KEY not set"

Make sure you've created a `.env` file with your API key:
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### Issue: "Module not found"

Make sure you've installed the package:
```bash
pip install -e .
```

### Issue: "Database errors"

Reset the database:
```python
from terminal_todos.db.migrations import reset_database
reset_database()
```

### Issue: "Vector store issues"

Delete the ChromaDB directory:
```bash
rm -rf ~/.terminal-todos/data/chroma
```

The next run will recreate it.

## Export/Import

Export your data for backup or migration:

```bash
terminal-todos export --output backup.zip
```

Import on a new computer:

```bash
terminal-todos import backup.zip
```

See [MIGRATION.md](MIGRATION.md) for complete migration guide.

## Contributing

This is a demonstration project following the PRD specifications. Future enhancements could include:

- [ ] Complete Phase 8: All slash commands (`/capture`, `/search`, `/del`, etc.)
- [ ] Complete Phase 9: Full agent integration in TUI
- [ ] Complete Phase 10: Confirmation dialogs and error handling
- [ ] Due dates and priorities
- [ ] Tags and categories
- [ ] Recurring todos
- [x] Export/import (completed!)
- [ ] Sync across devices

## License

MIT License - see LICENSE file for details

## Credits

Built with:
- [Textual](https://textual.textualize.io/) by Textualize
- [LangChain](https://www.langchain.com/) & [LangGraph](https://langchain-ai.github.io/langgraph/)
- [ChromaDB](https://www.trychroma.com/)
- [sentence-transformers](https://www.sbert.net/)
- [OpenAI](https://openai.com/)
