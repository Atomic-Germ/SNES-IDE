"""Textual-based TUI for SNES Installer.

This module provides a modern keyboard-driven terminal UI using Textual.
It is invoked from `snes_installer.tui.SNESInstallerTUI.run()` when Textual
is available and the process is attached to a real TTY.
"""

from __future__ import annotations

import asyncio
import io
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)


class SNESInstallerTextualApp(App):
    css_path = "tui_textual.css"
    # reactive fields must be declared at class level for Textual to track them
    current_category = reactive("")

    BINDINGS = [
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Previous"),
        ("escape", "go_back", "Back"),
        ("backspace", "go_back", "Back"),
        ("ctrl+d", "quit_graceful", "Quit"),
        ("s", "open_settings", "Settings"),
        ("i", "do_install", "Install"),
    ]

    def __init__(self, tui_instance, **kwargs: Any):
        super().__init__(**kwargs)
        self.tui = tui_instance
        self.tools_config = tui_instance.tools_config
        self.installer = tui_instance.installer
        self.categories = list(self.tui.get_tools_by_category().keys())
        # set the reactive value (reactive descriptor declared at class level)
        self.current_category = self.categories[0] if self.categories else ""
        self.selected_tools: Set[str] = set()
        self.failed_tools: Set[str] = set()
        # highlight index per category
        self.highlight_index: Dict[str, int] = {cat: 0 for cat in self.categories}
        self.ctrl_c_count = 0
        self.errors: List[str] = []
        # progress/log UI state
        self.log_lines: List[str] = []
        self.progress_total: int = 0
        self.progress_done: int = 0
        # current stop event for canceling installs
        self._stop_event: threading.Event | None = None
        self.installing = False

    async def show_error_dialog(self, title: str, short: str, details: str) -> str:
        """Show a blocking error dialog with Skip / Cancel / Details buttons.

        Returns one of: 'skip', 'cancel'. The Details button will toggle showing
        the full details and will write a short error file `./error.log`.
        """
        # create a future that will be set by the screen when user picks Skip/Cancel
        loop = self.loop
        fut = loop.create_future()

        class ErrorScreen(Screen):
            def __init__(self, fut, title, short, details):
                super().__init__()
                self.fut = fut
                self.title_text = title
                self.short = short
                self.details = details
                self.showing_details = False

            def compose(self) -> ComposeResult:
                yield Header(show_clock=False)
                yield Static(self.title_text, id="err_title")
                self.msg = Static(self.short, id="err_msg")
                yield self.msg
                with Horizontal(classes="err_buttons"):
                    self.skip_btn = Button("Skip", id="err_skip")
                    self.details_btn = Button("Details", id="err_details")
                    self.cancel_btn = Button("Cancel", id="err_cancel")
                    yield self.skip_btn
                    yield self.details_btn
                    yield self.cancel_btn

            async def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "err_skip":
                    if not self.fut.done():
                        self.fut.set_result("skip")
                    await self.app.pop_screen()
                elif event.button.id == "err_cancel":
                    if not self.fut.done():
                        self.fut.set_result("cancel")
                    await self.app.pop_screen()
                elif event.button.id == "err_details":
                    # write a short error file to cwd and toggle the message
                    try:
                        with open("error.log", "w") as fh:
                            fh.write(self.details)
                    except Exception:
                        pass
                    if not self.showing_details:
                        self.msg.update(self.details)
                        self.showing_details = True
                    else:
                        self.msg.update(self.short)
                        self.showing_details = False

        screen = ErrorScreen(fut, title, short, details)
        await self.push_screen(screen)
        # wait for user choice
        res = await fut
        return res

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
            self.cancel_btn = Button("CANCEL", id="cancel", disabled=True)
            self.settings_btn = Button("SETTINGS", id="settings")
            self.quit_btn = Button("QUIT", id="quit")
            yield self.install_btn
            yield self.cancel_btn
            yield self.settings_btn
            yield self.quit_btn
        # progress bar and log area (above status bar)
        self.progress_bar = Static("", id="progress_bar")
        yield self.progress_bar
        self.log_box = Static("", id="log_box")
        yield self.log_box
        # status bar for debug/UX information
        self.status_bar = Static("", id="status_bar")
        yield self.status_bar
        yield Footer()

    def on_mount(self) -> None:
        # populate categories
        for i, cat in enumerate(self.categories):
            # give each category list item a stable id (no spaces)
            self.cat_list.append(ListItem(Static(cat), id=f"cat_{i}"))
        # select first
        if self.categories:
            self.cat_list.index = 0
            self.current_category = self.categories[0]
        # set initial focus to categories for predictable tab order
        try:
            self.set_focus(self.cat_list)
        except Exception:
            pass
        self.refresh_tools()
        # ensure status bar displays initial info right away
        try:
            self._update_status_bar()
        except Exception:
            pass
        self.set_interval(0.5, self._reset_ctrl_c)
        # update a status bar regularly for debugging
        self.set_interval(0.25, self._update_status_bar)

        # ensure progress/log start empty
        try:
            self.progress_bar.update("")
            self.log_box.update("")
        except Exception:
            pass

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
            if name in self.failed_tools:
                marker = "[!]"
            else:
                marker = "[x]" if installed or name in self.selected_tools else "[ ]"
            # Use a one-line short description in the list to avoid multi-line ListItem heights
            raw_desc = t.get("description", "") or ""
            first_line = raw_desc.splitlines()[0] if raw_desc else ""
            short = first_line.strip()
            if len(short) > 80:
                short = short[:77] + "..."
            label = f"{marker} {name} - {short}"
            # sanitize id for ListItem (Textual ids should avoid spaces/special chars)
            safe_name = re.sub(r"[^0-9a-zA-Z_-]", "_", name)
            self.tools_list.append(ListItem(Static(label), id=f"tool_{safe_name}"))
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
        installed = (
            self.tui.is_tool_installed(t["name"]) or t["name"] in self.selected_tools
        )
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
        # Let ListView handle up/down when it is focused to avoid double-moves
        focused_id = getattr(self.focused, "id", None)
        if event.key == "up":
            if focused_id not in ("cat_list", "tools_list"):
                await self._focus_move(-1)
                event.stop()
            return
        if event.key == "down":
            if focused_id not in ("cat_list", "tools_list"):
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
            # custom focus order to ensure Categories -> Tools -> Buttons
            try:
                self.action_focus_next()
            except Exception:
                pass
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
        # quick keys
        if event.key == "s":
            # open settings
            await self.action_open_settings()
            event.stop()
            return
        if event.key == "i":
            await self.action_do_install()
            event.stop()
            return

    async def _focus_move(self, delta: int) -> None:
        # Move selection up/down in focused list
        if not self.focused:
            return
        fv = getattr(self.focused, "id", None)
        if fv == "cat_list":
            # move category selection and refresh tools immediately
            idx = (self.cat_list.index or 0) + delta
            if idx < 0:
                idx = 0
            if idx >= len(self.categories):
                idx = len(self.categories) - 1
            self.cat_list.index = idx
            # update current category and refresh tools
            self.current_category = self.categories[idx]
            self.refresh_tools()
        elif fv == "tools_list":
            total = len(self.tui.get_tools_in_category(self.current_category))
            idx = (self.tools_list.index or 0) + delta
            if idx < 0:
                idx = 0
            if idx >= total:
                idx = total - 1
            self.tools_list.index = idx
            # update highlight index and detail box
            self.highlight_index[self.current_category] = idx
            self.update_detail()

    def action_focus_next(self) -> None:
        """Override focus next to enforce desired traversal order."""
        focus_order = [
            getattr(self, "cat_list", None),
            getattr(self, "tools_list", None),
            getattr(self, "install_btn", None),
            getattr(self, "cancel_btn", None),
            getattr(self, "settings_btn", None),
            getattr(self, "quit_btn", None),
            getattr(self, "progress_bar", None),
            getattr(self, "log_box", None),
            getattr(self, "status_bar", None),
        ]
        # filter out None and non-focusable
        nodes = [
            n for n in focus_order if n is not None and getattr(n, "can_focus", True)
        ]
        if not nodes:
            return
        cur = getattr(self.focused, "id", None)
        # find index of current focused widget in our order
        cur_idx = 0
        for i, node in enumerate(nodes):
            if getattr(node, "id", None) == cur:
                cur_idx = i
                break
        next_idx = (cur_idx + 1) % len(nodes)
        try:
            self.set_focus(nodes[next_idx])
        except Exception:
            pass

    def action_focus_previous(self) -> None:
        """Reverse traversal for shift+tab."""
        focus_order = [
            getattr(self, "cat_list", None),
            getattr(self, "tools_list", None),
            getattr(self, "install_btn", None),
            getattr(self, "cancel_btn", None),
            getattr(self, "settings_btn", None),
            getattr(self, "quit_btn", None),
            getattr(self, "progress_bar", None),
            getattr(self, "log_box", None),
            getattr(self, "status_bar", None),
        ]
        nodes = [
            n for n in focus_order if n is not None and getattr(n, "can_focus", True)
        ]
        if not nodes:
            return
        cur = getattr(self.focused, "id", None)
        cur_idx = 0
        for i, node in enumerate(nodes):
            if getattr(node, "id", None) == cur:
                cur_idx = i
                break
        prev_idx = (cur_idx - 1) % len(nodes)
        try:
            self.set_focus(nodes[prev_idx])
        except Exception:
            pass

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

    async def action_open_settings(self) -> None:
        """Action invoked by key binding to open settings."""
        try:
            res = await self.show_settings_dialog()
            if res == "saved":
                self.detail_box.update("[green]Settings saved.[/green]")
            else:
                self.detail_box.update("Settings unchanged.")
        except Exception:
            pass

    async def action_do_install(self) -> None:
        """Action invoked by key binding to start install."""
        await self._do_install()

    def _update_status_bar(self) -> None:
        """Update a small status bar with debug information."""
        focused_id = getattr(self.focused, "id", None)
        sel_count = len(self.selected_tools)
        fail_count = len(self.failed_tools)
        cat = self.current_category or "(none)"
        status = f"Focus:{focused_id} | Cat:{cat} | Selected:{sel_count} Failed:{fail_count} | ctrl_c:{self.ctrl_c_count}"
        try:
            self.status_bar.update(status)
        except Exception:
            pass

    def _render_progress(self, percent: int) -> str:
        # simple textual progress bar
        width = 40
        filled = int((percent * width) / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {percent}%"

    def _update_progress_ui(self, percent: int) -> None:
        try:
            self.progress_bar.update(self._render_progress(percent))
        except Exception:
            pass

    def _update_log_ui(self) -> None:
        try:
            # show last 200 lines
            content = "\n".join(self.log_lines[-200:])
            self.log_box.update(content)
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "install":
            await self._do_install()
        elif event.button.id == "cancel":
            # user requested cancellation
            try:
                if self._stop_event:
                    self._stop_event.set()
                    self.detail_box.update("Cancellation requested...")
            except Exception:
                pass
        elif event.button.id == "quit":
            await self.action_quit()
        elif event.button.id == "settings":
            # Show settings dialog
            res = await self.show_settings_dialog()
            if res == "saved":
                self.detail_box.update("[green]Settings saved.[/green]")
            else:
                self.detail_box.update("Settings unchanged.")

    async def show_settings_dialog(self) -> str:
        """Show a modal settings dialog to edit install directory and min free MB.

        Returns 'saved' or 'cancel'.
        """
        loop = self.loop
        fut = loop.create_future()

        class SettingsScreen(Screen):
            def __init__(self, fut, parent_app: "SNESInstallerTextualApp"):
                super().__init__()
                self.fut = fut
                self.parent_app = parent_app

            def compose(self) -> ComposeResult:
                yield Header(show_clock=False)
                yield Static("Settings", id="settings_title")
                # current values
                cur_dir = str(self.parent_app.installer.install_dir)
                cur_space = str(
                    self.parent_app.installer.min_free_bytes // (1024 * 1024)
                )
                yield Label("Install directory:")
                self.dir_input = Input(value=cur_dir, id="dir_input")
                yield self.dir_input
                yield Label("Minimum free space (MB):")
                self.space_input = Input(value=cur_space, id="space_input")
                yield self.space_input
                self.err = Static("", id="settings_err")
                yield self.err
                with Horizontal(classes="settings_buttons"):
                    self.save_btn = Button("Save", id="save_settings")
                    self.cancel_btn = Button("Cancel", id="cancel_settings")
                    yield self.save_btn
                    yield self.cancel_btn

            async def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "save_settings":
                    dirv = self.dir_input.value.strip()
                    spacev = self.space_input.value.strip()
                    # try to parse space
                    try:
                        sb = int(spacev)
                    except Exception:
                        sb = None
                        self.err.update("Minimum free space must be an integer")
                        return
                    # apply
                    try:
                        if dirv:
                            p = Path(dirv)
                            if not p.exists():
                                try:
                                    p.mkdir(parents=True, exist_ok=True)
                                except Exception as e:
                                    self.err.update(f"Could not create directory: {e}")
                                    return
                            self.parent_app.installer.install_dir = p
                        if sb is not None:
                            self.parent_app.installer.min_free_bytes = (
                                int(sb) * 1024 * 1024
                            )
                        # persist
                        try:
                            self.parent_app.tui.save_user_settings()
                        except Exception:
                            pass
                        if not self.fut.done():
                            self.fut.set_result("saved")
                    except Exception:
                        if not self.fut.done():
                            self.fut.set_result("cancel")
                    await self.app.pop_screen()
                elif event.button.id == "cancel_settings":
                    if not self.fut.done():
                        self.fut.set_result("cancel")
                    await self.app.pop_screen()

        screen = SettingsScreen(fut, self)
        await self.push_screen(screen)
        res = await fut
        return res

    async def _do_install(self) -> None:
        # collect selected tools from all categories if none selected in current, install them
        if not self.selected_tools:
            # fallback: install all missing
            self.selected_tools = set(self.tui.get_missing_tools())
        tools = list(self.selected_tools)
        if not tools:
            self.detail_box.update("No tools selected to install")
            return

        total = len(tools)
        self.progress_total = total
        self.progress_done = 0
        self.log_lines = []
        # refresh initial UI
        self._update_progress_ui(0)
        self._update_log_ui()

        stop_event = threading.Event()

        # expose stop_event so cancel button can set it
        self._stop_event = stop_event
        self.installing = True
        try:
            self.install_btn.disabled = True
            self.cancel_btn.disabled = False
        except Exception:
            pass

        def progress_cb(tool_name: str, kind: str, message: Optional[str]) -> None:
            # This callback may be called from a worker thread. Use call_from_thread
            def _handle() -> None:
                try:
                    if kind == "starting":
                        self.detail_box.update(f"Starting {tool_name}...")
                    elif kind == "log" and message is not None:
                        self.log_lines.append(message)
                    elif kind == "success":
                        self.progress_done += 1
                    elif kind in ("failed", "cancelled"):
                        self.progress_done += 1
                        if message:
                            self.errors.append(f"{tool_name}: {message}")
                        self.failed_tools.add(tool_name)
                    # update percent based on completed tools
                    percent = int((self.progress_done / total) * 100)
                    self._update_progress_ui(percent)
                    self._update_log_ui()
                    # refresh the tools list occasionally
                    self.refresh_tools()
                except Exception:
                    pass

            try:
                # schedule UI update on the main thread
                self.call_from_thread(_handle)
            except Exception:
                # fallback: try asyncio scheduling
                try:
                    asyncio.get_event_loop().call_soon_threadsafe(_handle)
                except Exception:
                    pass

        # run installer in background; rely on installer's progress_callback
        self._stop_event = stop_event
        self.installing = True
        try:
            try:
                self.install_btn.disabled = True
                self.cancel_btn.disabled = False
            except Exception:
                pass

            try:
                await asyncio.to_thread(
                    self.installer.install_selected_tools,
                    tools,
                    progress_cb,
                    stop_event,
                )
            except Exception as exc:  # noqa: BLE001
                # show blocking dialog for errors that stop the entire run
                msg = f"Installation error: {exc}"
                self.errors.append(msg)
                choice = await self.show_error_dialog("Install Error", msg, str(exc))
                if choice == "cancel":
                    self.detail_box.update("Installation cancelled")
        finally:
            # cleanup and restore UI state
            self._stop_event = None
            self.installing = False
            try:
                self.install_btn.disabled = False
                self.cancel_btn.disabled = True
            except Exception:
                pass

        # finalize progress
        self.progress_done = total
        self._update_progress_ui(100)
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
        # set_focus is synchronous
        self.set_focus(self.cat_list)

    async def action_quit_graceful(self) -> None:
        # Print goodbye and exit
        self.console.print("Goodbye!")
        await self.action_quit()


def run_textual_tui(tui_instance) -> None:
    """Helper to run the textual app given an existing SNESInstallerTUI instance."""
    app = SNESInstallerTextualApp(tui_instance)
    app.run()
