#!/bin/sh
# Skeleton script to fetch bsnes-plus and prepare an experimental patch
# This script is intentionally non-destructive and intended to be run locally
# by a developer with macOS toolchain installed.

set -euo pipefail

WORKDIR="${1:-bsnes-plus-work}"
REPO="git@github.com:devinacker/bsnes-plus.git"
OPTIROC="https://github.com/Optiroc/bsnes-plus.git"

echo "Preparing workspace in: $WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

if [ ! -d bsnes-plus ]; then
  echo "Cloning bsnes-plus upstream (devinacker)..."
  git clone "$REPO" bsnes-plus
else
  echo "bsnes-plus clone already present"
fi

cd bsnes-plus

echo "Adding Optiroc as remote for potential patch references..."
if ! git remote | grep -q optiroc; then
  git remote add optiroc "$OPTIROC"
fi

echo "Fetch remotes (this may require network access and proper SSH keys)..."
git fetch --all --prune

# Placeholder: developers should examine differences and craft a patchset.
# Example commands to create a patch branch:
# git checkout -b mac/experimental
# # apply changes here, then
# git add . && git commit -m "mac: experimental build changes"
# git format-patch origin/master --stdout > ../bsnes-plus-mac-experimental.patch

cat <<EOF
Workspace ready. To prepare a patch:
  1. Create a branch: git checkout -b mac/experimental
  2. Modify build files (CMake/Makefiles) and source to support macOS toolchain.
  3. Commit locally then create a patch file:
     git format-patch origin/master --stdout > ../bsnes-plus-mac-experimental.patch

This script does NOT attempt to patch automatically. It simply prepares the repository and remotes.
EOF