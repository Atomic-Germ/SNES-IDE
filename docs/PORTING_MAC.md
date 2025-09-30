Porting Windows CI to macOS — Summary and Next Steps

This document summarizes the automated steps taken to port the Windows CI to macOS and lists manual follow-ups that remain.

What I changed

- Added a macOS build mode to `build/build.py`:
  - Detects `python build/build.py mac` and produces a `SNES-IDE-out` directory suitable for macOS packaging.
  - Generates simple shell script wrappers for Windows `.bat` files under `SNES-IDE-out/tools/*.sh` so macOS packaging contains placeholders.
  - For Python-based tools, creates executable shell wrappers (no extension) that call `python3` with the script; this mirrors the existing Linux behavior.
  - Skips copying Windows-only `.dll` files in macOS mode and instead looks for `.dylib` in `tools/` if present.

- Added a macOS installer script `INSTALL.sh` at project root. It is a simple placeholder installer that copies `SNES-IDE-out` to a local `sneside-macos-install` directory; customize as needed.

- Replaced `.github/workflows/MacOS.yml` with a macOS-specific CI workflow that:
  - Runs on `macos-2025`.
  - Builds using `python build/build.py mac`.
  - Creates `sneside-macos.zip` artifact and uploads it.
  - Validates expected `libs` folders and presence of `INSTALL.sh` and generated tool wrappers.

What remains manual / follow-ups

- Native Windows binaries (.exe) and DLLs will not work on macOS. These need macOS-equivalent binaries or native ports (e.g., building `automatizer` for macOS, or providing cross-platform replacements). The CI currently packages placeholders for these.

- The generated `.sh` wrappers are intentionally simple and often only print a message. They must be adapted to implement the original tool logic in a macOS-friendly way where necessary.

- `buildModules/buildPy` remains Windows-oriented (it invokes PyInstaller to create .exe). For macOS-native single-file builds, one may want to create a macOS-specific packaging step that creates a `.app` bundle or a macOS single-file binary using PyInstaller options. Currently the build process creates Python-based wrappers for mac.

- Update project documentation and README with macOS contribution/build instructions (e.g., Homebrew dependencies, Xcode command line tools).

- If you want CI to produce real macOS native executables, add a new build module that invokes PyInstaller with macOS targets or uses a proper macOS build pipeline.

How to test locally

1. On macOS with Python 3.13 installed, run:

   python build/build.py mac

2. Inspect `SNES-IDE-out` and run `INSTALL.sh` inside it.

3. Customize generated shell scripts in `SNES-IDE-out/tools` to provide the expected behavior for macOS users.

Contact

If you want me to continue and implement generation of real macOS native binaries (e.g., PyInstaller-based `.app` or `.dmg` bundles), tell me and I will add those changes and update CI to produce them.
