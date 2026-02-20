# Terminal Todos - Quick Start

## Fresh Install (New Computer)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd terminal-todos

# 2. Run one-click install
./install.sh

# 3. Add your API key
nano .env
# Add: OPENAI_API_KEY=sk-your-key-here

# 4. Reload shell and launch
source ~/.zshrc
todos
```

## Migrating from Another Computer

### On Old Computer
```bash
todos export --output ~/Downloads/backup.zip
# Upload to cloud storage
```

### On New Computer
```bash
# After running install.sh above:
todos import ~/Downloads/backup.zip
todos  # Launch with all your data!
```

## Daily Usage

```bash
# Launch the app
todos

# Or use full commands
todos export                    # Backup your data
todos import backup.zip         # Restore from backup
todos run                       # Launch TUI explicitly
```

## No Conda Activation Needed!

The `todos` alias handles everything automatically:
- Activates the conda environment
- Runs the command
- Works from any directory

## Troubleshooting

**Command not found**: Run `source ~/.zshrc` to reload your shell

**API key error**: Edit `.env` file and add your OpenAI API key

**Need help**: See [SETUP.md](SETUP.md) or [MIGRATION.md](MIGRATION.md)

## Files Overview

- `install.sh` - One-click installation script
- `SETUP.md` - Detailed setup guide
- `MIGRATION.md` - Complete migration workflow
- `README.md` - Full documentation
- `.env` - Configuration (add your API key here)
