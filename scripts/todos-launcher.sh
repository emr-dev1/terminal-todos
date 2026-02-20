#!/bin/bash
# Terminal Todos launcher

# Navigate to project directory (resolve symlinks to get actual script location)
SCRIPT_DIR="$( cd "$( dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_DIR"

# Activate conda environment (Homebrew miniconda location)
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
conda activate terminal-todos

# Run terminal-todos
exec terminal-todos "$@"
