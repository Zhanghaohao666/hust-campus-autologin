#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_DIR"

if [ ! -f "pyproject.toml" ]; then
  echo "Run this script from a cloned project directory or set PROJECT_DIR to an existing checkout." >&2
  exit 1
fi

"$PYTHON_BIN" -m pip install --user -e ".[linux]"
"$PYTHON_BIN" -m campus_autologin doctor

echo
echo "Next:"
echo "  python3 -m campus_autologin init --username <student-id>"
echo "  python3 -m campus_autologin set-credential --username <student-id>"
echo "  python3 -m campus_autologin login"
echo "  python3 -m campus_autologin install-service"
