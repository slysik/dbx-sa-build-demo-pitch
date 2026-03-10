#!/usr/bin/env bash
# open-live.sh — Open live-arch.md in a browser with auto-refresh
# Usage: bash scripts/open-live.sh [path/to/arch.md]

ARCH_FILE="${1:-./live-arch.md}"

# Create the file if it doesn't exist
if [ ! -f "$ARCH_FILE" ]; then
  cat > "$ARCH_FILE" << 'EOF'
# Live Architecture — Awaiting Discovery
*Start the interview agent and tell it what you're learning.*

## Discovery Status
| Category | Status | Key Facts |
|----------|--------|-----------|
| Business Problem | ❓ | Not yet captured |
| Current Stack | ❓ | Not yet captured |
| Cloud & Region | ❓ | Not yet captured |
| Data Volume | ❓ | Not yet captured |
| Latency Needs | ❓ | Not yet captured |
| Compliance | ❓ | Not yet captured |

## Architecture
*Diagram will appear here as discovery progresses.*
EOF
  echo "✓ Created $ARCH_FILE"
fi

echo "📄 Opening $ARCH_FILE"
echo ""
echo "Tip: If you have 'grip' (GitHub Markdown preview) installed:"
echo "  pip install grip"
echo "  grip '$ARCH_FILE' --browser"
echo ""
echo "Or use VS Code with Markdown Preview:"
echo "  code '$ARCH_FILE'"
echo "  Then press: Cmd+Shift+V (Mac) or Ctrl+Shift+V (Windows/Linux)"
echo ""
echo "Or install 'glow' for terminal rendering:"
echo "  brew install glow"
echo "  glow -p '$ARCH_FILE'"
echo ""

# Try each renderer in order
if command -v grip &>/dev/null; then
  echo "🌐 Launching grip (auto-refresh browser preview)..."
  grip "$ARCH_FILE" --browser
elif command -v glow &>/dev/null; then
  echo "✨ Launching glow (terminal preview)..."
  glow -p "$ARCH_FILE"
elif command -v code &>/dev/null; then
  echo "💻 Opening in VS Code..."
  code "$ARCH_FILE"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  echo "🍎 Opening with macOS default..."
  open "$ARCH_FILE"
else
  echo "📝 No preview tool found. Open $ARCH_FILE manually."
  echo "   Recommended: pip install grip && grip '$ARCH_FILE' --browser"
fi
