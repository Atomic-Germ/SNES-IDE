import importlib
import sys
from pathlib import Path

import pytest


def test_main_passes_install_dir_and_min_space(monkeypatch, tmp_path):
    """Ensure `main.main()` passes CLI flags to ToolInstaller (via monkeypatch)."""
    # Import main fresh
    main_mod = importlib.import_module("snes_installer.main")
    # Create a fake ToolInstaller that captures init args
    captured = {}

    class FakeInstaller:
        def __init__(
            self, config_file, dry_run=False, min_free_bytes=None, install_dir=None
        ):
            captured["config_file"] = config_file
            captured["dry_run"] = dry_run
            captured["min_free_bytes"] = min_free_bytes
            captured["install_dir"] = install_dir

        def load_config(self):
            return {"tools": []}

        def is_tool_installed(self, name):
            return False

        def install_selected_tools(self, tools):
            pass

        # For TUI codepath, ensure we have load_config and other methods
        def get_installed_tools(self):
            return []

        def get_missing_tools(self):
            return []

    # Replace the ToolInstaller in both the main module and the installer module to ensure it is used
    monkeypatch.setattr(main_mod, "ToolInstaller", FakeInstaller)
    monkeypatch.setattr("snes_installer.installer.ToolInstaller", FakeInstaller)

    # Build argv to simulate args
    tmp_dir = tmp_path / "install"
    sys_argv = [
        "snes_installer",
        "--dry-run",
        "--install-dir",
        str(tmp_dir),
        "--min-space",
        "500",
        "--tools",
        "ca65",
    ]
    monkeypatch.setattr("sys.argv", sys_argv)

    # Call main without reloading (we already monkeypatched the ToolInstaller)
    main_mod.main()

    assert captured["dry_run"] is True
    assert captured["install_dir"] == tmp_dir
    assert captured["min_free_bytes"] == 500 * 1024 * 1024
