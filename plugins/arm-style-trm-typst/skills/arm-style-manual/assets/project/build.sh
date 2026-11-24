#!/usr/bin/env bash
# Run from any working directory. Optional arguments: project-relative entrypoint and output.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTRY="${1:-main.typ}"
OUTPUT="${2:-}"
if [[ -z "${OUTPUT}" ]]; then
    if [[ "$(basename "$(dirname "${PROJECT_DIR}")")" == doc ]]; then
        NAME="$(basename "${PROJECT_DIR}")"
        OUTPUT="../${NAME%_manual}_manual.pdf"
    else
        OUTPUT="build/manual.pdf"
    fi
fi
cd "${PROJECT_DIR}"
mkdir -p "$(dirname "${OUTPUT}")"
typst compile --root "${PROJECT_DIR}" --font-path "${PROJECT_DIR}/fonts/Pretendard" "${ENTRY}" "${OUTPUT}"
