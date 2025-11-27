from pathlib import Path
import tempfile
import os

def test_install_selected_tools_progress(monkeypatch, tmp_path):
    from snes_installer.installer import ToolInstaller
    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    installer = ToolInstaller(config_file, install_dir=tmp_path / 'inst')
    installer.install_dir.mkdir(parents=True, exist_ok=True)

    # Use a known tool from config (ca65)
    tool_name = 'ca65'
    cfg_tool = next((t for t in installer.config['tools'] if t['name'] == tool_name), None)
    assert cfg_tool is not None

    # Create dummy archive file so install_selected_tools doesn't try to download
    tool_dir = installer.install_dir / tool_name
    tool_dir.mkdir(parents=True, exist_ok=True)
    archive_path = tool_dir / Path(cfg_tool['url']).name
    archive_path.write_text('x')

    # Monkeypatch build and configure to no-ops
    monkeypatch.setattr(installer, 'build_tool', lambda t: None)
    monkeypatch.setattr(installer, 'configure_tool', lambda t: None)

    calls = []
    def cb(tool_name_arg, state, message):
        calls.append((tool_name_arg, state, message))

    installer.install_selected_tools([tool_name], progress_callback=cb)

    # Expect a 'starting' then 'success' callback
    assert any(c[1] == 'starting' for c in calls)
    assert any(c[1] == 'success' for c in calls)
