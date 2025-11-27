from pathlib import Path
import json
from snes_installer.tui import SNESInstallerTUI


def test_settings_persistence(monkeypatch, tmp_path):
    # Force user home to temp dir so we don't write real home
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    tui = SNESInstallerTUI(config_file, install_dir=tmp_path / 'snes_tools', min_free_bytes=300 * 1024 * 1024, dry_run=True)
    # Save settings
    tui.save_user_settings()
    # Create a new TUI to load settings
    tui2 = SNESInstallerTUI(config_file, install_dir=None, min_free_bytes=None, dry_run=True)
    assert str(tui2.installer.install_dir) == str(tmp_path / 'snes_tools')
    assert tui2.installer.min_free_bytes == 300 * 1024 * 1024
