import os
import shutil
import subprocess
from pathlib import Path

import pytest

from snes_installer.installer import ToolInstaller


def test_copy_cargo_binary_if_exists(tmp_path):
    config_file = (
        Path(__file__).parent.parent / "src" / "snes_installer" / "tools_config.json"
    )
    installer = ToolInstaller(config_file)
    # Set a fake install dir to tmp so we don't touch real home
    installer.install_dir = tmp_path / "install"
    installer.install_dir.mkdir(parents=True)

    # Create a fake build_dir with target/release/tad-compiler
    build_dir = tmp_path / "src" / "terrific"
    cargo_bin = build_dir / "target" / "release" / "tad-compiler"
    cargo_bin.parent.mkdir(parents=True)
    cargo_bin.write_text("binary")

    installer._copy_cargo_binary_if_exists(build_dir, "tad-compiler")
    dest = installer.install_dir / "bin" / "tad-compiler"
    assert dest.exists()
    assert dest.read_text() == "binary"


def test_build_tool_runs_cargo(monkeypatch, tmp_path):
    config_file = (
        Path(__file__).parent.parent / "src" / "snes_installer" / "tools_config.json"
    )
    installer = ToolInstaller(config_file)
    installer.install_dir = tmp_path / "install"
    installer.install_dir.mkdir(parents=True)

    # Prepare a fake tool dict
    tool = {
        "name": "terrific_audio_driver",
        "url": "https://example.com/tad.tar.gz",
        "build_commands": {"linux": []},
    }

    # Monkeypatch that the archive exists and is extracted
    def fake_extract(archive_path, extract_to):
        extract_to.mkdir(parents=True, exist_ok=True)
        # Create a fake crate dir with target release
        crate_dir = extract_to / "crates" / "tad-compiler"
        (crate_dir / "target" / "release").mkdir(parents=True, exist_ok=True)
        (crate_dir / "target" / "release" / "tad-compiler").write_text("binary")

    monkeypatch.setattr(installer, "extract_archive", fake_extract)

    # Monkeypatch shutil.which to pretend cargo exists
    import shutil as _shutil

    monkeypatch.setattr(
        _shutil, "which", lambda name: "/usr/bin/cargo" if name == "cargo" else None
    )

    # Monkeypatch subprocess.run to ensure it gets called with cargo
    def fake_run(cmd, cwd, shell, check):
        assert "cargo build" in cmd
        return None

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Create a fake archive file so build_tool doesn't throw FileNotFoundError
    tool_dir = installer.install_dir / tool["name"]
    tool_dir.mkdir(parents=True, exist_ok=True)
    archive_path = tool_dir / "tad.tar.gz"
    archive_path.write_text("x")

    # Run build_tool - it should run cargo build (fake_run asserts)
    installer.build_tool(tool)


def test_build_tool_space_check(monkeypatch, tmp_path):
    """If disk is low, build_tool should raise OSError via ensure_enough_space."""
    config_file = (
        Path(__file__).parent.parent / "src" / "snes_installer" / "tools_config.json"
    )
    installer = ToolInstaller(config_file)
    installer.install_dir = tmp_path / "install"
    installer.install_dir.mkdir(parents=True)

    def fake_extract(archive_path, extract_to):
        extract_to.mkdir(parents=True, exist_ok=True)
        (extract_to / "dummy").mkdir()

    monkeypatch.setattr(installer, "extract_archive", fake_extract)

    # Ensure ensure_enough_space will raise when called
    def fake_space_check(path, min_bytes=None):
        import errno

        raise OSError(errno.ENOSPC, "No space")

    monkeypatch.setattr(installer, "ensure_enough_space", fake_space_check)

    tool = {
        "name": "some_tool",
        "url": "https://example.com/some_tool.tar.gz",
        "build_commands": {"linux": ["echo build"]},
    }

    # Create dummy archive path
    tool_dir = installer.install_dir / tool["name"]
    tool_dir.mkdir(parents=True, exist_ok=True)
    archive_path = tool_dir / "some_tool.tar.gz"
    archive_path.write_text("x")

    try:
        installer.build_tool(tool)
        assert False, "Expected OSError due to low disk during build"
    except OSError:
        assert True
