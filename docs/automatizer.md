Automatizer — packaging and release

This project includes a Python implementation of the "automatizer" at src/libs/pvsneslib/devkitsnes/automatizer.py. To provide release parity with the Windows-native `automatizer.exe`, we use PyInstaller to generate one-file native executables per-platform.

Local build

- Install PyInstaller (preferably in a virtualenv):
  python3 -m pip install pyinstaller

- Build a local single-file binary:
  scripts/build_automatizer.sh

CI builds

A GitHub Actions workflow `Build Automatizer` builds platform artifacts on demand (tag or manual dispatch) for Windows, macOS and Linux. The workflow outputs the following artifacts for download:

- automatizer-windows (dist/automatizer.exe)
- automatizer-macos (dist/automatizer)
- automatizer-linux (dist/automatizer)

Notes & caveats

- PyInstaller must be run on its target platform to produce a native executable. The workflow uses platform-specific runners to satisfy this requirement.
- The generated binaries are self-contained but may still depend on system GUI frameworks (tkinter) if the automatizer uses them. Packaging for GUI apps may require additional PyInstaller flags (e.g. --windowed) or hidden imports.
- Do not commit large binary artifacts to the repository. Use GitHub Releases or artifacts produced by the workflow for distribution.

Running the packaged automatizer

- On Windows: download `automatizer.exe` and place it under `libs/pvsneslib/devkitsnes/` or `libs/pvsneslib/devkitsnes/bin/` so the existing Windows wrappers will detect it automatically.
- On macOS/Linux: download the `automatizer` binary and place it under `libs/pvsneslib/devkitsnes/bin/` (ensure it is executable) to be discoverable by the POSIX wrapper added in src.

If desired, the project can be extended to automatically publish built binaries to GitHub Releases as part of a release workflow.
