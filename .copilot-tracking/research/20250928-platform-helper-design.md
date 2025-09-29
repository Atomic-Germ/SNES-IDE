# Platform helper design (macOS-focused)

Purpose
- Provide a single helper module in `src/` (e.g., `src/platform_bridge.py`) that centralizes platform detection and the logic to locate or (optionally) fetch platform-native external artifacts (emulator binary, preferred editor CLI).
- The design below is research-only and proposes the exact functions and behavior that should be implemented and covered by the proposed failing tests.

Files to add (implementation PR):
- `src/platform_bridge.py`  (implementation)
- `tests/test_platform_binaries.py` (tests)

Recommended layout for external artifacts
- `libs/bsnes/` (keep Windows binary `bsnes.exe` here)
- `libs/bsnes/mac/` (place `bsnes` macOS binary and any resource files)
- `libs/bsnes/linux/` (place Linux binary or wrapper)

Primary responsibilities
- find_emulator(): return path to platform-appropriate emulator or None
- ensure_emulator_available(): if not present and running in CI, download official release asset into `libs/bsnes/<platform>/` and return path
- detect_editor(): return a callable command or path for launching an editor on the platform

Example implementation (research-only example code)

```python
# ...conceptual code to be added to src/platform_bridge.py...
import platform
import shutil
from pathlib import Path
import urllib.request
import json

REPO_BSNES_API = 'https://api.github.com/repos/bsnes-emu/bsnes/releases/latest'


def platform_name():
    return platform.system().lower()  # 'darwin', 'linux', 'windows'


def find_emulator():
    system = platform.system()
    if system == 'Windows':
        path = Path('libs/bsnes/bsnes.exe')
        if path.exists():
            return str(path)
    elif system == 'Darwin':
        path = Path('libs/bsnes/mac')
        # mac artifact could be either an app bundle or a single executable
        if path.exists():
            # choose the first executable-looking file
            for p in path.iterdir():
                if p.is_file() and os.access(p, os.X_OK):
                    return str(p)
    else:  # Linux
        path = Path('libs/bsnes/linux')
        if path.exists():
            for p in path.iterdir():
                if p.is_file() and os.access(p, os.X_OK):
                    return str(p)
    return None


def download_bsnes_for_macos(dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Query GitHub Releases for the latest macOS asset
    with urllib.request.urlopen(REPO_BSNES_API) as r:
        data=json.load(r)
    url=None
    for a in data.get('assets', []):
        name = a.get('name','').lower()
        if 'macos' in name or 'bsnes-macos' in name:
            url = a.get('browser_download_url')
            break
    if not url:
        url = 'https://github.com/bsnes-emu/bsnes/releases/download/nightly/bsnes-macos.zip'
    out = dest_dir / 'bsnes-macos.zip'
    urllib.request.urlretrieve(url, str(out))
    # unzip and return path to extracted files
    return out


def detect_editor():
    # prefer cli tools in order: code (VSCode), subl (Sublime), mate (TextMate), open (macOS)
    for name in ('code', 'subl', 'mate', 'nano', 'vi'):
        if shutil.which(name):
            return name
    # for macOS, 'open' is always available
    if platform.system() == 'Darwin' and shutil.which('open'):
        return 'open'
    return None
```

Operational notes
- Keep Windows shipped binaries in place to avoid disrupting Windows users.
- The helper should be tolerant: where possible prefer system-installed emulators/editors; otherwise, fall back to a `libs/<component>/<platform>/` artifact shipped by CI.
- For CI, the helper can include an environment-variable override (e.g., `SNES_IDE_BSNES_PATH`) so CI can point tests and builds at downloaded assets rather than perform runtime network downloads.

CI behavior
- For reproducibility and security, CI should download release artifacts during the workflow and place them under `libs/bsnes/<platform>/` (as proposed in the workflow YAML in research).
- The helper should first check `SNES_IDE_BSNES_PATH` and a well-known libs path before attempting any network fetches.

Security and caching
- When downloading assets in CI, use checksums or release tag pins to avoid silent upgrades or injecting malicious assets. Record the release tag used in CI logs and, when appropriate, provide the hash to the repository.

Testing strategy
- Start with the intentionally failing tests (red-light) to indicate missing platform artifacts.
- When CI adds the download step and artifacts, the tests should become green; that transition acts as the porting gate.

Next steps (if you want me to proceed beyond research):
- Prepare a PR that adds the helper module, integrates helper usage into the launcher, adds the failing tests into `tests/`, and commits a `.github/workflows/macos.yml` that implements the research workflow (CI changes will be done only after review).