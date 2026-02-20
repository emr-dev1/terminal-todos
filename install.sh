#!/bin/bash
# One-click installation script for Terminal Todos
# Run this after cloning from GitHub: ./install.sh

set -e  # Exit on error

echo "============================================================"
echo "Terminal Todos - One-Click Installation"
echo "============================================================"
echo ""

# Get the project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Initialize conda
echo "Initializing conda..."
if [ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]; then
    source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
else
    echo "❌ Error: Conda not found at /opt/homebrew/Caskroom/miniconda/"
    echo "Please install Miniconda first: brew install miniconda"
    exit 1
fi

# Check if environment exists
if conda env list | grep -q "^terminal-todos "; then
    echo "✓ Conda environment 'terminal-todos' already exists"
else
    echo "Creating conda environment 'terminal-todos'..."
    conda env create -f environment.yml
    echo "✓ Conda environment created"
fi

# Activate the environment
echo "Activating environment..."
conda activate terminal-todos

# Install the package
echo ""
echo "Installing Terminal Todos package..."
pip install -e .

# Setup .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your OPENAI_API_KEY"
    echo "   File location: $SCRIPT_DIR/.env"
else
    echo "✓ .env file already exists"
fi

# Add alias to .zshrc if not already present
echo ""
ZSHRC="$HOME/.zshrc"
ALIAS_LINE="alias todos=\"$SCRIPT_DIR/todos-launcher.sh\""

if [ -f "$ZSHRC" ]; then
    if grep -q "alias todos=" "$ZSHRC"; then
        echo "✓ 'todos' alias already exists in .zshrc"
    else
        echo "Adding 'todos' alias to .zshrc..."
        echo "" >> "$ZSHRC"
        echo "# Terminal Todos (added by install script)" >> "$ZSHRC"
        echo "$ALIAS_LINE" >> "$ZSHRC"
        echo "✓ Alias added to .zshrc"
        echo "   Run: source ~/.zshrc  (or restart terminal)"
    fi
else
    echo "⚠️  Warning: .zshrc not found at $ZSHRC"
    echo "   Add this alias manually:"
    echo "   $ALIAS_LINE"
fi

# Make launcher executable
chmod +x todos-launcher.sh
chmod +x scripts/todos-launcher.sh

echo ""
echo "============================================================"
echo "✅ Installation Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env and add your OpenAI API key:"
echo "   nano $SCRIPT_DIR/.env"
echo ""
echo "2. Reload your shell configuration:"
echo "   source ~/.zshrc"
echo ""
echo "3. Launch Terminal Todos:"
echo "   todos"
echo ""
echo "Or activate the environment and run directly:"
echo "   conda activate terminal-todos"
echo "   terminal-todos"
echo ""
echo "For migration from another computer, see MIGRATION.md"
echo "============================================================"
echo ""
