# Red-light tests: intentionally fail until macOS platform artifacts are provided by CI
# These tests define the acceptance criteria for the macOS porting TCC.

from pathlib import Path
import platform
import shutil


def test_emulator_binary_for_platform_exists():
    """Fail until CI download / platform selection logic places a native bsnes binary for macOS/Linux."""
    system = platform.system()
    if system == 'Darwin':
        mac_path = Path('libs/bsnes/mac')
        assert mac_path.exists() and any(mac_path.iterdir()), (
            'bsnes macOS binary missing - CI must download or provide a native macOS build at libs/bsnes/mac/'
        )
    elif system == 'Linux':
        linux_path = Path('libs/bsnes/linux')
        assert linux_path.exists() and any(linux_path.iterdir()), (
            'bsnes linux binary missing - CI must download or provide a native Linux build at libs/bsnes/linux/'
        )
    else:
        # Windows: original shipped binary should exist
        assert Path('libs/bsnes/bsnes.exe').exists(), 'Windows bsnes binary missing'


def test_editor_detection_on_macos():
    """Fail on macOS until editor-detection / installation policies are provided in CI."""
    if platform.system() != 'Darwin':
        return
    ok = bool(shutil.which('code') or shutil.which('subl') or shutil.which('mate') or shutil.which('open'))
    assert ok, 'No known editor detected on macOS; CI must provide a fallback (e.g., install VS Code CLI or document use of TextEdit)'
