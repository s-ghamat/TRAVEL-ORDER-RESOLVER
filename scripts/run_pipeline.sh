#!/bin/bash
# End-to-end Travel Order Resolver pipeline
# NLP -> Pathfinder
# Uses the project virtual environment explicitly

set -e

# Absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Python from venv
PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Safety check
if [ ! -x "$PYTHON" ]; then
  echo "ERROR: .venv/bin/python not found. Did you create the virtualenv?"
  exit 1
fi

export PYTHONPATH="$PROJECT_ROOT/src"

# 1) NLP: sentenceID,sentence -> sentenceID,Departure,Destination | INVALID
# 2) Filter INVALID
# 3) Pathfinder: sentenceID,Departure,Destination -> route

"$PYTHON" -m tor.cli \
| grep -v ",INVALID" \
| "$PYTHON" -m tor.pathfinder_cli
