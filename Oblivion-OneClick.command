#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "python3 is required. Install Command Line Tools first: xcode-select --install" buttons {"OK"} default button "OK" with icon caution'
  exit 1
fi

python3 "$SCRIPT_DIR/app.py"
