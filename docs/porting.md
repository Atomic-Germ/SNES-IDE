# Porting SNES-IDE off WINE

This document describes the changes required to make SNES-IDE run natively on macOS and Linux without relying on Wine.

Goals
- Remove runtime dependence on Wine and Windows-only batch files
- Provide native POSIX shell wrappers and Python entry points
- Keep Windows compatibility where possible

Key changes made
- `src/snes-ide.py`: Reworked to dispatch to platform-appropriate launchers. Uses `run_script()` to find `.sh` or `.py` on POSIX, and `.bat`/`.exe`/`.py` on Windows.
- `linux/configure.sh`: Removed Wine installation flow. Copies distribution into `~/.local/share/snes-ide` and runs `INSTALL.sh` if present. Otherwise provides guidance to run Python entrypoint.
- `linux/src/start.sh`: Now starts the application using native `snes-ide.sh` wrapper or `python3 src/snes-ide.py`.
- `build/build.py`: Generates POSIX `.sh` wrappers for Python entry points when `build.py linux` is used, and packages emulator binaries and libretro cores found under `libs/bsnes` and `libs/libretro` into the distribution.

Next steps
- Implement actual `.sh` placeholders for tools currently distributed as `.bat` (see `src/tools`). I have created an initial `.sh` wrapper for `automatizer-batch` as an example.
- Replace or provide native binaries for tools such as `schismtracker.exe` and other Windows-only installers, or provide Python fallbacks where available.
- New interactive installers
  - `INSTALL_VARIANT.sh` (POSIX) and `INSTALL_VARIANT.bat` (Windows) let users choose an install directory, select an editor integration (VS Code or Vim on POSIX; VS Code, Vim, or Notepad++ on Windows), and optionally copy emulator binaries/cores from the repository into the installed location. They create desktop shortcuts appropriate for each platform.

Manual testing instructions
1. Run `python3 src/snes-ide.py` on Linux/macOS to ensure the menu launches.
2. Create `.sh` wrappers in `src/tools` corresponding to the `.bat` files and ensure they are executable.
3. Run `build/build.py linux` to create POSIX wrappers under `SNES-IDE-out` and install with `linux/configure.sh`.

If you want, I can:
- Create the initial `.sh` placeholders for all toolkit scripts and make them executable.
- Add CI scripts and packaging notes.

Additional Notes
- The `linux/configure.sh` and `INSTALL.sh` scripts now set executable bits on shell wrappers and native emulator binaries when installing the distribution.
