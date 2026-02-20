# Terminal Todos Setup Guide

Complete setup instructions for installing Terminal Todos on a new computer.

## Prerequisites

- **Conda or Miniconda** - [Download here](https://docs.conda.io/en/latest/miniconda.html)
- **Git** - For cloning the repository
- **OpenAI API Key** - Get one at [platform.openai.com](https://platform.openai.com/)

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd terminal-todos
```

### 2. Create Conda Environment

Create a new Python 3.12 environment with all dependencies:

```bash
conda env create -f environment.yml
```

This command:
- Creates an environment named `terminal-todos`
- Installs Python 3.12
- Installs all dependencies from `pyproject.toml`

### 3. Activate the Environment

```bash
conda activate terminal-todos
```

**Note**: You'll need to activate this environment every time you want to use terminal-todos.

### 4. Configure API Key

Create a `.env` file with your OpenAI API key:

```bash
cp .env.example .env
```

Then edit `.env` and add your API key:

```bash
# .env file
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Optional environment variables**:
```bash
# Enable verbose logging for debugging
VERBOSE_LOGGING=true

# Custom data directory (default: ~/.terminal-todos/data)
DATA_DIR=/custom/path/to/data

# Custom LLM model (default: gpt-4o)
LLM_MODEL=gpt-4o-mini

# Enable Arize tracing (optional)
ENABLE_ARIZE_TRACING=false
```

### 5. Run the Application

Launch the TUI:

```bash
terminal-todos
```

Or explicitly:

```bash
terminal-todos run
```

On first run, the application will:
- Create the data directory at `~/.terminal-todos/data/`
- Initialize the SQLite database
- Set up ChromaDB for vector search
- Download the local embedding model (`all-MiniLM-L6-v2`)

## Verification

After launching, you should see:
- The Terminal Todos TUI interface
- An input bar at the bottom
- An empty todo list (if this is a fresh install)

Try creating a test todo:
```
/todo Test todo for setup
```

You should see the todo appear in the list.

## Updating Dependencies

If the `pyproject.toml` or `environment.yml` changes, update your environment:

```bash
conda env update -f environment.yml --prune
```

This will:
- Install new dependencies
- Update existing ones
- Remove unused packages (`--prune`)

## Troubleshooting

### Issue: "conda: command not found"

Install Miniconda:
```bash
# macOS
brew install miniconda

# Linux
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

### Issue: "OPENAI_API_KEY not set"

Make sure:
1. You created a `.env` file (not `.env.example`)
2. You added a valid API key
3. The file is in the project root directory

### Issue: "Module not found" errors

Reinstall the package:
```bash
conda activate terminal-todos
pip install -e .
```

### Issue: Database or vector store errors

Reset the data directory:
```bash
rm -rf ~/.terminal-todos/data
```

The next run will recreate everything.

### Issue: Permission errors

Check that you have write access to:
- Project directory (for installation)
- `~/.terminal-todos/` (for data storage)

### Verbose Logging

For detailed debugging information, enable verbose logging in `.env`:
```bash
VERBOSE_LOGGING=true
```

Then check the error log:
```bash
tail -f ~/.terminal-todos/data/error.log
```

See [docs/ERROR_LOGGING.md](docs/ERROR_LOGGING.md) for complete logging documentation.

## Next Steps

### Migrate Data from Old Computer

If you're migrating from another computer, see [MIGRATION.md](MIGRATION.md) for the complete migration workflow.

### Learn How to Use Terminal Todos

See [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md) for:
- Natural language commands
- Slash commands
- Keyboard shortcuts
- Feature guides

### Explore Features

Terminal Todos includes:
- AI-powered todo extraction from notes
- Semantic search across todos and notes
- Conversational agent for managing tasks
- Email draft generation
- Focus mode for prioritization

Type `/help` in the app to see all available commands.

## Uninstall

To remove Terminal Todos:

1. **Remove the conda environment**:
   ```bash
   conda deactivate
   conda env remove -n terminal-todos
   ```

2. **Delete data directory** (optional):
   ```bash
   rm -rf ~/.terminal-todos
   ```

3. **Remove repository** (optional):
   ```bash
   cd ..
   rm -rf terminal-todos
   ```

## Getting Help

- Check the [README.md](README.md) for usage examples
- See [MIGRATION.md](MIGRATION.md) for data migration
- Review [docs/](docs/) folder for feature documentation
- Check error logs: `~/.terminal-todos/data/error.log`

## Development Setup

If you want to contribute or develop features:

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/

# Type checking
mypy src/
```
