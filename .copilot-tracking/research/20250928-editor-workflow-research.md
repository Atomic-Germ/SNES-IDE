<!-- markdownlint-disable-file -->
# Task Research Notes: Editor workflow (VS Code primary, Vim config secondary)

## Research Executed

### File Analysis
- `src/platform_bridge.py`
  - Already implements a `detect_editor()` helper and is referenced by `src/snes-ide.py` to choose a preferred editor at runtime. This is the primary integration point for editor selection.
  - Evidence: `src/platform_bridge.py` contains a `detect_editor()` function and `src/snes-ide.py` calls `platform_bridge.detect_editor()` before launching editors.

- `src/snes-ide.py`
  - `run_with_compat('text-editor')` uses `platform_bridge.detect_editor()` and then runs the detected editor via `subprocess.run([editor, str(self.path)], check=True)` or falls back to `open` on macOS.

- `libs/notepad++/notepad++.exe`
  - The repository currently ships Notepad++ for Windows only. Editor workflow changes will avoid using this binary on macOS and Linux and prefer native editors.

- Tests
  - Existing research red-light tests include an editor detection test that asserts presence of `code`, `subl`, `mate`, or `open` on macOS; these will be adapted to prefer `code` (VS Code) in CI once the install steps are in place.

### Code Search Results
- `detect_editor` and `text-editor` usage
  - Files discovered: `src/platform_bridge.py`, `src/snes-ide.py` — these are the places to integrate the editor policy change.
- `notepad++` / `notepad++.exe`
  - Files discovered: `libs/notepad++/notepad++.exe` and references in `src/snes-ide.py` help text. The Notepad++ binary will remain for Windows but not be preferred on macOS.
- Tests referencing editor detection
  - Files discovered: `.copilot-tracking/research/20250928-macos-failing-tests.py` and `tests/test_editor_detection.py` (proposed/placed in research). These tests will be used as red-light gates until VS Code is available in CI.

### External Research
- #githubRepo:"microsoft/vscode"
  - #fetch:https://code.visualstudio.com/docs/configure/command-line
    - Key facts: `code` is the VS Code CLI: use `code .` to open a folder, `--wait` to block until closed, `--new-window` to open a new window. On macOS, users must run "Shell Command: Install 'code' command in PATH" or manually add `/Applications/Visual Studio Code.app/Contents/Resources/app/bin` to PATH.
  - #fetch:https://code.visualstudio.com/docs/setup/mac
    - Key facts: On macOS you download the app, place into `/Applications`, and run the Shell Command from the Command Palette to install the `code` CLI — or add the path to the shell profile.
- #fetch:https://formulae.brew.sh/cask/visual-studio-code
  - Key facts: Homebrew cask `visual-studio-code` can install VS Code on macOS runners using `brew install --cask visual-studio-code`. The cask provides a deterministic method to install VS Code on GitHub-hosted macOS runners.
- #githubRepo:"VSCodeVim/Vim"
  - #fetch:https://github.com/VSCodeVim/Vim
    - Key facts: VSCodeVim provides Vim emulation inside VS Code and supports `.vimrc` via experimental `.vimrc` integration; recommended as an option for Vim users inside VS Code.
- #githubRepo:"amix/vimrc"
  - #fetch:https://github.com/amix/vimrc
    - Key facts: `amix/vimrc` is a well-known, production-ready starting point for a robust `.vimrc`; it provides both minimal and 'awesome' bundles; useful as a template for our project's recommended Vim configuration.

### Project Conventions
- Use `platform_bridge.detect_editor()` as the canonical place for runtime detection and launching logic.
- CI should provide a deterministic `code` CLI on macOS (via Homebrew cask) and ensure `code` appears on PATH (or create a symlink) so `platform_bridge.detect_editor()` will find it via `shutil.which('code')`.
- For Vim users, supply a small, repository-contained `vimrc` example in the docs (in this research area) and reference a curated plugin list; do not overwrite users' own dotfiles.

## Key Discoveries

### Runtime behavior desired
- On macOS and Linux prefer `code` (VS Code CLI) when `shutil.which('code')` returns a path.
- If `code` is not present, fall back in order: `subl` (Sublime CLI), `mate` (TextMate CLI), `open` (macOS default), then `vim` or `nano` for terminal users.
- Preserve Windows preference for `notepad++` on Windows hosts.

### CI behavior to support VS Code in macOS jobs
- Use Homebrew cask to install Visual Studio Code in the macOS workflow: `brew install --cask visual-studio-code`.
- Make sure `code` is available in PATH after the install: either run the VS Code Shell Command (not available headlessly) or create a symlink from the app bin into `/usr/local/bin` or `$HOME/.local/bin`. Example safe command for CI:

  # If `code` is not present, add a link to the app's bin
  if ! command -v code >/dev/null 2>&1; then
    sudo ln -sf "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" /usr/local/bin/code || true
  fi

- Alternatively for reproducibility, on `macos-latest` we may prefer to rely on the Homebrew cask and then assert `shutil.which('code')` is available in subsequent steps.

### Vim support strategy
- Provide a minimal repository `vimrc` example and a short guide in README explaining how to install a recommended `.vimrc` (use `amix/vimrc` reference) and how to add project-specific settings via `~/.vim_runtime/my_configs.vim` or a `.vimrc.local` in project folder.
- Recommend using `VSCodeVim` inside VS Code for users who prefer Vim bindings, and document how to enable `.vimrc` support (experimental) and how to configure `vim.vimrc.enable` if desired.

