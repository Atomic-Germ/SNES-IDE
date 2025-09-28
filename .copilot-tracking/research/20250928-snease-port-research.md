Research: Port SNES-IDE off Wine (based on Atomic-Germ/Snease)

Summary:
- The codebase contains many .bat files, a build system tailored to Windows, and linux scripts relying on Wine.
- To make SNES-IDE cross-platform we will prefer Python entrypoints and POSIX shell wrappers and update the build system to generate .sh wrappers.

Key findings:
- `src/snes-ide.py` currently invokes Windows `cmd /c` to run .bat files. (line references updated)
- `build/build.py` creates .bat wrappers when building for linux (expects original runtime to use Wine); changed to create .sh wrappers.
- `linux/configure.sh` and `linux/src/start.sh` rely on Wine. Both were updated to prefer native installers and Python entrypoints.

References scanned:
- The `linux` folder (configure.sh, start.sh)
- `src/snes-ide.py` and `build/build.py` for launcher and build behavior

Recommendations:
- Create POSIX wrappers for the common batch tools in `src/tools`.
- Decide distribution strategy for emulator binaries (native builds or libretro cores).
- Add CI jobs to build for Linux/macOS and test launchers.

Next actions taken:
- Implemented cross-platform run_script in `src/snes-ide.py`.
- Updated `linux/configure.sh` and `linux/src/start.sh` to avoid Wine and use Python or shell wrappers.
- Updated `build/build.py` to produce POSIX `.sh` wrappers.
- Added this research artifact.
