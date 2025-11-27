def test_sound_music_category_and_tools():
    """Verify Sound & Music category exists and contains expected tools."""
    from snes_installer.tui import SNESInstallerTUI
    from pathlib import Path

    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    tui = SNESInstallerTUI(config_file)

    categorized = tui.get_tools_by_category()
    assert "Sound & Music" in categorized

    sound_tools = [t['name'] for t in categorized['Sound & Music']]
    expected = ["snes_gss", "furnace", "terrific_audio_driver"]
    for name in expected:
        assert name in sound_tools
