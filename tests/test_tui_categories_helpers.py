def test_get_tools_in_category():
    """Test that get_tools_in_category returns expected tool names for a given category."""
    from snes_installer.tui import SNESInstallerTUI
    from pathlib import Path

    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    tui = SNESInstallerTUI(config_file)

    compilers = tui.get_tools_in_category("Compilers")
    compiler_names = [t["name"] for t in compilers]

    expected = ["ca65", "asar", "xkas", "64tass", "wla-dx", "libsfx", "pvsneslib", "superfamiconv"]
    for name in expected:
        assert name in compiler_names

    debugging = tui.get_tools_in_category("Debugging Tools")
    debug_names = [t["name"] for t in debugging]
    assert "bsnes" in debug_names
    assert "no$snes" in debug_names

    utils = tui.get_tools_in_category("Utilities")
    util_names = [t["name"] for t in utils]
    assert "ucon64" in util_names


def test_generate_preview_info_contains_cargo(monkeypatch):
    from pathlib import Path
    from snes_installer.tui import SNESInstallerTUI
    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    tui = SNESInstallerTUI(config_file, dry_run=True)
    preview = tui.generate_preview_info(['terrific_audio_driver'])
    assert preview and preview[0]['name'] == 'terrific_audio_driver'
    assert preview[0]['requires_cargo'] is True


def test_install_missing_preview(monkeypatch, tmp_path):
    from pathlib import Path
    from snes_installer.tui import SNESInstallerTUI
    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    tui = SNESInstallerTUI(config_file, dry_run=True)
    # Monkeypatch show_preview_panel to capture input
    called = {}
    def fake_preview(names):
        called['names'] = names
        return False
    monkeypatch.setattr(tui, 'show_preview_panel', fake_preview)
    # Run install_missing_tools - with dry_run True it should call preview but not install
    tui.install_missing_tools()
    assert 'names' in called