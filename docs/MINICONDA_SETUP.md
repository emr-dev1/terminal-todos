# Miniconda Setup Guide

Complete guide for installing and configuring Miniconda for Terminal Todos.

## What is Miniconda?

Miniconda is a minimal installer for conda - a package and environment management system. It allows you to:
- Create isolated Python environments with specific versions
- Manage dependencies without affecting your system Python
- Easily switch between different project environments

Terminal Todos uses Miniconda to ensure consistent Python 3.12 environment across all computers.

## Installation

### macOS

#### Option 1: Homebrew (Recommended)

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Miniconda
brew install miniconda

# Initialize conda for your shell
conda init zsh  # or 'bash' if you use bash
```

#### Option 2: Official Installer

```bash
# Download the installer
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh

# For Intel Macs, use:
# curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh

# Run the installer
bash Miniconda3-latest-MacOSX-arm64.sh

# Follow the prompts:
# - Press Enter to review license
# - Type 'yes' to accept
# - Press Enter to confirm installation location
# - Type 'yes' when asked to initialize conda
```

### Linux

```bash
# Download the installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Run the installer
bash Miniconda3-latest-Linux-x86_64.sh

# Follow the prompts (same as macOS)

# Initialize conda
conda init bash  # or 'zsh' if you use zsh
```

### Windows

1. Download the installer: https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
2. Run the installer
3. Follow the installation wizard
4. Check "Add Miniconda to PATH" (optional but convenient)
5. Open "Anaconda Prompt" from Start menu

## Post-Installation Setup

### 1. Reload Your Shell

After installation, reload your shell configuration:

```bash
# macOS/Linux with zsh
source ~/.zshrc

# macOS/Linux with bash
source ~/.bashrc

# Or simply close and reopen your terminal
```

### 2. Verify Installation

```bash
# Check conda is installed
conda --version
# Should show: conda 23.x.x or similar

# Check Python version
conda info
```

### 3. Configure Conda (Optional but Recommended)

```bash
# Disable auto-activation of base environment (prevents conda base from activating on every terminal)
conda config --set auto_activate_base false

# Set channel priority (improves package resolution)
conda config --add channels conda-forge
conda config --set channel_priority strict
```

## Using Conda with Terminal Todos

### Initial Setup

Once Miniconda is installed, Terminal Todos setup is easy:

```bash
# Clone the repository
git clone https://github.com/emr-dev1/terminal-todos.git
cd terminal-todos

# Run one-click install (creates environment automatically)
./install.sh
```

The install script will:
- Create a conda environment named `terminal-todos`
- Install Python 3.12
- Install all dependencies from `pyproject.toml`
- Configure shell aliases

### Manual Environment Creation

If you prefer to create the environment manually:

```bash
# Create environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate terminal-todos

# Install the package
pip install -e .
```

## Common Conda Commands

### Environment Management

```bash
# List all environments
conda env list

# Activate an environment
conda activate terminal-todos

# Deactivate current environment
conda deactivate

# Remove an environment
conda env remove -n terminal-todos

# Export environment to file
conda env export > environment.yml
```

### Package Management

```bash
# List installed packages
conda list

# Update conda itself
conda update conda

# Update all packages in current environment
conda update --all

# Install a specific package
conda install package-name

# Remove a package
conda remove package-name
```

### Environment Information

```bash
# Show conda configuration
conda config --show

# Show environment information
conda info

# Show environment details
conda env list
```

## Troubleshooting

### "conda: command not found"

**Problem**: Conda not in PATH after installation

**Solution**:
```bash
# Find conda installation
find ~ -name "conda" -type f 2>/dev/null | grep bin/conda | head -1

# Common locations:
# - Homebrew: /opt/homebrew/Caskroom/miniconda/base/bin/conda
# - Official: ~/miniconda3/bin/conda

# Manually initialize (replace path with your conda location)
/opt/homebrew/Caskroom/miniconda/base/bin/conda init zsh

# Reload shell
source ~/.zshrc
```

### "CondaHTTPError" or Network Issues

**Problem**: Cannot download packages

**Solution**:
```bash
# Try different channels
conda config --add channels defaults
conda config --add channels conda-forge

