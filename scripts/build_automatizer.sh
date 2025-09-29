#!/usr/bin/env bash
# scripts/build_automatizer.sh
# Local helper to build the automatizer using PyInstaller (platform-specific).
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found; aborting"
  exit 1
fi

python3 scripts/pyinstaller_build_helper.py --src src/libs/pvsneslib/devkitsnes/automatizer.py --name automatizer --onefile

echo "Build helper finished; check dist/ for the output binary"