## Complete Examples

### Platform detection snippet (to add to `src/platform_bridge.py` - research example)
```python
# ...existing code...
import shutil
from typing import Optional


def detect_editor() -> Optional[str]:
    """Detect a preferred editor CLI on the current platform.

    Preference order on POSIX: code (VS Code CLI) -> subl -> mate -> open -> vim -> nano
    Windows: prefer Notepad++ binary bundled in libs if present.
    """
    # ...existing code...
    candidates = ["code", "subl", "mate", "open", "vim", "nano"]
    for name in candidates:
        if shutil.which(name):
            return name

    # Windows fallback: check for bundled notepad++
    if platform.system() == 'Windows':
        candidate = Path('libs') / 'notepad++' / 'notepad++.exe'
        if candidate.exists():
            return str(candidate)

    return None
# ...existing code...
```

### How `snes-ide.py` should launch VS Code (research example)
```python
# ...existing code...
editor = platform_bridge.detect_editor()
if editor == 'code':
    # Open project folder in a new VS Code window
    subprocess.run([editor, '--new-window', str(self.path)], check=True)
elif editor in ('subl', 'mate'):
    subprocess.run([editor, str(self.path)], check=True)
elif editor == 'open':
    subprocess.run(['open', str(self.path)], check=True)
# ...existing code...
```

### GitHub Actions macOS job snippet to install VS Code CLI
```yaml
- name: Install VS Code (CLI)
  run: |
    brew list --cask visual-studio-code || brew install --cask visual-studio-code
    # Ensure 'code' CLI is available for subsequent steps
    if ! command -v code >/dev/null 2>&1; then
      sudo ln -sf "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" /usr/local/bin/code || true
    fi
    code --version || true
```

### Red-light test for editor availability (pytest)
```python
# tests/test_editor_detection.py
import platform
import shutil


def test_preferred_editor_present_on_macos():
    if platform.system() != 'Darwin':
        return
    # Gate: prefer VS Code in CI; accept terminal vim as fallback
    assert shutil.which('code') or shutil.which('vim') or shutil.which('open'), (
        'No supported editor available on macOS CI: install VS Code CLI or ensure vim/open is available'
    )
```

### Minimal example `.vimrc` for SNES/6502/65c816 assembly work (to be included in docs)
```
" Minimal vimrc for SNES-IDE contributors
set nocompatible
filetype plugin indent on
syntax on
set number
set tabstop=4
set shiftwidth=4
set expandtab
set autoindent
" Recommended plugins (use your preferred plugin manager):
" - preservim/nerdtree
" - dense-analysis/ale  (linting)
" - tpope/vim-commentary
" - scrooloose/syntastic

" Project-local settings override:
if filereadable('.vim_local')
  source .vim_local
endif
```

## Configuration Examples
```yaml
# Add to macOS CI workflow
- name: Install VS Code (CLI)
  run: |
    brew install --cask visual-studio-code || true
    if ! command -v code >/dev/null 2>&1; then
      sudo ln -sf "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" /usr/local/bin/code || true
    fi
```

## Technical Requirements
- macOS CI: Homebrew + `visual-studio-code` cask to ensure `code` CLI is available.
- CI: Ensure PATH includes `/usr/local/bin` or symlink as shown above.
- Developer machines: VS Code installed or terminal `vim` available.
- Optional: `VSCodeVim` extension for users who want Vim emulation inside VS Code.

## Recommended Approach
- Implement the following sequence:
  1. Add CI step to install VS Code in `macos-latest` CI job (Homebrew cask + symlink) and assert `code --version` is present.
  2. Update `platform_bridge.detect_editor()` to prefer `code` on POSIX hosts (as shown above) and keep fallbacks.
  3. Add `tests/test_editor_detection.py` red-light test to assert presence of `code` or a terminal editor on macOS CI — CI job will install `code`, flipping the red-light to green.
  4. Provide a `docs/editor.md` fragment (research-only here) and a minimal `.vimrc` example (in `.copilot-tracking/research/` for review) that will be copied into `docs/` or `README.md` once the approach is confirmed.
  5. Recommend `VSCodeVim` for users who want Vim keybindings; document how to enable `.vimrc` support if desired.

## Implementation Guidance
- Objectives: Make VS Code the canonical editor on macOS CI and in developer workflows while preserving Vim users with a simple documented config.
- Key Tasks:
  - Add CI snippet to install VS Code and make `code` available.
  - Add red-light pytest that requires the presence of `code` (or `vim`) on macOS CI until the CI step is in place.
  - Add small documentation fragment and provide example `.vimrc` in the `docs/` or README (here included in research for review).
- Dependencies: Homebrew, `visual-studio-code` cask, optional `VSCodeVim` extension. For reproducibility pin the VS Code version in CI if you want to avoid silent upgrades.

## Success Criteria
- macOS CI job installs VS Code and `command -v code` returns a path.
- `platform_bridge.detect_editor()` returns `code` on macOS CI and local macOS dev machines with VS Code installed.
- `tests/test_editor_detection.py` passes in CI once the `code` install step is present.
- Vim users have an accessible sample `.vimrc` and clear README instructions to adopt the project's recommended setup.