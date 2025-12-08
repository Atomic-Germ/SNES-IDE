from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Dict, TYPE_CHECKING

from textual.command import Hit, Hits, Provider

if TYPE_CHECKING:
    from ..app import ToolBrowser
    from ..widgets.tool_panel import ToolDetailPanel

# Category to scripts mapping
CATEGORY_SCRIPTS: Dict[str, list[Dict[str, str]]] = {
    "audio": [
        {"label": "Convert WAV to BRR", "script": "audio-wav-brr-converter.py"},
        {"label": "Convert BRR to WAV", "script": "audio-brr-wav-converter.py"},
        {"label": "Generate Audio Sample", "script": "audio-sample-generator.py"},
        {"label": "Initialize Impulse Tracker", "script": "audio-impulse-tracker-init.py"},
    ],
    "graphics": [
        {"label": "Convert PNG to SNES", "script": "gfx-png-bmp-snes-converter.py"},
        {"label": "Edit PNG/BMP", "script": "gfx-png-bmp-editor.py"},
        {"label": "Edit TMX Map", "script": "gfx-tmx-editor.py"},
        {"label": "Convert TMX to TMJ", "script": "gfx-tmx-tmj-converter.py"},
    ],
    "emulators": [
        {"label": "Open in Emulator", "script": "open-emulator.py"},
    ],
    "sdk": [
        {"label": "Create PVSnesLib Project", "script": "create-pvsneslib-proj.py"},
        {"label": "Compile PVSnesLib Project", "script": "compile-pvsneslib-proj.py"},
        {"label": "Create DotnetSnes Project", "script": "create-dotnetsnes-proj.py"},
        {"label": "Compile DotnetSnes Project", "script": "compile-dotnetsnes-proj.py"},
        {"label": "Create JavaSnes Project", "script": "create-javasnes-proj.py"},
        {"label": "Compile JavaSnes Project", "script": "compile-javasnes-proj.py"},
    ],
}


class ToolCommandProvider(Provider):
    """Provides contextual commands for the selected tool."""

    @property
    def _app(self) -> "ToolBrowser":
        return self.app  # type: ignore

    async def search(self, query: str) -> Hits:
        """Yield command hits based on current context."""
        matcher = self.matcher(query)
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"

        # Get currently selected tool
        # We need to import ToolDetailPanel here to avoid circular imports
        # But we can't import it if it doesn't exist yet.
        # For now, we'll assume it will be available.
        try:
            from ..widgets.tool_panel import ToolDetailPanel
            detail_panel = self._app.query_one(ToolDetailPanel)
            tool_data = detail_panel.tool_data
        except Exception:
            tool_data = None
            
        tool_name = tool_data.get("name", "tool") if tool_data else None
        is_installed = tool_data.get("available", False) if tool_data else False
        category = tool_data.get("category") if tool_data else None

        # === Always-available commands ===
        
        # Refresh
        command = "Refresh Tools"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_refresh, help="Reload tool list")

        # Toggle sidebar
        command = "Toggle Sidebar"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_toggle_sidebar, help="Show/hide sidebar")

        # Open project
        command = "Open Project"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_open_project, help="Open project directory")

        # Toggle files/tools view
        command = "Toggle Code/Tools View"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_toggle_files, help="Switch between code and tools view")

        # Show tools view
        command = "Show Tools"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_show_tools, help="Show tools panel")

        # Show Profiler
        command = "Show Profiler (Silicon Turtleneck)"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_show_profiler, help="Open the Cycle Profiler")

        # Show Disassembler
        command = "Show Disassembler"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_show_disassembler, help="Open the Disassembler")

        # Open in Editor (only when viewing a file)
        current_file = self._app.current_file
        if current_file:
            command = f"Open in Editor: {current_file.name}"
            score = matcher.match(command)
            if score > 0:
                yield Hit(score, command, self._app.action_open_in_editor, help="Edit file in external editor")

        # === Tool-specific commands (require a selected tool) ===
        if tool_data:
            # Install (only if not installed)
            if not is_installed:
                command = f"Install {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, self._app.action_install, help=f"Download and build {tool_name}")

            # Update (re-run install, only if installed)
            if is_installed:
                command = f"Update {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, self._app.action_update, help=f"Re-download and rebuild {tool_name}")

            # Verify (only if installed)
            if is_installed:
                command = f"Verify {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, self._app.action_verify, help=f"Check {tool_name} installation")

            # Uninstall (only if installed)
            if is_installed:
                command = f"Uninstall {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, self._app.action_uninstall, help=f"Remove {tool_name} binary and source")

            # Documentation (if docs_url exists)
            docs_url = tool_data.get("docs_url")
            if docs_url:
                command = f"Documentation: {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, lambda: webbrowser.open(docs_url), help=f"Open {tool_name} docs in browser")

            # Per-tool custom commands from tools.json
            tool_commands = tool_data.get("commands", [])
            for cmd in tool_commands:
                label = cmd.get("label", "")
                script = cmd.get("script", "")
                args = cmd.get("args", [])
                if label:
                    command = f"{tool_name}: {label}"
                    score = matcher.match(command)
                    if score > 0:
                        script_path = scripts_dir / script if script else None
                        yield Hit(
                            score, 
                            command, 
                            lambda s=script_path, a=args: self._run_script(s, a),
                            help=f"Run {script}" if script else label
                        )

            # Category-based commands
            if category and category in CATEGORY_SCRIPTS:
                for cat_cmd in CATEGORY_SCRIPTS[category]:
                    label = cat_cmd.get("label", "")
                    script = cat_cmd.get("script", "")
                    command = label
                    score = matcher.match(command)
                    if score > 0:
                        script_path = scripts_dir / script
                        yield Hit(
                            score,
                            command,
                            lambda s=script_path: self._run_script(s, []),
                            help=f"Run {script}"
                        )

    def _run_script(self, script_path: Path | None, args: list[str]) -> None:
        """Run a script with arguments."""
        if script_path and script_path.exists():
            self._app.notify(f"Running {script_path.name}...", severity="information")
            # For now, just notify - full implementation would run the script
            # subprocess.Popen([sys.executable, str(script_path)] + args)
        else:
            self._app.notify(f"Script not found: {script_path}", severity="error")
