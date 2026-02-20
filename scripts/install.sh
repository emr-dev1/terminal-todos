#!/bin/bash
# Install terminal-todos package and all dependencies

# Navigate to project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_DIR"

# Activate conda environment (Homebrew miniconda location)
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
conda activate terminal-todos

echo "============================================================"
echo "Installing Terminal Todos Package"
echo "============================================================"

# Install the package in editable mode with all dependencies
pip install -e .

echo ""
echo "============================================================"
echo "✅ Installation Complete!"
echo "============================================================"
echo ""
echo "The terminal-todos package and all dependencies are now installed."
echo ""
echo "To start:"
echo "  Terminal mode: todos"
echo "  Web mode:      todos --web"
echo ""
