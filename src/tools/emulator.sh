#!/bin/sh
# macOS emulator launcher for SNES-IDE
# Preference order:
# 1. bundled bsnes (if present and user chooses to vendor one)
# 2. mednafen (recommended replacement)
# 3. retroarch (libretro bsnes core)

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1) bundled bsnes (user may place bsnes binary in libs/bsnes/ or tools/bsnes)
if [ -x "$SELF_DIR/bsnes" ]; then
  exec "$SELF_DIR/bsnes" "$@"
fi
if [ -x "${SELF_DIR}/../libs/bsnes/bsnes" ]; then
  exec "${SELF_DIR}/../libs/bsnes/bsnes" "$@"
fi

# 2) mednafen (recommended via Homebrew)
if command -v mednafen >/dev/null 2>&1; then
  # mednafen takes rom as argument; the IDE should call this wrapper with the ROM path
  exec mednafen "$@"
fi

# 3) retroarch
if command -v retroarch >/dev/null 2>&1; then
  # If a specific core is present, attempt to use it. Otherwise ask user to configure.
  if [ -n "$1" ]; then
    exec retroarch -L "$(which retroarch)" "$@" || exec retroarch "$@"
  else
    exec retroarch
  fi
fi

cat <<EOF
No SNES emulator found for macOS.

Options:
- Install mednafen (recommended):
  brew install mednafen

- Use RetroArch with bsnes-libretro core; install via Homebrew or RetroArch UI.

- Optional (experimental): provide a bsnes-native binary at SNES-IDE-out/libs/bsnes/bsnes and re-run the build.

See packaging/macos/README.md and docs/PORTING_MAC.md for details.
EOF
exit 1
