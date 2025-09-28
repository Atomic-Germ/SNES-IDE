<!-- markdownlint-disable-file -->
# Task Details: Windows CI for SNES-IDE

## Research Reference

**Source Research**: #file:../research/20250928-windows-ci-research.md

## Phase 1: Discovery & Prep

### Task 1.1: Verify build entrypoint and artifacts

Validate that the Windows build entrypoint is `build\\build.bat` and that the build produces `SNES-IDE-out/INSTALL.bat` which tests rely on.

- **Files**:
  - `build/build.bat` - wrapper that calls `build.py`
  - `build/build.py` - orchestrates creation of `SNES-IDE-out`
  - `build/buildModules/buildPy/__init__.py` - PyInstaller-based packaging
- **Success**:
  - Confirm `SNES-IDE-out/` is produced and contains `INSTALL.bat` and compiled `.exe` files.
- **Research References**:
  - #file:../research/20250928-windows-ci-research.md (Lines 7-27) - Repository findings and file list
- **Dependencies**:
  - Local knowledge of how `build.py` calls `buildModules.buildPy`

### Task 1.2: Identify CI platform requirements

Specify required runner, Python version, caching strategy, and artifact handling.

- **Files**:
  - `.github/workflows/CI.yml` - current minimal CI stub
- **Success**:
  - A documented list of runner and tool requirements (Python, PyInstaller, Visual C++ redist guidance)
- **Research References**:
  - #file:../research/20250928-windows-ci-research.md (Lines 28-42) - Tooling and external references
- **Dependencies**:
  - Access to GitHub Actions runner selectors (windows-latest)

## Phase 2: CI Design & Tasks

### Task 2.1: Build job design (Windows)

Design a job that runs on `windows-latest` to produce `SNES-IDE-out` and upload it as an artifact.

- **Specific action items**:
  1. Checkout repository (`actions/checkout@v4`)
  2. Setup Python (`actions/setup-python@v4`) pinned to the required version (recommend 3.10+)
  3. Restore pip cache (use `actions/cache@v4`, key: `${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}`)
  4. Install build dependencies: `python -m pip install --upgrade pip PyInstaller`
  5. Run `cmd /c build\\build.bat` or `build\\build.bat` with `shell: cmd` or default `pwsh`
  6. Upload `SNES-IDE-out` via `actions/upload-artifact@v4`

- **Files to create/modify**:
  - `.github/workflows/CI.yml` (replace or add a `build-windows` job that performs the above)
- **Success**:
  - `SNES-IDE-out` artifact uploaded and visible in workflow run
- **Research References**:
  - #file:../research/20250928-windows-ci-research.md (Lines 36-49) - CI patterns and PyInstaller guidance
- **Dependencies**:
  - PyInstaller availability and pip access on runner

### Task 2.2: Test job design (needs: build)

Design a downstream job that downloads `SNES-IDE-out`, runs `INSTALL.bat`, and executes Python tests.

- **Specific action items**:
  1. `needs: build-windows`
  2. `runs-on: windows-latest`
  3. `uses: actions/download-artifact@v5` to fetch `SNES-IDE-out`
  4. Run `SNES-IDE-out\\INSTALL.bat` with `shell: cmd` to install to the runner workspace (or simulate execution); capture logs
  5. Run `python -u tests/test.py` to validate installer and basic integration
  6. Upload test logs as artifacts on failure or success

- **Files to create/modify**:
  - `.github/workflows/CI.yml` - add `test` job dependent on `build-windows`
- **Success**:
  - Tests complete with exit code 0; test logs available as artifact
- **Research References**:
  - #file:../research/20250928-windows-ci-research.md (Lines 50-57) - Example commands
- **Dependencies**:
  - `SNES-IDE-out` artifact produced by build job

## Phase 3: Optimization & Hardening

### Task 3.1: Caching and speed

- **Specific actions**:
  - Cache pip cache and optionally PyInstaller cache across runs using `actions/cache@v4`
  - Use cache keys that include `runner.os` and `hashFiles` of lock files
- **Research References**:
  - #file:../research/20250928-windows-ci-research.md (Lines 36-42)

### Task 3.2: Failure diagnostics

- **Specific actions**:
  - Upload build logs and `SNES-IDE-out` artifact for debugging
  - Add `if: failure()` steps to capture system information and list of files
- **Success**:
  - Sufficient logs to debug build failures

## Files to create/modify (summary)
- `.github/workflows/CI.yml` - replace current minimal Windows job with a multi-job pipeline (build + test) following this plan
- Optionally create `.github/workflows/windows-build.yml` as a focused reusable workflow

## Success Criteria
- `build-windows` job produces `SNES-IDE-out` and uploads it (artifact exists)
- `test` job downloads artifact, runs `INSTALL.bat`, and `python -u tests/test.py` with exit code 0
- Pip cache restores and significantly reduces subsequent run times (measurable cache hits)
- Artifacts and logs are available for debugging failures

