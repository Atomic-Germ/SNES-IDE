import platform
import shutil


def test_preferred_editor_present_on_macos():
    """Red-light: prefer VS Code on macOS; allow terminal editor fallback.

    CI will install VS Code via Homebrew cask; this test asserts the
    `code` CLI is present or an acceptable fallback exists.
    """
    if platform.system() != 'Darwin':
        return
    assert shutil.which('code') or shutil.which('vim') or shutil.which('open'), (
        'No supported editor found on macOS runner; install VS Code CLI or ensure vim/open is present'
    )
