<!-- markdownlint-disable-file -->
# Task Research Notes: Automation wrapper (prefer Python)

## Research Executed

### File Analysis
- `src/libs/pvsneslib/devkitsnes/automatizer.py`
  - A full Python implementation of the automatizer exists in the repository under `src/libs/pvsneslib/devkitsnes/automatizer.py` with a `SNESAutomatizer` class and a `__main__` entry that constructs and runs the automatizer.
  - Evidence: the repository contains `src/libs/pvsneslib/devkitsnes/automatizer.py` with a main execution block calling `automatizer.run()`.

- Windows wrappers referencing `automatizer.exe`
  - `src/tools/automatizer-batch.bat` contains a hard-coded path `%toolsDirectory%\libs\pvsneslib\devkitsnes\automatizer.exe` and executes it.
  - `src/tools/automatizer-batch.ps1` also builds a path to `automatizer.exe` and executes it when present.
  - These call sites must be migrated or made cross-platform to avoid relying on a Windows `.exe` on POSIX hosts.

- CI and release artifacts
  - The prebuilt pvsneslib release archives provide `devkitsnes/bin` native toolchain executables (assembler, linker, tcc), but they do not include a platform-agnostic `automatizer` executable. The Python script present in the repository serves as the most direct cross-platform replacement.
  - Evidence: pvsneslib release zips include `devkitsnes` but did not include an `automatizer.exe` for macOS in our earlier macOS import; our local `libs/pvsneslib/devkitsnes/bin` contained compilers/linkers but not `automatizer.exe`.

### Code Search Results
- `automatizer` references in the workspace:
  - `src/libs/pvsneslib/devkitsnes/automatizer.py` — Python implementation available.
  - `src/tools/automatizer-batch.bat` and `src/tools/automatizer-batch.ps1` — Windows wrappers that call `automatizer.exe` directly.
  - Other possible scripts or docs may reference `automatizer.exe` by name — search results in repo confirm several wrapper references.

### External Research
- #githubRepo:"alekmaul/pvsneslib automatizer"
  - #fetch:https://github.com/alekmaul/pvsneslib
  - Key info: The upstream `pvsneslib` project maintains `devkitsnes` with many tools, provides a `devkitsnes` Python utility sub-tree with assorted helpers, and documents building/packaging strategies. There is a Python tooling culture present (e.g., `816-opt.py`), so adding a Python-first automatizer is consistent with upstream patterns.

## Key Discoveries

1. A cross-platform automation entrypoint is already present as a Python script in our repo (`src/libs/pvsneslib/devkitsnes/automatizer.py`). Using it as the canonical automatizer on macOS/Linux removes the need for a native `automatizer.exe` and keeps CI reproducible.

2. Existing Windows wrapper scripts still expect `automatizer.exe` to exist under `libs/pvsneslib/devkitsnes/` — to prevent regression, wrappers should be updated to prefer the Python script on POSIX and fall back to the `.exe` only on Windows.

3. CI should ensure the Python automatizer is staged into `libs/pvsneslib/devkitsnes/` (or create a small POSIX wrapper under `libs/pvsneslib/devkitsnes/bin/automatizer`) so `platform_bridge.find_tool('automatizer')` will find it.

## Implementation Alternatives (evaluated)

A. Python-first wrapper (recommended)
- Keep the Python `automatizer.py` as the canonical implementation.
- Add a small POSIX wrapper script at `libs/pvsneslib/devkitsnes/bin/automatizer` that executes `python3 ../automatizer.py "$@"` and is executable; update Windows wrappers to prefer calling `automatizer` on PATH or `python automatizer.py` on POSIX.
- CI: copy `src/libs/pvsneslib/devkitsnes/automatizer.py` into `libs/pvsneslib/devkitsnes/` as part of macOS/Linux workflow, and create an executable POSIX wrapper.

Advantages: minimal build steps, uses existing code, portable, consistent with devkitsnes Python tools.
Limitations: Requires ensuring correct Python runtime and any Python dependencies are available in CI/dev machines (project already uses Python heavily).

B. Build a native automatizer binary for macOS (e.g., via PyInstaller)
- Use PyInstaller in CI to build an `automatizer` binary for macOS and copy into `libs/pvsneslib/devkitsnes/bin/`.

Advantages: one-file native binary similar to Windows `.exe` experience.
Limitations: PyInstaller must be run on macOS for macOS builds; code signing/notarization considerations; more complex CI packaging.

C. Ship the automatizer as a small Python package and pip install into CI
- Create a package for automatizer and `pip install -e .` or `pip install .` in CI to make `automatizer` CLI entrypoint available.

Advantages: canonical packaging, good for reuse.
Limitations: requires packaging work and versioning; heavier lift for initial port.

Recommended approach: start with (A) Python-first wrapper to minimize friction, and evaluate (C) for a follow-on release once the wrapper is stable.

## Complete Examples (what to implement)

1) POSIX wrapper to place under `libs/pvsneslib/devkitsnes/bin/automatizer` (make executable)

```bash
#!/usr/bin/env bash
# libs/pvsneslib/devkitsnes/bin/automatizer
# Small POSIX wrapper to run the Python automatizer shipped with the repo
set -e
# Resolve the script directory (this wrapper may be in bin/)
SCRIPT_DIR=$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")
# The python script is expected to be one directory up: ../automatizer.py
PY_AUTOMATIZER="$SCRIPT_DIR/../automatizer.py"
if [ -f "$PY_AUTOMATIZER" ]; then
  exec python3 "$PY_AUTOMATIZER" "$@"
else
  echo "automatizer Python script not found at $PY_AUTOMATIZER" >&2
  exit 1
fi
```

