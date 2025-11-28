import os
import shutil
from pathlib import Path

from snes_installer.installer import ToolInstaller


def test_ensure_enough_space_raises(monkeypatch, tmp_path):
    config_file = (
        Path(__file__).parent.parent / "src" / "snes_installer" / "tools_config.json"
    )
    installer = ToolInstaller(config_file)

    # Monkeypatch disk_usage to return a very small free space
    class Usage:
        total = 100
        used = 99
        free = 1

    monkeypatch.setattr(shutil, "disk_usage", lambda p: Usage)

    try:
        installer.ensure_enough_space(tmp_path, min_bytes=1024)
        assert False, "Expected OSError due to insufficient space"
    except OSError as e:
        assert e.errno == os.errno.ENOSPC if hasattr(os, "errno") else e.errno == 28
