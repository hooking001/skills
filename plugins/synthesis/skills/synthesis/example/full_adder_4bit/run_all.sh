#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Libraries are not stored in git; download and verify them on first use.
python3 "${PROJECT_DIR}/../../scripts/manage.py" download --pdk nangate45 "${PROJECT_DIR}/lib"
bash "${PROJECT_DIR}/script/run_tb.sh"
bash "${PROJECT_DIR}/script/run_synth.sh" "$@"
