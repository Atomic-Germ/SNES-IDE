# Deliberately failing tests to act as "red-light" indicators for macOS porting
# Place these in the main tests/ folder when ready; for now they live in research for review.

import platform
from pathlib import Path
import shutil


def test_emulator_binary_for_platform_exists():
    """Fail until CI download / platform selection logic places a native bsnes binary for macOS/Linux."""
    system = platform.system()
    if system == 'Darwin':
        mac_path = Path('libs/bsnes/mac')
        assert mac_path.exists() and any(mac_path.glob('*')), (
            'bsnes macOS binary missing - CI must download or provide a native macOS build at libs/bsnes/mac/'
        )
    elif system == 'Linux':
        linux_path = Path('libs/bsnes/linux')
        assert linux_path.exists() and any(linux_path.glob('*')), (
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
