# Editor setup for SNES-IDE

This project prefers Visual Studio Code on macOS and Linux for developer workflows. The `platform_bridge.detect_editor()` helper prefers `code` (VS Code CLI) on POSIX systems and falls back to other editors.

## VS Code (recommended)

- On macOS CI we will install VS Code via Homebrew cask so `code` is available to the test suite and to the IDE when launching an editor.

  Install locally on macOS:

  1. Download and install Visual Studio Code from https://code.visualstudio.com/
  2. Open VS Code and run the Command Palette (⇧⌘P) -> "Shell Command: Install 'code' command in PATH" to add the `code` CLI to your shell.

  Or install via Homebrew:

  ```bash
  brew install --cask visual-studio-code
  ```

- Once installed, open the project from the terminal:

  ```bash
  code .
  ```

- Recommended VS Code extensions:
  - vscodevim.vim (if you like Vim keybindings)
  - EditorConfig, Python, and language-specific extensions you normally use.

## Vim users

A minimal example `vimrc` for the project is available at `docs/vimrc_example.vim`. We recommend using your own preferred Vim runtime or `amix/vimrc` as a starting point. If you use VS Code and want Vim bindings, install the VSCodeVim extension.

## CI behavior

- The macOS CI job installs the `visual-studio-code` cask and ensures `code --version` prints the version. This allows `platform_bridge.detect_editor()` to find `code` and the test `tests/test_editor_detection.py` to pass.

## Fallbacks

- If `code` is not available, the project falls back to `subl`, `mate`, `open` (macOS), and finally to terminal editors (`vim`/`nano`).
