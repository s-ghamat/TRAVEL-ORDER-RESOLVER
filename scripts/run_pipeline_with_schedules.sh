#!/bin/bash
# End-to-end pipeline:
# sentenceID,sentence -> NLP -> triplet -> GTFS pathfinder with schedule proof
# Output includes:
#  - strict route line
#  - schedule line

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "ERROR: .venv/bin/python not found. Create your venv first."
  exit 1
fi

export PYTHONPATH="$PROJECT_ROOT/src"

"$PYTHON" -m tor.cli \
| grep -v ",INVALID" \
| "$PYTHON" -m tor.gtfs_pathfinder_cli
