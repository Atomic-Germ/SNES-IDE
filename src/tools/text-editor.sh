#!/usr/bin/env bash

# POSIX wrapper to open a text editor. Attempts common editors, then falls back to $EDITOR or xdg-open/open.
set -e

FILE="$1"
shift || true

# Try Visual Studio Code
if command -v code &> /dev/null; then
    if [ -n "$FILE" ]; then
        exec code "$FILE"
    else
        exec code
    fi
fi

# Try gedit
if command -v gedit &> /dev/null; then
    if [ -n "$FILE" ]; then
        exec gedit "$FILE"
    else
        exec gedit
    fi
fi

# Try default editor from environment
if [ -n "$EDITOR" ]; then
    if [ -n "$FILE" ]; then
        exec "$EDITOR" "$FILE"
    else
        exec "$EDITOR"
    fi
fi

# macOS open
if command -v open &> /dev/null; then
    if [ -n "$FILE" ]; then
        open "$FILE"
        exit 0
    else
        open -a TextEdit
        exit 0
    fi
fi

# Fallback to xdg-open
if command -v xdg-open &> /dev/null; then
    if [ -n "$FILE" ]; then
        xdg-open "$FILE"
    else
        echo "No file provided and no GUI editor found. Set the EDITOR environment variable to your preferred terminal editor."
    fi
    exit 0
fi

echo "No suitable editor found. Please install VS Code, gedit, or set the EDITOR environment variable."
exit 1
