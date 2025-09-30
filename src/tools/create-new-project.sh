#!/bin/sh
# macOS wrapper for create-new-project
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOL="$SELF_DIR/create-new-project"

if [ -x "$TOOL" ]; then
  exec "$TOOL" "$@"
fi

echo "create-new-project: native binary not found. Falling back to Python script execution if present."
if [ -f "${SELF_DIR}/../src/tools/create-new-project.py" ]; then
  python3 "${SELF_DIR}/../src/tools/create-new-project.py" "$@"
  exit $?
fi

echo "create-new-project: no native binary or script available. See docs/PORTING_MAC.md for details."
exit 1