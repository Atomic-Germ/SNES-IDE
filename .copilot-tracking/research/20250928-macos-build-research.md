<!-- markdownlint-disable-file -->
# Task Research Notes: macOS build and runtime dependencies

## Research Executed

### File Analysis
- `build/BUILDING_FROM_SOURCE.md`
  - Finds explicit Linux instructions that require Wine 9.0+ and installing Windows Python under Wine. This indicates the repository currently treats non-Windows platforms by emulating Windows rather than providing native macOS support.
- `libs/bsnes/` (contains `bsnes.exe`)
  - Project currently ships a Windows-only emulator binary in `libs/bsnes/bsnes.exe`.
- `libs/notepad++/` (contains `notepad++.exe`)
  - Project ships Notepad++ Windows distribution assets and an `.exe` editor binary.
- `src/snes-ide.py`
  - Compatibility wrapper prefers running PowerShell (`pwsh`) with `.ps1` when present, otherwise falls back to `.bat` via `cmd` — shows intention to preserve Windows workflows while enabling cross-platform `pwsh` when available.
- `build/buildModules/buildPy/__init__.py` and other build scripts
  - Use PyInstaller to create distribution binaries (.exe on Windows) and contain logic to install / invoke PyInstaller when missing.
- `requirements.txt`
  - Declares `pyinstaller`, `wheel` and optional `pytest`; includes note about `tkinter` and system Tcl/Tk dependency.
- `linux/src/install.sh` and `linux/installers/README.md`
  - Linux installer scripts copy project into a Wine prefix and instruct users to install Windows-specific binaries into the Wine environment. This pattern must be replaced for native macOS support.

### Code Search Results
- term: `wine`
  - actual matches found: references in `build/build.py`, `build/BUILDING_FROM_SOURCE.md`, `linux/src/install.sh`, `src/tools/*` helper docs — repo currently depends on Wine for Linux.
- term: `bsnes` / `bsnes.exe`
  - actual matches found: `libs/bsnes/bsnes.exe`, `src/snes-ide.py` menu option for launching emulator, README references to bsnes GitHub project.
- term: `notepad++` / `notepad++.exe`
  - actual matches found: `libs/notepad++/notepad++.exe`, `INSTALL.bat`, `INSTALL.ps1`, README references.
- term: `pyinstaller`
  - actual matches found: `build/buildModules/buildPy/__init__.py`, `requirements.txt`, build/README mentions PyInstaller usage and platform-specific notes for macOS.
- term: `pwsh` / `PowerShell` / `.ps1`
  - actual matches found: `src/snes-ide.py` wrapper logic and many `.ps1` support scripts in `src/tools`.
- term: `tkinter` / `tcl` / `tcl-tk`
  - actual matches found: `requirements.txt` notes; GUI code depends on tkinter being available.

### External Research
- #githubRepo:"bsnes-emu/bsnes macOS builds and releases"
  - #fetch:https://github.com/bsnes-emu/bsnes
  - Key info gathered: bsnes is multi-platform and publishes macOS release assets (nightly and tagged releases include `bsnes-macos.zip`); therefore the emulator dependency can be satisfied on macOS by using official macOS builds rather than bundling or running the Windows binary under Wine.
- #fetch:https://github.com/bsnes-emu/bsnes/releases
  - Key info: releases include platform-specific artifacts (Windows, macOS, Linux) and nightly releases have direct downloadable macOS zips suitable for CI download.
- #fetch:https://pyinstaller.org/en/stable/usage.html
  - Key info: PyInstaller supports macOS app bundle creation (`--windowed` => `.app`), has macOS-specific options (`--osx-bundle-identifier`, `--codesign-identity`, `--target-arch`), and documents macOS multi-arch, codesigning and notarization considerations. PyInstaller is recommended for building native macOS applications, but must be run on macOS to create macOS bundles (PyInstaller is not a cross-compiler).
- #fetch:https://pyinstaller.org/en/stable/requirements.html
  - Key info: PyInstaller runs on macOS 10.15+ and builds macOS bundles for the OS it runs on. Building for older macOS versions requires building on that older macOS. macOS bootloader and code signing caveats are documented.
- #fetch:https://www.winehq.org/
  - Key info: Wine can run Windows binaries on macOS but Wine on macOS is fragile, especially on Apple Silicon; relying on Wine for macOS is discouraged unless unavoidable.
- #fetch:https://docs.brew.sh/ and https://brew.sh/
  - Key info: Homebrew is the de-facto package manager for macOS CI/runners; Homebrew can install Python, PowerShell (`pwsh`), `tcl-tk`, and many utilities needed for building and testing on macOS; `brew install --cask` can install GUI apps (e.g., Visual Studio Code) on macOS runners.
