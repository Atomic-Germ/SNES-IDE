Automatizer — packaging and release

This project includes a Python implementation of the "automatizer" at src/libs/pvsneslib/devkitsnes/automatizer.py. To provide release parity with the Windows-native `automatizer.exe`, we use PyInstaller to generate one-file native executables per-platform. Packaging tkinter apps requires bundling Tcl/Tk runtime data alongside the binary; this repository includes a helper to automate that.

Local build

- Install PyInstaller (preferably in a virtualenv):
  python3 -m pip install pyinstaller

- Build a local single-file binary using the helper script which attempts to discover Tcl/Tk libraries and include them:
  scripts/build_automatizer.sh

CI builds

A GitHub Actions workflow `Build Automatizer` builds platform artifacts on demand (tag or manual dispatch) for Windows, macOS and Linux. The workflow now calls a helper script that probes the environment and passes appropriate `--add-data` and `--hidden-import` flags to PyInstaller so tkinter works correctly in the bundled binary. The workflow outputs the following artifacts for download:

- automatizer-windows (dist/automatizer.exe)
- automatizer-macos (dist/automatizer)
- automatizer-linux (dist/automatizer)

Notes & caveats

- PyInstaller must be run on its target platform to produce a native executable. The workflow uses platform-specific runners to satisfy this requirement.
- The helper attempts to locate Tcl/Tk libraries via environment variables (`TCL_LIBRARY`, `TK_LIBRARY`), by probing `tkinter` (using `tkinter.Tcl()` to avoid creating a window), and by checking common Homebrew or Python install paths. If the helper cannot detect Tcl/Tk, it will warn, and the resulting binary may fail at runtime when importing/using tkinter.
- On macOS with Homebrew-installed tcl-tk, ensure your Python interpreter and Homebrew Tcl/Tk are compatible (sometimes `python` needs to be linked against the Homebrew tcl-tk). If packaging fails because tkinter cannot be imported during the probe, set `TCL_LIBRARY` and `TK_LIBRARY` environment variables in the workflow job to assist the helper.
- If the automatizer uses other resources (images, fonts), you may need to add them to the helper's `--add-data` list.

Running the packaged automatizer

- On Windows: download `automatizer.exe` and place it under `libs/pvsneslib/devkitsnes/` or `libs/pvsneslib/devkitsnes/bin/` so the existing Windows wrappers will detect it automatically.
- On macOS/Linux: download the `automatizer` binary and place it under `libs/pvsneslib/devkitsnes/bin/` (ensure it is executable) to be discoverable by the POSIX wrapper added in src.

Troubleshooting

- If the packaged binary fails with Tcl/Tk runtime errors, re-run the Build Automatizer workflow with `TCL_LIBRARY` and `TK_LIBRARY` environment variables set to the correct directories for that runner, or adjust the helper to include additional paths.
- To debug PyInstaller packaging locally, run the helper with `--debug` to get verbose warnings.

If desired, the project can be extended to automatically publish built binaries to GitHub Releases as part of a release workflow.
