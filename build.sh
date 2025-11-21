#!/bin/bash
# SNES-IDE Build System for Unix-like Systems (macOS, Linux)
# This script provides a convenient interface to the Python build system
# Usage: ./build.sh [command]

set -e

if [ $# -eq 0 ]; then
    python build_system.py build
else
    python build_system.py "$@"
fi
