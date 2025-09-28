<!-- markdownlint-disable-file -->
# Research: Windows CI for SNES-IDE

## Summary
This research gathers repository evidence and external references needed to design a comprehensive Windows CI build and test workflow for SNES-IDE. It focuses on building the project on `windows-latest` GitHub Actions runners, producing the `SNES-IDE-out` build output (including `INSTALL.bat`), packaging Python tools into Windows executables using PyInstaller, running installer and tests, caching Python dependencies, and uploading build artifacts.

## Repository Findings (verified)
- Project contains a Windows-oriented build pipeline based on a Python-driven `build` process that outputs `SNES-IDE-out`:
  - `build/build.bat` (invokes `python .\build.py`)
  - `build/build.py` (copies files and compiles Python scripts into `.exe` using `buildModules.buildPy`)
  - `build/buildModules/buildPy/__init__.py` (uses PyInstaller to create Windows `.exe` files)
- Installer and packaging:
  - Root `INSTALL.bat` is an installer that must be created/run from the `SNES-IDE-out` output.
  - Tests reference the resulting `SNES-IDE-out/INSTALL.bat` (see `tests/test.py` which attempts to run the installer if present).
- Linux support uses Wine to invoke Windows batch scripts (e.g., `linux/src/install.sh` runs `wine cmd /c "./build/build.bat linux"`).
- Docs instruct Windows builds to run `cmd /c build\\build.bat` and users to run `INSTALL.bat` from output directory.

Files of interest:
- `build/BUILDING_FROM_SOURCE.md` — high-level build instructions
- `build/build.bat` — Windows batch wrapper to run `build.py`
- `build/build.py` — build orchestration and compile routine for Python files (uses `buildModules.buildPy`)
- `build/buildModules/buildPy/__init__.py` — PyInstaller invocation and packaging behavior
- `tests/test.py` — simple test using `SNES-IDE-out/INSTALL.bat`
- `.github/workflows/CI.yml` — current CI which only runs `INSTALL.bat` on Windows (insufficient because build output not produced first)

(Repository evidence compiled from local file inspection.)

## Tooling & Build Steps (repo-derived)
- Primary build entrypoint for CI: `cmd /c build\\build.bat` (or directly `build\\build.bat`) on Windows runners.
- `build.py` will:
  - create `SNES-IDE-out` by copying files and directories
  - use `buildModules.buildPy.main(...)` which invokes PyInstaller to convert `.py` to `.exe`
  - expect a working Python and pip environment (and may install PyInstaller dynamically if missing)
- Tests: `python tests/test.py` checks for `SNES-IDE-out/INSTALL.bat` and tries to execute it (shell True)

## External References (authoritative, concise)
- GitHub Actions: workflow syntax, `runs-on: windows-latest`, step shells and `run` behavior, job matrix and `defaults.run.shell` (docs: Workflow syntax for GitHub Actions).
  - Using `cmd`, `pwsh` or `powershell` shells on Windows; default `pwsh` is used unless `shell: cmd` specified.
- PyInstaller: CLI options (notably `--onefile`, `--icon`, `--noconfirm`, dist/work paths), platform-specific notes about Visual C++ runtimes and UPX. PyInstaller is invoked by `buildModules.buildPy`.
- actions/cache: recommended for caching Python packages (pip cache) using `actions/cache@v4` with keys containing `runner.os` and `hashFiles('**/requirements*.txt')`.
- actions/upload-artifact & download-artifact: for storing `SNES-IDE-out` and test logs between jobs.

## CI Patterns & Best Practices (validated)
- Build job should run on `windows-latest` and install required Python packages (PyInstaller).
- Use `actions/cache` to cache pip wheel caches and speed subsequent runs.
- Separate build and test stages: build produces `SNES-IDE-out`, upload as artifact; test job downloads artifact, runs `SNES-IDE-out/INSTALL.bat`, and runs Python tests.
- Use `actions/upload-artifact@v4` to persist the output and `actions/download-artifact@v5` for downstream jobs.
- Ensure the build step uses deterministic Python version (use `actions/setup-python@v4` to pin Python version).

## Example Commands (derived from repo + PyInstaller docs)
- Build on Windows runner (cmd):
  - `cmd /c build\\build.bat`
- Ensure Python and PyInstaller installed (PowerShell or cmd):
  - `python -m pip install --upgrade pip PyInstaller`
- Run tests (Python):
  - `python -u tests/test.py`

## Risks & Edge Cases
- PyInstaller on windows-latest needs Visual C++ runtime available when running generated executables — ensure packaging includes required redistributables or installer includes VCRedist as needed.
- Build time on hosted runners may be long; consider caching and splitting steps.
- Artifacts larger than default limits need careful retention settings and possibly compressing contents.

## Implementation Guidance (high-level)
- CI Workflow flow (recommended):
  1. Checkout code
  2. Setup Python (pin version)
  3. Restore pip cache
  4. Install PyInstaller and other build dependencies (if any)
  5. Run `build\\build.bat` to create `SNES-IDE-out`
  6. Upload `SNES-IDE-out` as artifact
  7. Run a downstream job (needs: build) which downloads artifact, runs `SNES-IDE-out/INSTALL.bat` and executes `python -u tests/test.py` to validate installer
  8. Upload test logs/artifacts on failure or success for debugging

- Optional: add a matrix to test multiple Python versions or Windows variants (windows-2022, windows-2025) if required.

---

End of research notes.
