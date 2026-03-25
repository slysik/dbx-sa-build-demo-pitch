#!/usr/bin/env bash
# Wrapper — delegates to Python implementation
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/sync-skills.py" "$@"
