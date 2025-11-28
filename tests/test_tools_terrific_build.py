def test_terrific_audio_driver_build_command_exists():
    """Ensure terrific_audio_driver has cargo build in tools_config.json build_commands."""
    import json
    from pathlib import Path

    config_file = (
        Path(__file__).parent.parent / "src" / "snes_installer" / "tools_config.json"
    )
    with open(config_file, "r") as f:
        config = json.load(f)
    tools = config.get("tools", [])
    tad = next((t for t in tools if t["name"] == "terrific_audio_driver"), None)
    assert tad is not None
    linux_cmds = tad.get("build_commands", {}).get("linux", [])
    assert any("cargo build" in c for c in linux_cmds) or any(
        "cargo build" in c for c in tad.get("build_commands", {}).get("darwin", [])
    )