# Or use pip as fallback (after creating environment with conda)
conda create -n terminal-todos python=3.12
conda activate terminal-todos
pip install -e .
```

### Base Environment Auto-Activating

**Problem**: `(base)` appears in every terminal

**Solution**:
```bash
# Disable auto-activation
conda config --set auto_activate_base false
```

### Environment Conflicts

**Problem**: Packages won't install due to conflicts

**Solution**:
```bash
# Remove and recreate environment
conda deactivate
conda env remove -n terminal-todos
conda env create -f environment.yml
```

### Wrong Python Version

**Problem**: Environment has wrong Python version

**Solution**:
```bash
# Check current version
python --version

# If wrong, recreate with correct version
conda deactivate
conda env remove -n terminal-todos
conda create -n terminal-todos python=3.12
conda activate terminal-todos
pip install -e .
```

### Permission Errors on macOS

**Problem**: Permission denied errors during installation

**Solution**:
```bash
# Fix conda directory permissions
sudo chown -R $(whoami) /opt/homebrew/Caskroom/miniconda

# Or for official install
sudo chown -R $(whoami) ~/miniconda3
```

## Best Practices

### 1. One Environment Per Project

Create separate conda environments for different projects to avoid dependency conflicts:

```bash
# Project 1
conda create -n project1 python=3.12
conda activate project1
pip install -r requirements.txt

# Project 2
conda create -n project2 python=3.11
conda activate project2
pip install -r requirements.txt
```

### 2. Use environment.yml for Reproducibility

Always commit `environment.yml` to version control:

```bash
# Export current environment
conda env export > environment.yml

# Others can recreate exact environment
conda env create -f environment.yml
```

### 3. Keep Conda Updated

```bash
# Update conda regularly
conda update conda

# Update environments
conda activate terminal-todos
conda update --all
```

### 4. Clean Up Unused Environments

```bash
# List environments
conda env list

# Remove unused ones
conda env remove -n old-project

# Clean package cache
conda clean --all
```

## Miniconda vs Anaconda

### Miniconda (Recommended for Terminal Todos)
- ✅ Minimal installation (~400MB)
- ✅ Only includes conda and Python
- ✅ Faster to install
- ✅ You install only what you need

### Anaconda
- Includes 250+ pre-installed packages
- Larger installation (~3GB)
- Good for data science with GUI tools
- Overkill for Terminal Todos

**Recommendation**: Use Miniconda for Terminal Todos - it's lightweight and sufficient.

## Integration with Terminal Todos

### Auto-Activation

The `todos` alias automatically activates the conda environment:

```bash
# This alias does everything:
alias todos="/path/to/terminal-todos/todos-launcher.sh"

# When you run 'todos', it:
# 1. Navigates to project directory
# 2. Activates conda environment
# 3. Runs terminal-todos command
```

### Manual Activation

You can also activate manually:

```bash
conda activate terminal-todos
terminal-todos         # Run directly
terminal-todos export  # Export data
terminal-todos import backup.zip  # Import data
```

### Multiple Computers

Use the same workflow on all computers:

```bash
# Computer 1: Setup
brew install miniconda
git clone https://github.com/emr-dev1/terminal-todos.git
cd terminal-todos
./install.sh

# Computer 2: Same setup
brew install miniconda
git clone https://github.com/emr-dev1/terminal-todos.git
cd terminal-todos
./install.sh
```

Conda ensures Python 3.12 and dependencies are identical across all computers.

## Additional Resources

- **Official Conda Docs**: https://docs.conda.io/
- **Conda Cheat Sheet**: https://docs.conda.io/projects/conda/en/latest/user-guide/cheatsheet.html
- **Miniconda Download**: https://docs.conda.io/en/latest/miniconda.html
- **Troubleshooting Guide**: https://docs.conda.io/projects/conda/en/latest/user-guide/troubleshooting.html

## Quick Reference

```bash
# Installation (macOS)
brew install miniconda
conda init zsh

# Terminal Todos Setup
git clone https://github.com/emr-dev1/terminal-todos.git
cd terminal-todos
./install.sh

# Daily Usage
conda activate terminal-todos  # Activate environment
todos                           # Launch app (or use alias)
conda deactivate               # Deactivate when done

# Maintenance
conda update conda             # Update conda
conda env update -f environment.yml --prune  # Update environment
```

---

For Terminal Todos specific setup, see [SETUP.md](../SETUP.md)
