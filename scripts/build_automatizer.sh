#!/usr/bin/env bash
# scripts/build_automatizer.sh
# Local helper to build the automatizer using PyInstaller (platform-specific).
set -euo pipefail

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller not found; installing into virtualenv or user site-packages"
  python3 -m pip install --user pyinstaller
fi

SRC=src/libs/pvsneslib/devkitsnes/automatizer.py
OUT_DIR=dist

pyinstaller --onefile --name automatizer "$SRC"

echo "Build complete; output in $OUT_DIR/"
