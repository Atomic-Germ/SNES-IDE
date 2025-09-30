#!/bin/sh
# Try to build bsnes-plus on macOS (best-effort, experimental).
# This script is intended for developer experimentation. It will clone the
# devinacker/bsnes-plus repo and attempt a default CMake configuration and build.

set -euo pipefail

WORKDIR="${1:-bsnes-plus-build}"
REPO="https://github.com/devinacker/bsnes-plus.git"

echo "Workspace: $WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

if [ ! -d bsnes-plus ]; then
  echo "Cloning bsnes-plus..."
  git clone "$REPO" bsnes-plus
else
  echo "bsnes-plus already present; updating..."
  cd bsnes-plus
  git fetch --all --prune
  git checkout master || true
  git pull --ff-only || true
  cd ..
fi

cd bsnes-plus

# Create build directory
mkdir -p build
cd build

# Attempt a simple CMake configure and build. This may require installing
# dependencies (SDL2, libsndfile, libogg, libvorbis, libflac) via Homebrew on macOS.
# This is intentionally conservative and will not attempt invasive patches.

echo "Running CMake configure..."
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES="arm64;x86_64" || cmake .. -DCMAKE_BUILD_TYPE=Release

echo "Building..."
cmake --build . -- -j$(sysctl -n hw.logicalcpu)

echo "Build finished. Check build/ for binaries and logs."

# End of script
