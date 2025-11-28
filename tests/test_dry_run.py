from pathlib import Path

from snes_installer.installer import ToolInstaller


def test_dry_run_skips_download_build_configuration(monkeypatch, tmp_path, caplog):
    config_file = (
        Path(__file__).parent.parent / "src" / "snes_installer" / "tools_config.json"
    )
    # Instantiate with dry_run True
    installer = ToolInstaller(config_file, dry_run=True)

    # Monkeypatch download_file, build_tool, and configure_tool to assert not called
    def fail_if_called(*args, **kwargs):
        raise AssertionError("download/build/config should not be called in dry run")

    monkeypatch.setattr(installer, "download_file", fail_if_called)
    monkeypatch.setattr(installer, "build_tool", fail_if_called)
    monkeypatch.setattr(installer, "configure_tool", fail_if_called)

    # Also ensure we skip disk space checks in dry-run mode
    def fail_space_check(path, min_bytes=None):
        raise AssertionError("ensure_enough_space should not be called in dry run")

    monkeypatch.setattr(installer, "ensure_enough_space", fail_space_check)

    # Should not raise
    installer.install_selected_tools(["ca65"])
    assert True
