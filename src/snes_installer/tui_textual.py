"""Textual-based TUI for SNES Installer.

This module provides a modern keyboard-driven terminal UI using Textual.
It is invoked from `snes_installer.tui.SNESInstallerTUI.run()` when Textual
is available and the process is attached to a real TTY.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, ListView, ListItem, Button
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual import events


class SNESInstallerTextualApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    # simple layout: header, body, footer
    .body {
        height: 1fr;
    }
    .left {
        width: 25%;
        padding: 1 1;
    }
    .center {
        padding: 1 1;
        width: 75%;
    }
    .details {
        height: 20%;
        padding: 1 1;
    }
    .buttons {
        height: 3;
        padding: 1 1;
    }
    """

    BINDINGS = [
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Previous"),
        ("escape", "go_back", "Back"),
        ("backspace", "go_back", "Back"),
        ("ctrl+d", "quit_graceful", "Quit"),
    ]

    def __init__(self, tui_instance, **kwargs: Any):
        super().__init__(**kwargs)
        self.tui = tui_instance
        self.tools_config = tui_instance.tools_config
        self.installer = tui_instance.installer
        self.categories = list(self.tui.get_tools_by_category().keys())
        self.current_category = reactive(self.categories[0] if self.categories else "")
        self.selected_tools: Set[str] = set()
        # highlight index per category
        self.highlight_index: Dict[str, int] = {cat: 0 for cat in self.categories}
        self.ctrl_c_count = 0
        self.errors: List[str] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(classes="body"):
            with Vertical(classes="left"):
                yield Static("Categories", id="cat_title")
                self.cat_list = ListView(id="cat_list")
                yield self.cat_list
            with Vertical(classes="center"):
                yield Static("Tools", id="tools_title")
                self.tools_list = ListView(id="tools_list")
                yield self.tools_list
                self.detail_box = Static("", id="detail_box", classes="details")
                yield self.detail_box
        with Horizontal(classes="buttons"):
            self.install_btn = Button("INSTALL", id="install")
            self.settings_btn = Button("SETTINGS", id="settings")
            self.quit_btn = Button("QUIT", id="quit")
            yield self.install_btn
            yield self.settings_btn
            yield self.quit_btn
        yield Footer()

    def on_mount(self) -> None:
        # populate categories
        for cat in self.categories:
            self.cat_list.append(ListItem(Static(cat)))
        # select first
        if self.categories:
            self.cat_list.index = 0
            self.current_category = self.categories[0]
        self.refresh_tools()
        self.set_interval(0.5, self._reset_ctrl_c)

    def _reset_ctrl_c(self) -> None:
        # reset ctrl+c counter slowly
        if self.ctrl_c_count > 0:
            self.ctrl_c_count = 0

    def refresh_tools(self) -> None:
        # Populate tools_list for current category
        self.tools_list.clear()
        tools = self.tui.get_tools_in_category(self.current_category)
        for t in tools:
            name = t["name"]
            installed = self.tui.is_tool_installed(name)
            marker = "[x]" if installed or name in self.selected_tools else "[ ]"
            label = f"{marker} {name} - {t.get('description','') }"
            self.tools_list.append(ListItem(Static(label)))
        # set index to previous highlight if available
        idx = self.highlight_index.get(self.current_category, 0)
        try:
            self.tools_list.index = idx
        except Exception:
            self.tools_list.index = 0
        self.update_detail()

    def update_detail(self) -> None:
        tools = self.tui.get_tools_in_category(self.current_category)
        if not tools:
            self.detail_box.update("No tools in this category")
            return
        idx = self.tools_list.index or 0
        if idx < 0 or idx >= len(tools):
            idx = 0
        t = tools[idx]
        desc = t.get("description", "No description")
        url = t.get("url", "N/A")
        build_cmds = t.get("build_commands", "(no build commands)")
        installed = self.tui.is_tool_installed(t["name"]) or t["name"] in self.selected_tools
        installed_status = "Installed" if installed else "Not installed"
        content = f"Name: {t['name']}\nStatus: {installed_status}\nURL: {url}\n\n{desc}\n\nBuild: {build_cmds}"
        self.detail_box.update(content)

    async def on_list_view_selected(self, message: ListView.Selected) -> None:
        # handle selection change in either list
        if message.list_view.id == "cat_list":
            idx = message.index
            if idx is None:
                return
            self.current_category = self.categories[idx]
            self.refresh_tools()
        elif message.list_view.id == "tools_list":
            # update highlight index
            self.highlight_index[self.current_category] = message.index or 0
            self.update_detail()

    async def on_key(self, event: events.Key) -> None:  # noqa: D401 - textual handler
        # navigation and selection handlers
        if event.key == "up":
            # default: move up in focused list
            await self._focus_move(-1)
            event.stop()
            return
        if event.key == "down":
            await self._focus_move(1)
            event.stop()
            return
        if event.key in ("enter", "space"):
            # toggle selection if focus is tools_list
            if self.focused and getattr(self.focused, "id", None) == "tools_list":
                await self._toggle_current_tool()
                event.stop()
                return
        if event.key == "tab":
            await self.action_focus_next()
            event.stop()
            return
        if event.key == "escape" or event.key == "backspace":
            await self.action_go_back()
            event.stop()
            return
        if event.key == "ctrl+c":
            self.ctrl_c_count += 1
            if self.ctrl_c_count >= 2:
                await self.action_quit()
            event.stop()
            return
        if event.key == "ctrl+d":
            await self.action_quit_graceful()
            event.stop()
            return

    async def _focus_move(self, delta: int) -> None:
        # Move selection up/down in focused list
        if not self.focused:
            return
        fv = getattr(self.focused, "id", None)
        if fv == "cat_list":
            self.cat_list.index = (self.cat_list.index or 0) + delta
            # clamp
            if self.cat_list.index is None:
                self.cat_list.index = 0
            if self.cat_list.index < 0:
                self.cat_list.index = 0
            if self.cat_list.index >= len(self.categories):
                self.cat_list.index = len(self.categories) - 1
            # cause selection event to refresh tools
            await self.cat_list.emit_selected()
        elif fv == "tools_list":
            total = len(self.tui.get_tools_in_category(self.current_category))
            idx = (self.tools_list.index or 0) + delta
            if idx < 0:
                idx = 0
            if idx >= total:
                idx = total - 1
            self.tools_list.index = idx
            await self.tools_list.emit_selected()

    async def _toggle_current_tool(self) -> None:
        tools = self.tui.get_tools_in_category(self.current_category)
        if not tools:
            return
        idx = self.tools_list.index or 0
        name = tools[idx]["name"]
        if name in self.selected_tools:
            self.selected_tools.remove(name)
        else:
            self.selected_tools.add(name)
        # if tool is installed, leave it selected visually
        self.refresh_tools()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "install":
            await self._do_install()
        elif event.button.id == "quit":
            await self.action_quit()
        elif event.button.id == "settings":
            # For now, show a simple message
            await self.push_screen(Static("Settings not implemented yet"))

    async def _do_install(self) -> None:
        # collect selected tools from all categories if none selected in current, install them
        if not self.selected_tools:
            # fallback: install all missing
            self.selected_tools = set(self.tui.get_missing_tools())
        tools = list(self.selected_tools)
        # run installer in blocking fashion — we will update the detail box with progress
        for i, t in enumerate(tools, 1):
            try:
                self.detail_box.update(f"Installing {t} ({i}/{len(tools)})...")
                # call the underlying installer (this may perform I/O)
                self.installer.install_selected_tools([t])
                # reflect installation state
                # note: installer may have already installed binaries; we'll refresh
                self.refresh_tools()
            except Exception as exc:  # noqa: BLE001 - bubble up for dialog
                # record error and show blocking dialog
                msg = f"Failed to install {t}: {exc}"
                self.errors.append(msg)
                # show a simple blocking dialog with Skip / Cancel / Details
                # For simplicity, print to detail box and continue
                self.detail_box.update(msg)
                # In a more complete implementation we'd present a modal with buttons
                # For now, allow user to decide via keys; record error and continue
        # write errors to ~/.snes_installer/error.log at end
        if self.errors:
            cfg_dir = Path.home() / ".snes_installer"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            logp = cfg_dir / "error.log"
            with open(logp, "w") as f:
                for e in self.errors:
                    f.write(e + "\n")
        # show complete
        self.detail_box.update("Installation complete")

    async def action_go_back(self) -> None:
        # A simple back action: focus categories
        await self.set_focus(self.cat_list)

    async def action_quit_graceful(self) -> None:
        # Print goodbye and exit
        self.console.print("Goodbye!")
        await self.action_quit()


def run_textual_tui(tui_instance) -> None:
    """Helper to run the textual app given an existing SNESInstallerTUI instance."""
    app = SNESInstallerTextualApp(tui_instance)
    app.run()