- #githubRepo:"notepad-plus-plus/notepad-plus-plus"
  - #fetch:https://github.com/notepad-plus-plus/notepad-plus-plus
  - Key info: Notepad++ is Windows-only (Win32), though source can be built on Windows. Notepad++ is not a suitable native macOS editor — the project should detect a macOS-native editor (e.g., Visual Studio Code, Sublime, TextMate, or fallback to `open -a TextEdit`) when running on macOS.

### Project Conventions
- Standards referenced: `requirements.txt`, `build/` scripts using PyInstaller, `src/snes-ide.py` style of OS detection and fallback logic for scripts (`pwsh` preferred, fall back to `.bat` via `cmd`).
- Instructions followed: keep Windows flow intact; detect and prefer native tools on host OS; use platform-specific assets in `libs/` or a per-platform `libs/<platform>/` layout rather than bundling Windows-only binaries in the top-level `libs/`.

## Key Discoveries

### Project Structure
- Binaries for Windows are checked into `libs/` (`notepad++.exe`, `bsnes.exe`).
- Build system is Python/PyInstaller-driven with supporting shell/PowerShell wrappers. For non-Windows platforms the repo currently uses Wine to run Windows-specific artifacts.
- There is an established pattern in `src/snes-ide.py` to detect `pwsh` and prefer `.ps1` scripts, indicating that introducing `pwsh` on macOS (via Homebrew) is both intended and supported.

### Implementation Patterns
- Cross-platform strategy currently used: "run Windows binaries inside Wine on POSIX systems" rather than provide native binaries.
- PyInstaller is used to produce distributables and its docs indicate the correct approach is to run PyInstaller on each target OS in CI to produce native artifacts (Windows on windows-latest, macOS on macos-latest, Linux on linux-latest).
- There is existing wrapper code that can be extended to detect platform and select platform-appropriate binaries or download them at install time.

### Complete Examples
```python
# Example (taken from repository pattern) - platform-aware launcher logic
# ...existing code...
ps1_path = base_path.with_suffix('.ps1')
bat_path = base_path.with_suffix('.bat')
# Prefer pwsh if available (works on macOS via Homebrew) -> use .ps1
if ps1_path.exists() and shutil.which('pwsh'):
    cmd = ['pwsh', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ps1_path)]
# Fallback to Windows .bat via cmd (Windows only)
elif bat_path.exists() and shutil.which('cmd'):
    cmd = ['cmd', '/c', str(bat_path)]
else:
    raise FileNotFoundError(...)
# ...existing code...
```

### API and Schema Documentation
- No external API schema required. The main integration points are: (1) launching external emulator binary, (2) launching external text editor, (3) PyInstaller build pipeline for producing platform artifacts.

### Configuration Examples
```yaml
# Minimal GitHub Actions macOS job sketch (conceptual)
name: macOS build
runs-on: macos-latest
steps:
- uses: actions/checkout@v4
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
- name: Install Homebrew deps
  run: |
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || true
    brew install python tcl-tk
    brew install --cask visual-studio-code || true
    brew install powershell || true
- name: Install Python deps
  run: python -m pip install -U pip && pip install -r requirements.txt
- name: Download native bsnes for macOS (placeholder)
  run: curl -L -o libs/bsnes/bsnes-macos.zip "https://github.com/bsnes-emu/bsnes/releases/download/nightly/bsnes-macos.zip"
- name: Build with PyInstaller
  run: pyinstaller --noconfirm --onefile --windowed --icon=assets/icons/icon.icns src/snes-ide.py
```

### Technical Requirements (macOS)
- macOS runner (github `macos-latest`) — PyInstaller must run on macOS to produce native macOS bundles.
- Homebrew (recommended) to install: Python (if not using actions/setup-python), `tcl-tk` (for tkinter), `powershell` (`pwsh`) if `.ps1` scripts should run, `visual-studio-code` optionally for local editor tests. Homebrew can be used to install additional developer tooling.
- PyInstaller (pip install pyinstaller) and optionally `codesign`/`productbuild` for signing and packaging (notarization requires Apple Developer credentials and is out-of-scope for initial porting).
- Native bsnes macOS build (downloaded from bsnes releases or built from source) to replace `libs/bsnes/bsnes.exe` when running on macOS.

## Recommended Approach

After evaluating alternatives (continue relying on Wine vs. adopt native macOS tooling), I recommend the single, consolidated approach below for macOS.

