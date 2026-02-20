# Terminal Todos Documentation

Complete documentation for Terminal Todos features and setup.

## Getting Started

- **[MINICONDA_SETUP.md](MINICONDA_SETUP.md)** - Complete guide to installing and configuring Miniconda
  - Installation on macOS, Linux, Windows
  - Post-installation setup
  - Troubleshooting conda issues
  - Best practices

## Feature Documentation

### Core Features

- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Complete usage guide
  - Natural language mode
  - Slash commands
  - Todo management
  - Note management
  - Search and filtering

- **[ERROR_LOGGING.md](ERROR_LOGGING.md)** - Error logging and debugging
  - How to enable verbose logging
  - Where to find error logs
  - Debugging tips

### Advanced Features

- **[CONVERSATION_CONTEXT_FEATURE.md](CONVERSATION_CONTEXT_FEATURE.md)** - Context management
  - How conversation context works
  - Context limits and purging

- **[CONTEXT_PURGING.md](CONTEXT_PURGING.md)** - Context purging details
  - Automatic context cleanup
  - Manual context management

- **[INPUT_HISTORY_FEATURE.md](INPUT_HISTORY_FEATURE.md)** - Input history
  - Keyboard shortcuts for history
  - History persistence

### Optional Features

- **[ARIZE_TRACING.md](ARIZE_TRACING.md)** - Arize integration (optional)
  - Set up observability with Arize
  - Monitor agent behavior
  - Debug LLM interactions

## Development Documentation

- **[FEATURE_ROADMAP.md](FEATURE_ROADMAP.md)** - Planned features and roadmap
- **[NEW_FEATURES.md](NEW_FEATURES.md)** - Recently added features
- **[FIXES_SUMMARY.md](FIXES_SUMMARY.md)** - Bug fixes and improvements
- **[ALL_FIXES_SUMMARY.md](ALL_FIXES_SUMMARY.md)** - Complete fix history
- **[CLEANUP_DONE.md](CLEANUP_DONE.md)** - Code cleanup history

## Quick Links

### Setup
- [Main README](../README.md)
- [Setup Guide](../SETUP.md)
- [Migration Guide](../MIGRATION.md)
- [Quick Start](../QUICKSTART.md)

### Installation
1. Install Miniconda: [MINICONDA_SETUP.md](MINICONDA_SETUP.md)
2. Clone repository
3. Run `./install.sh`
4. Configure `.env` with API key
5. Launch with `todos`

### Support
- Check [ERROR_LOGGING.md](ERROR_LOGGING.md) for debugging
- Review [USAGE_GUIDE.md](USAGE_GUIDE.md) for how-to guides
- See [MINICONDA_SETUP.md](MINICONDA_SETUP.md) for conda issues

## Documentation Index

| Document | Description |
|----------|-------------|
| **Setup & Installation** | |
| [MINICONDA_SETUP.md](MINICONDA_SETUP.md) | Complete Miniconda installation and configuration |
| **User Guides** | |
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | How to use Terminal Todos |
| [ERROR_LOGGING.md](ERROR_LOGGING.md) | Debugging and error logs |
| **Features** | |
| [CONVERSATION_CONTEXT_FEATURE.md](CONVERSATION_CONTEXT_FEATURE.md) | Context management |
| [CONTEXT_PURGING.md](CONTEXT_PURGING.md) | Context cleanup details |
| [INPUT_HISTORY_FEATURE.md](INPUT_HISTORY_FEATURE.md) | Input history feature |
| **Optional** | |
| [ARIZE_TRACING.md](ARIZE_TRACING.md) | Observability with Arize |
| **Development** | |
| [FEATURE_ROADMAP.md](FEATURE_ROADMAP.md) | Future features |
| [NEW_FEATURES.md](NEW_FEATURES.md) | Recent additions |
| [FIXES_SUMMARY.md](FIXES_SUMMARY.md) | Bug fixes |
| [ALL_FIXES_SUMMARY.md](ALL_FIXES_SUMMARY.md) | Complete fix history |
| [CLEANUP_DONE.md](CLEANUP_DONE.md) | Code cleanup log |
