#!/bin/bash
# Start Terminal Todos

# Navigate to project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_DIR"

# Activate conda environment (Homebrew miniconda location)
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
conda activate terminal-todos

# Run terminal-todos
terminal-todos "$@"
