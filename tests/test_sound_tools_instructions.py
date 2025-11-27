def test_sound_tools_have_instructions():
    from snes_installer.tui import SNESInstallerTUI
    from pathlib import Path

    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    tui = SNESInstallerTUI(config_file)
    categorized = tui.get_tools_by_category()
    sound = categorized.get('Sound & Music', [])
    assert sound, "Sound & Music category should exist"
    for tool in sound:
        assert 'install_instructions' in tool or tool.get('url'), f"Tool {tool['name']} should have install instructions or URL"
