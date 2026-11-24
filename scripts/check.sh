#!/usr/bin/env bash
# Validate marketplace manifests and run every plugin's tests.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
fail=0
step() { printf '\n== %s\n' "$1"; }

step "JSON"
while IFS= read -r f; do
  python3 -m json.tool "$f" >/dev/null || { echo "invalid JSON: $f"; fail=1; }
done < <(git ls-files --cached --others --exclude-standard '*.json')

step "marketplace"
python3 -I - <<'PY' || fail=1
import json, os, sys
m = json.load(open(".claude-plugin/marketplace.json"))
bad = 0
for p in m["plugins"]:
    if not os.path.isdir(p["source"]):
        print("missing source:", p["source"]); bad = 1
    if "version" not in p:
        print("missing version:", p["name"]); bad = 1
listed = {os.path.normpath(p["source"]) for p in m["plugins"]}
for d in sorted(os.listdir("plugins")):
    if os.path.normpath("./plugins/" + d) not in listed and os.path.isdir("plugins/" + d):
        print("unlisted plugin dir:", d); bad = 1
sys.exit(bad)
PY
if command -v claude >/dev/null 2>&1; then
  claude plugin validate . || fail=1
fi

step "tests"
while IFS= read -r t; do
  echo "-- $t"
  python3 -m unittest discover -s "$t" || fail=1
done < <(find plugins -type d -name tests -not -path '*/cases/*' | sort)

if command -v typst >/dev/null 2>&1; then
  step "arm-style-manual template regression"
  python3 plugins/arm-style-trm-typst/skills/arm-style-manual/assets/scripts/manual.py test | tail -2 || fail=1
fi

exit "$fail"
