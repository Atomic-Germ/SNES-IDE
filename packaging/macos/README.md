# macOS Packaging Guide — SNES-IDE

Purpose: document how to produce a working macOS distribution (unsigned DMG by default) and where to place mac-native binaries.

High-level strategy
- Keep a single repository for Windows, Linux, and macOS builds.
- Vendor or build mac-native binaries under `libs/<tool>/darwin/` and let the build script include them only for mac builds.
- Use small POSIX wrappers in `src/tools/*.sh` (already present) so the `snes-ide` launcher works on macOS.

Dependencies (recommend using Homebrew)
- Homebrew base: https://brew.sh/
- Required libs for audio and tracker tools:
  - SDL2: brew install sdl2
  - libogg: brew install libogg
  - libflac: recommended distribution: use the libflac-framework release (see below) or install `flac` via brew for CLI.

Recommended installs

  brew install sdl2 libogg mednafen

Notes on libflac
- If you need a framework-style `libFLAC` packaged for mac apps, consider using the `libflac-framework` release:
  - https://github.com/nbonamy/libflac-framework/releases/tag/1.4.2-2
  - Download and place the .framework bundle under `libs/<tool>/darwin/` or copy the `.dylib` into the app bundle's Frameworks folder during packaging.

Emulator strategy (bsnes replacement)
- Primary: mednafen (recommended replacement)
  - Install: brew install mednafen
  - The IDE emulator wrapper will call `mednafen <ROM>` if present.
- Experimental: bsnes-plus patching (if you want native bsnes features)
  - Use the script: `scripts/prepare-bsnes-plus-patch.sh` to fetch `devinacker/bsnes-plus` and prepare a workspace for experimental macOS patches.
  - This is a long-term effort and will require upstream CMake/Makefile edits.
- Alternative: RetroArch bsnes-libretro core (advanced users).

SchismTracker
- macOS builds are available at the official release URL:
  - https://github.com/schismtracker/schismtracker/releases/tag/20250825
- Place the mac binary in `SNES-IDE-out/tools/soundsnes/tracker/` or `libs/schismtracker/` and the `schismtracker.sh` wrapper will prefer it.

Where to place mac-native binaries
- `libs/<tool>/darwin/` → for vendored mac native libs and binaries.
- Example:
  - `libs/bsnes/darwin/bsnes` (binary)
  - `libs/schismtracker/darwin/schismtracker` (binary)
  - `libs/m8te/darwin/m8te` (if/when available)

Packaging steps (unsigned DMG)
1. Build the project for mac: `python build/build.py mac`
2. Use PyInstaller or an equivalent to create an `.app` bundle. Example:
   python -m PyInstaller --noconfirm --windowed --name "SNES IDE" --add-data "libs:libs" src/snes-ide.py
3. Copy vendored darwin binaries into `dist/SNES IDE.app/Contents/Resources/libs/` or `Contents/Frameworks/` as appropriate.
4. Create a DMG:
   mkdir -p release/SNES-IDE
   cp -R dist/SNES\ IDE.app release/SNES-IDE/
   hdiutil create -volname "SNES IDE" -srcfolder release/SNES-IDE -ov -format UDZO SNES-IDE-<version>-mac.dmg

Notes & known limitations
- If you need an x86_64 build on Apple Silicon, you will have to build under Rosetta (install Rosetta2 and run `arch -x86_64` for the build commands), or run on an Intel mac runner.
- Producing a single universal `.app` for PyInstaller-built Python apps is complex; the recommended interim approach is to produce separate arm64 and x86_64 builds and publish them as separate artifacts.

Developer notes: bsnes-plus experimentation
- The experimental script `scripts/prepare-bsnes-plus-patch.sh` will clone the devinacker/bsnes-plus repo and add the Optiroc remote as reference. The developer should create a `mac/experimental` branch and begin porting the build system to macOS.

User-facing instructions
- If a required binary is missing, the wrapper script will print clear instructions and point to this README and `docs/PORTING_MAC.md`.