2) CI steps to stage python automatizer into libs path (macOS job example)

```yaml
- name: Stage Python automatizer for POSIX
  run: |
    mkdir -p libs/pvsneslib/devkitsnes
    cp src/libs/pvsneslib/devkitsnes/automatizer.py libs/pvsneslib/devkitsnes/ || true
    mkdir -p libs/pvsneslib/devkitsnes/bin
    cp -v src/libs/pvsneslib/devkitsnes/bin/automatizer.sh libs/pvsneslib/devkitsnes/bin/automatizer || true
    chmod +x libs/pvsneslib/devkitsnes/bin/automatizer || true
```

Note: `automatizer.sh` can be the wrapper above kept in `src/` and copied in CI.

3) Update Windows wrappers (conceptual) — to be applied in a follow-up implementation PR
- `automatizer-batch.bat` should attempt the following in order:
  - If running on Windows and `automatizer.exe` exists -> run it
  - Else if Python is available (`python` or `py`) and `automatizer.py` exists -> run `python automatizer.py ...`
  - Else show an informative error

- `automatizer-batch.ps1` should likewise prefer `automatizer.exe` on Windows; but also accept a Python fallback on POSIX when run under pwsh.

Example batch pseudocode:
```
if exist "%automatizerPath%" (
  "%automatizerPath%" "%userDirectory%" ...
) else if exist "%toolsDirectory%\libs\pvsneslib\devkitsnes\automatizer.py" (
  python "%toolsDirectory%\libs\pvsneslib\devkitsnes\automatizer.py" "%userDirectory%" ...
) else (
  echo "automatizer not found"
)
```

4) Red-light tests to gate the Python automatizer
- Add a test in `tests/` (red-light) to assert presence and basic health-check of the automatizer on POSIX CI:

```python
# tests/test_automatizer_redlight.py
import platform
import subprocess
from pathlib import Path


def test_automatizer_available_on_macos_linux():
    if platform.system() == 'Windows':
        return
    # prefer a POSIX wrapper on PATH
    path = Path('libs/pvsneslib/devkitsnes/bin/automatizer')
    py = Path('libs/pvsneslib/devkitsnes/automatizer.py')
    assert path.exists() or py.exists(), 'automatizer not staged for POSIX: CI must place a Python wrapper (automatizer.py) into libs/pvsneslib/devkitsnes/'
    # Optional smoke-run
    if py.exists():
        res = subprocess.run(['python3', str(py), '--help'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert res.returncode in (0, 2), 'automatizer --help returned unexpected status'
```

(Place this test in the research folder for review before adding to active tests.)

## Migration Plan (step-by-step)

1. Research-only step: Create the plan and tests (this document) and confirm with maintainers.
2. CI staging: Add a CI step (macOS and Linux jobs) that copies `src/libs/pvsneslib/devkitsnes/automatizer.py` to `libs/pvsneslib/devkitsnes/` and creates the POSIX wrapper in `libs/pvsneslib/devkitsnes/bin/automatizer`. Run the red-light test to make the gate green.
3. Wrapper update: Modify `src/tools/automatizer-batch.bat` and `src/tools/automatizer-batch.ps1` so they prefer the Python wrapper on POSIX and keep Windows `.exe` as the default on Windows.
4. Documentation: Add `docs/automatizer.md` describing usage, CLI flags, and how to use the python automatizer.
5. Optional: Package the automatizer as a small pip-installable tool or build a PyInstaller single binary for releases for parity with `automatizer.exe` if desired.

## Risks and Mitigations
- Risk: Automatizer Python script depends on local devkits toolchain being present in `libs/pvsneslib/devkitsnes/bin/` (wla, tcc, etc.). Mitigation: CI already stages devkits toolchain via prebuilt archive; ensure the Python wrapper only runs smoke-checks until tools are present.
- Risk: Automatizer may require additional Python dependencies. Mitigation: inspect `automatizer.py` for external imports; include them in `requirements.txt` or stage a virtualenv in CI.
- Risk: Changing wrappers may confuse Windows users. Mitigation: keep existing Windows behavior and only prefer Python on POSIX.

## Success Criteria
- POSIX CI jobs pass the new automatizer red-light test because the Python automatizer is staged into `libs/pvsneslib/devkitsnes/` and the POSIX wrapper is executable.
- `src/tools/automatizer-batch.bat` and `.ps1` are updated (in follow-up PR) to prefer the Python wrapper on non-Windows platforms without breaking Windows usage.
- Local macOS/Linux developers can run `libs/pvsneslib/devkitsnes/bin/automatizer <args>` and observe the same behavior as Windows users had with `automatizer.exe` for supported feature sets.

## Recommended Next Action (implementation-ready)
- I will prepare a small set of changes (research-only artifacts are created here). If you want, I can then implement the minimal CI staging step and optional POSIX wrapper into `.github/workflows/macos.yml` and add the red-light test into `tests/` to flip the new automation wrapper gate to green. After CI confirms, we can create a follow-up PR that updates `automatizer-batch.bat` and `automatizer-batch.ps1` to prefer the Python CLI on POSIX.

````
<!-- #githubRepo:"alekmaul/pvsneslib automatizer" -->
#fetch:https://github.com/alekmaul/pvsneslib
````


