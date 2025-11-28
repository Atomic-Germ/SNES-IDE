def test_get_tools_by_category():
    """Test that tools are correctly grouped by category."""
    from pathlib import Path

    from snes_installer.tui import SNESInstallerTUI

    config_file = (
        Path(__file__).parent.parent / "src" / "snes_installer" / "tools_config.json"
    )
    tui = SNESInstallerTUI(config_file)

    categorized = tui.get_tools_by_category()

    # Check that we have the expected categories
    assert "Compilers" in categorized
    assert "Debugging Tools" in categorized
    assert "Utilities" in categorized

    # Check that compilers category has expected tools
    compilers = [tool["name"] for tool in categorized["Compilers"]]
    from tests.common_tools import COMPILER_TOOLS

    for compiler in COMPILER_TOOLS:
        assert compiler in compilers

    # Check that debugging tools has bsnes
    debug_tools = [tool["name"] for tool in categorized["Debugging Tools"]]
    assert "bsnes" in debug_tools
    assert "no$snes" in debug_tools

    # Check utilities
    utilities = [tool["name"] for tool in categorized["Utilities"]]
    assert "ucon64" in utilities