Recommended approach (single, evidence-backed):
- Keep Windows artifacts as-is in `libs/*` to avoid stomping on Windows functionality.
- Add a small platform layer and CI steps that select and install native macOS artifacts at build/install-time:
  - At CI/install time on macOS, fetch the official bsnes macOS release artifact and place it in a macOS-specific path (e.g., `libs/bsnes/mac/bsnes` or `libs/bsnes/bsnes-macos.zip` extracted into an OS-specific folder). Use the GitHub releases URL for bsnes to download correct binary for the runner architecture.
  - Implement editor detection: when running on macOS prefer `code` (VS Code CLI) -> `subl`/`sublime` -> `open -a "Visual Studio Code"` -> `open -a TextEdit` as fallbacks. Keep Notepad++ available for Windows only.
  - Use `pwsh` on macOS (installable via Homebrew) to enable executing existing `.ps1` scripts instead of `.bat` fallbacks. Add CI step to install `powershell` if needed.
  - Build native macOS distributables in CI using PyInstaller on `macos-latest`. Configure PyInstaller options `--windowed`, `--osx-bundle-identifier`, and `--target-arch` (universal2 or `arm64`/`x86_64`) based on runner and release targets. Reserve code signing and notarization for a follow-up task once the unsigned builds are working in CI.
  - For GUI/`tkinter` tests on macOS CI ensure `tcl-tk` system dependency is available via Homebrew and use actions/setup-python with a Python build that is compatible with the brewed tcl-tk (or use Homebrew Python which will be compatible).

Trade-offs & rationale:
- Pros: Native performance and user experience (bsnes macOS binary, native editors); avoids Wine fragility on macOS and Apple Silicon issues; keeps Windows flow untouched.
- Cons: Requires CI per-platform build (PyInstaller is not a cross-compiler) and per-platform test jobs; initial work to add download/selection logic and CI steps; code signing / notarization has additional complexity (separate task).

## Implementation Guidance
- Objectives: Provide native macOS runtime and CI builds while preserving Windows workflows.
- Key Tasks:
  1. Add `libs/<platform>/` layout or `libs/<component>/<platform>/` and update launcher/detection logic to prefer platform-appropriate binary.
  2. Add modular helper in Python for "find or fetch native binary" (e.g., fetch bsnes macOS artifact when missing); ensure it returns platform-appropriate path for launcher.
  3. Add macOS CI job in `.github/workflows/`:
     - Install Homebrew deps (tcl-tk, powershell, optionally Visual Studio Code), setup Python, pip install requirements, download native bsnes macOS artifact, run tests, build PyInstaller macOS bundle.
  4. Add "red light" failing tests initially to mark work items that must be completed (see suggested tests below).
  5. Update documentation and `BUILDING_FROM_SOURCE.md` to document macOS steps and CI expectations.
- Dependencies:
  - Homebrew (on macOS) for `tcl-tk`, `powershell`, optional editor casks.
  - PyInstaller (pip), Python >= 3.8.
  - bsnes macOS release artifact (downloaded from bsnes GitHub releases) or source build instructions if preferred.
- Success Criteria:
  - macOS CI job runs and produces a `dist/*.app` bundle using PyInstaller for macOS.
  - Tests that were intentionally introduced as failing initially become green after implementing the download/selection logic and CI steps.
  - Existing Windows jobs remain unchanged and continue producing Windows artifacts.

## Suggested "Red Light" (deliberately failing) tests to guide incremental porting
- tests/test_platform_binaries.py (new)
```python
import platform
import shutil

def test_emulator_binary_for_platform_exists():
    # Intentionally fail until CI fetch step is added
    if platform.system() == 'Darwin':
        assert shutil.which('bsnes') or Path('libs/bsnes/mac/bsnes').exists(), 'bsnes macOS binary missing - CI must download it'
    elif platform.system() == 'Linux':
        assert shutil.which('bsnes') or Path('libs/bsnes/linux/bsnes').exists(), 'bsnes linux binary missing - CI must download it'
    else:
        assert Path('libs/bsnes/bsnes.exe').exists(), 'Windows bsnes binary missing'
```
- tests/test_editor_detection.py (new)
```python
import platform
import shutil

def test_editor_detection():
    # Initially fail on macOS to force editor-install / detection work
    if platform.system() == 'Darwin':
        assert shutil.which('code') or shutil.which('subl') or shutil.which('open'), 'No known editor detected on macOS; CI step must provide a fallback or documentation'
```

## Next steps & decision required
- I recommend proceeding with the recommended approach: add platform-specific binary acquisition (download bsnes macOS artifact in CI), implement editor detection and macOS CI PyInstaller build, and introduce small failing tests that define the "red light" acceptance rules.

Which approach aligns better with your objectives?
- I recommend: "Native macOS artifacts fetched/installed in CI + PyInstaller macOS builds + Homebrew-managed macOS deps + preserve Windows binaries unchanged." 

Should I focus the next round of research on the CI workflow changes (download URLs, GitHub Actions job templates, and precise Homebrew packages and commands needed) and prepare a PR that adds the macOS CI job, the failing tests, and the platform-detection helper code (research-only: no source edits in this step)?