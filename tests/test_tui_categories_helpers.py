def test_get_tools_in_category():
    """Test that get_tools_in_category returns expected tool names for a given category."""
    from snes_installer.tui import SNESInstallerTUI
    from pathlib import Path

    config_file = Path(__file__).parent / "tools_config.json"
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