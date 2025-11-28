"""Simple Tk GUI wrapper for the SNES Installer.

This is intentionally minimal: it demonstrates a GUI with tool checkboxes, preview, and install.
It uses the same ToolInstaller API and honors dry_run/install_dir/min_space options.
"""

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from snes_installer.installer import ToolInstaller


class SNESTkGui:
    def __init__(
        self,
        config_file: Path,
        install_dir: Path | None = None,
        min_space: int | None = None,
        dry_run: bool = False,
        create_root: bool = True,
    ):
        self.config_file = config_file
        self.install_dir = install_dir
        self.min_space = min_space
        self.dry_run = dry_run
        self.installer = ToolInstaller(
            config_file,
            dry_run=dry_run,
            min_free_bytes=(min_space or 200 * 1024 * 1024),
            install_dir=install_dir,
        )
        self.tools = self.installer.load_config().get("tools", [])

        self.root = None
        self.frame = None
        self.create_root = create_root
        # tool_vars may hold real tk.IntVar instances (GUI) or DummyVar (headless/tests)
        self.tool_vars: Dict[str, object] = {}
        self.tool_status_labels: Dict[str, tk.Label] = {}
        self._log_lines = []
        # spinner state for activity indicators {tool_name: after_id}
        self._spinner_jobs: Dict[str, Optional[str]] = {}
        self._spinner_index: Dict[str, int] = {}
        if create_root:
            self.root = tk.Tk()
            self.root.title("SNES Installer GUI")
            self.frame = ttk.Frame(self.root, padding=10)
            self.frame.pack(fill="both", expand=True)
            self._build_ui()
        else:
            # headless mode for testing
            self.root = None
            self.tools_frame = None
            # populate minimal tool_vars for headless use
            for t in self.tools:
                name = t["name"]

                # use a small DummyVar to emulate tk.IntVar in headless mode
                class DummyVar:
                    def __init__(self, value: int = 0):
                        self._v = int(value)

                    def get(self) -> int:
                        return int(self._v)

                    def set(self, v: int) -> None:
                        self._v = int(v)

                self.tool_vars[name] = DummyVar(0)
                self.tool_status_labels[name] = None
            # headless widgets
            self.cancel_btn = None
            self.status_bar = None
            self.overall_progress = None
            self.log_text = None
            self._spinner_jobs = {}
            self._spinner_index = {}

    def _build_ui(self):
        label = ttk.Label(self.frame, text="Select tools to install")
        label.pack(anchor="w")
        # Create a notebook with tabs per category
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill="both", expand=True)
        # Create category tabs from installer config
        categories = {}
        for t in self.tools:
            cat = t.get("category", "Other")
            categories.setdefault(cat, []).append(t)
        for cat, tools in categories.items():
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=cat)
            # add a scrollable frame within the tab
            canvas = tk.Canvas(tab)
            scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
            subframe = ttk.Frame(canvas)
            subframe.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")),
            )
            canvas.create_window((0, 0), window=subframe, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            categories[cat] = (tools, subframe)
        # Keep tabs structure
        self._category_tabs = categories

        # Populate items across category tabs
        for cat, (tools, subframe) in self._category_tabs.items():
            for t in tools:
                name = t["name"]
                if self.create_root:
                    var = tk.IntVar(value=0)
                    row = ttk.Frame(subframe)
                    row.pack(fill="x", anchor="w", padx=2, pady=2)
                    cb = ttk.Checkbutton(
                        row, text=f"{name} - {t.get('description','')}", variable=var
                    )
                    cb.pack(side="left", anchor="w")
                    status_lbl = ttk.Label(row, text="idle", width=12, anchor="e")
                    status_lbl.pack(side="right", anchor="e", padx=4)
                    self.tool_status_labels[name] = status_lbl
                else:
                    var = 0
                    self.tool_status_labels[name] = None
                self.tool_vars[name] = var

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", pady=8)
        preview_btn = ttk.Button(btn_frame, text="Preview", command=self.on_preview)
        preview_btn.pack(side="left", padx=4)
        install_btn = ttk.Button(btn_frame, text="Install", command=self.on_install)
        install_btn.pack(side="left", padx=4)
        install_all_btn = ttk.Button(
            btn_frame, text="Install All", command=self.on_install_all
        )
        install_all_btn.pack(side="left", padx=4)
        select_all_btn = ttk.Button(
            btn_frame, text="Select All", command=self.on_select_all
        )
        select_all_btn.pack(side="left", padx=4)
        clear_all_btn = ttk.Button(
            btn_frame, text="Clear All", command=self.on_clear_all
        )
        clear_all_btn.pack(side="left", padx=4)
        details_btn = ttk.Button(btn_frame, text="Details", command=self.on_details)
        details_btn.pack(side="left", padx=4)
        choose_dir_btn = ttk.Button(
            btn_frame, text="Install Dir", command=self.on_choose_install_dir
        )
        choose_dir_btn.pack(side="left", padx=4)
        set_space_btn = ttk.Button(
            btn_frame, text="Min Space", command=self.on_set_min_space
        )
        set_space_btn.pack(side="left", padx=4)
        close_btn = ttk.Button(
            btn_frame,
            text="Close",
            command=(self.root.destroy if self.root else (lambda: None)),
        )
        close_btn.pack(side="right", padx=4)
        # Add a Cancel button disabled by default
        self.cancel_btn = ttk.Button(
            btn_frame, text="Cancel", command=self.on_cancel, state="disabled"
        )
        self.cancel_btn.pack(side="right", padx=4)

        # Log area
        # Bottom area: unified status/progress bar and collapsible console
        if self.create_root:
            self.bottom_frame = ttk.Frame(self.root)
            self.bottom_frame.pack(fill="x", side="bottom")

            # Progress canvas behind status label so status text appears on top
            self.progress_canvas = tk.Canvas(
                self.bottom_frame, height=24, highlightthickness=0
            )
            self.progress_canvas.pack(fill="x", side="top")
            self._progress_height = 24
            self._progress_rect = self.progress_canvas.create_rectangle(
                0, 0, 0, self._progress_height, fill="#4caf50", width=0
            )

            # Status label sits on top of canvas
            self.status_bar = ttk.Label(
                self.bottom_frame, text="Ready", anchor="w", background=""
            )
            # Use place to overlay the label over the canvas
            self.status_bar.place(
                in_=self.progress_canvas, relx=0.01, rely=0.0, relheight=1.0
            )

            # Toggle button to collapse/expand console
            self._console_shown = True
            toggle_frame = ttk.Frame(self.bottom_frame)
            toggle_frame.pack(fill="x", side="top")
            self.toggle_console_btn = ttk.Button(
                toggle_frame,
                text="Hide Console",
                width=12,
                command=self._toggle_console,
            )
            self.toggle_console_btn.pack(side="right", padx=4, pady=2)

            # Console area (collapsible)
            self.console_frame = ttk.Frame(self.root)
            self.console_frame.pack(fill="both", side="bottom")
            self.log_text = tk.Text(self.console_frame, height=10, state="disabled")
            # configure tags for colored log levels
            self.log_text.tag_config("INFO", foreground="black")
            self.log_text.tag_config("WARN", foreground="orange")
            self.log_text.tag_config("ERROR", foreground="red")
            self.log_text.tag_config("DEBUG", foreground="gray")
            self.log_text.tag_config("TOOL", foreground="#0066cc")
            self.log_text.pack(fill="both", expand=True)
        else:
            self.status_bar = None
            self.progress_canvas = None
            self._progress_rect = None
            self._progress_height = 0
            self.log_text = None

        # Keyboard shortcuts for power users
        try:
            self.root.bind("<p>", lambda e: self.on_preview())
            self.root.bind("<i>", lambda e: self.on_install())
            self.root.bind("<a>", lambda e: self.on_select_all())
            self.root.bind("<c>", lambda e: self.on_clear_all())
            self.root.bind(
                "<Escape>", lambda e: (self.root.destroy() if self.root else None)
            )
        except Exception:
            pass

    def on_preview(self):
        selected = [
            name
            for name, var in self.tool_vars.items()
            if (var.get() if hasattr(var, "get") else var)
        ]
        if not selected:
            if self.create_root:
                messagebox.showinfo("Preview", "No tools selected")
            else:
                self._log("Preview: No tools selected")
            return
        preview = self.installer  # use installer to get tool info
        # Summarize basic info
        summary = []
        for name in selected:
            tool = next((t for t in self.tools if t["name"] == name), None)
            if not tool:
                continue
            build_cmds = tool.get("build_commands", {}).get(
                __import__("sys").platform, []
            )
            summary.append(f"{name}: Build commands: {build_cmds}")
        if self.create_root:
            messagebox.showinfo("Preview", "\n".join(summary))
        else:
            self._log("Preview generated:\n" + "\n".join(summary))
        if self.status_bar:
            self.status_bar.configure(text="Preview generated")

    def _log(self, msg: str) -> None:
        log_widget = getattr(self, "log_text", None)
        if hasattr(log_widget, "configure"):
            log_widget.configure(state="normal")
            # choose tag based on message content
            tag = "INFO"
            m = msg.lower()
            if "error" in m or "failed" in m or "exception" in m:
                tag = "ERROR"
            elif "warn" in m or "warning" in m:
                tag = "WARN"
            elif "debug" in m:
                tag = "DEBUG"
            # if it's a tool line like [tool] ..., add TOOL tag as well
            tags = (tag,)
            try:
                if msg.startswith("["):
                    # annotate tool prefix specially
                    # insert with TOOL tag and rest with level tag
                    end_idx = msg.find("]")
                    if end_idx != -1:
                        prefix = msg[: end_idx + 1]
                        rest = msg[end_idx + 1 :]
                        log_widget.insert("end", prefix)
                        log_widget.insert("end", rest + "\n", tag)
                    else:
                        log_widget.insert("end", msg + "\n", tag)
                else:
                    log_widget.insert("end", msg + "\n", tag)
            except Exception:
                log_widget.insert("end", msg + "\n")
            log_widget.configure(state="disabled")
            log_widget.see("end")
        else:
            self._log_lines.append(msg)
        # Update status bar with last message if exists
        if getattr(self, "status_bar", None) and hasattr(self.status_bar, "configure"):
            self.status_bar.configure(text=msg)

    def on_install(self):
        selected = [
            name
            for name, var in self.tool_vars.items()
            if (var.get() if hasattr(var, "get") else var)
        ]
        if not selected:
            if self.create_root:
                messagebox.showinfo("Install", "No tools selected")
            else:
                self._log("Install: No tools selected")
            return

        if self.create_root:
            if not messagebox.askyesno(
                "Confirm Install", f"Proceed to install {len(selected)} tool(s)?"
            ):
                return
        else:
            self._log(f"Proceeding to install {len(selected)} tool(s) (headless)")

        # create a stop event here so tests/main thread can cancel immediately
        stop_event = threading.Event()
        self.cancel_event = stop_event
        # track overall progress across selected tools
        self._install_total = len(selected)
        self._install_completed = 0

        def run_installs():
            # progress callback invoked by installer
            def progress_cb(tool_name, state, message):
                # schedule UI updates
                if self.root:
                    self.root.after(
                        0, lambda: self._on_progress(tool_name, state, message)
                    )
                else:
                    # headless mode: just log
                    if state == "starting":
                        self._log(f"Starting {tool_name}")
                    elif state == "success":
                        self._log(f"Success {tool_name}")
                    elif state == "failed":
                        self._log(f"Failed {tool_name}: {message}")
                    elif state == "log":
                        # streaming build output lines
                        self._log(f"[{tool_name}] {message}")

            try:
                if self.cancel_btn:
                    try:
                        self.root.after(
                            0, lambda: self.cancel_btn.configure(state="normal")
                        )
                    except Exception:
                        pass
                total = len(selected)
                completed = 0
                # initialize progress canvas width to 0
                if getattr(self, "progress_canvas", None):
                    try:
                        self._set_progress_percent(0)
                    except Exception:
                        pass
                # call installer with progress_callback and stop_event
                self._log("Calling installer.install_selected_tools")
                try:
                    self.installer.install_selected_tools(
                        selected, progress_callback=progress_cb, stop_event=stop_event
                    )
                finally:
                    self._log("Returned from installer.install_selected_tools")
            except Exception as e:
                self._log(f"Error during installs: {e}")
            finally:
                if self.cancel_btn:
                    # disable Cancel
                    try:
                        self.root.after(
                            0, lambda: self.cancel_btn.configure(state="disabled")
                        )
                    except Exception:
                        pass
                # clear cancel_event
                self.cancel_event = None

        threading.Thread(target=run_installs, daemon=True).start()

    def on_install_all(self):
        # Select all tools and run install
        for name, var in self.tool_vars.items():
            if hasattr(var, "set"):
                var.set(1)
        self.on_install()

    def on_select_all(self):
        for name, var in self.tool_vars.items():
            if hasattr(var, "set"):
                var.set(1)

    def on_clear_all(self):
        for name, var in self.tool_vars.items():
            if hasattr(var, "set"):
                var.set(0)

    def set_selected(self, names: List[str]) -> None:
        """Set selected tools programmatically (useful for tests/headless).

        names: list of tool names to select; others will be cleared.
        """
        for name, var in self.tool_vars.items():
            if hasattr(var, "set"):
                var.set(1 if name in names else 0)

    def on_details(self):
        selected = [
            name
            for name, var in self.tool_vars.items()
            if (var.get() if hasattr(var, "get") else var)
        ]
        if not selected:
            if self.create_root:
                messagebox.showinfo("Details", "No tools selected")
            else:
                self._log("Details: No tools selected")
            return
        name = selected[0]
        tool = next((t for t in self.tools if t["name"] == name), None)
        if not tool:
            return
        url = tool.get("url", "")
        build_cmds = tool.get("build_commands", {})
        build_text = (
            build_cmds.get(__import__("sys").platform, "")
            if isinstance(build_cmds, dict)
            else build_cmds
        )
        content = f"{tool.get('description', '')}\n\nURL: {url}\nBuild: {build_text}\n"
        messagebox.showinfo("Details", content)

    def on_choose_install_dir(self):
        if not self.root:
            return
        d = filedialog.askdirectory(initialdir=str(self.installer.install_dir))
        if d:
            self.installer.install_dir = Path(d)
            self._log(f"Install dir set to {d}")

    def on_set_min_space(self):
        if not self.root:
            return
        val = simpledialog.askinteger(
            "Min Space",
            "Minimum free space in MB",
            initialvalue=self.installer.min_free_bytes // (1024 * 1024),
        )
        if val is not None:
            self.installer.min_free_bytes = int(val) * 1024 * 1024
            self._log(f"Min space set to {val} MB")

    def on_cancel(self):
        """Set the cancel event to signal a running install to stop."""
        if getattr(self, "cancel_event", None):
            try:
                self.cancel_event.set()
                self._log("Cancel requested")
            except Exception:
                pass

    def run(self):
        self.root.mainloop()

    def _set_progress_percent(self, percent: int) -> None:
        """Update the progress canvas fill to the given percent (0-100)."""
        try:
            percent = max(0, min(100, int(percent)))
        except Exception:
            percent = 0
        self._overall_percent = percent
        if not getattr(self, "progress_canvas", None):
            return
        try:
            w = (
                self.progress_canvas.winfo_width()
                or self.progress_canvas.winfo_reqwidth()
                or 1
            )
            fill_w = int((percent / 100.0) * w)
            self.progress_canvas.coords(
                self._progress_rect, 0, 0, fill_w, self._progress_height
            )
        except Exception:
            pass

    def _toggle_console(self):
        # toggle console visibility
        if not getattr(self, "console_frame", None):
            return
        if self._console_shown:
            self.console_frame.forget()
            self.toggle_console_btn.configure(text="Show Console")
            self._console_shown = False
        else:
            self.console_frame.pack(fill="both", side="bottom")
            self.toggle_console_btn.configure(text="Hide Console")
            self._console_shown = True

    def _start_spinner(self, tool_name: str) -> None:
        """Start a small spinner animation in the tool's label."""
        if not getattr(self, "root", None):
            return
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        # stop existing spinner if any
        self._stop_spinner(tool_name)
        self._spinner_index[tool_name] = 0

        def _spin():
            lbl = self.tool_status_labels.get(tool_name)
            if not lbl:
                return
            idx = self._spinner_index.get(tool_name, 0)
            ch = frames[idx % len(frames)]
            try:
                lbl.configure(text=ch)
            except Exception:
                pass
            self._spinner_index[tool_name] = idx + 1
            # schedule next
            try:
                job = self.root.after(120, _spin)
                self._spinner_jobs[tool_name] = job
            except Exception:
                self._spinner_jobs[tool_name] = None

        _spin()

    def _stop_spinner(self, tool_name: str) -> None:
        """Stop spinner for a tool if running."""
        if not getattr(self, "root", None):
            return
        job = self._spinner_jobs.get(tool_name)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self._spinner_jobs[tool_name] = None
        self._spinner_index[tool_name] = 0

    def _on_progress(self, tool_name: str, state: str, message: Optional[str]):
        # update status label and log
        label = self.tool_status_labels.get(tool_name)
        # update per-tool label with simple states and checkmarks
        if label:
            try:
                if state == "starting":
                    # start spinner for this tool
                    self._start_spinner(tool_name)
                elif state == "success":
                    self._stop_spinner(tool_name)
                    label.configure(text="✔")
                elif state in ("failed", "cancelled"):
                    self._stop_spinner(tool_name)
                    label.configure(text="✖")
                elif state == "log":
                    # don't change label on log lines
                    pass
            except Exception:
                pass

        # Log state transitions and update unified progress/status UI
        if state == "starting":
            self._log(f"Starting {tool_name}...")
            if getattr(self, "status_bar", None):
                self.status_bar.configure(text=f"Starting {tool_name}...")
        elif state == "success":
            self._log(f"Installed {tool_name}")
            if getattr(self, "status_bar", None):
                self.status_bar.configure(text=f"Installed {tool_name}")
            # increment overall progress
            try:
                if hasattr(self, "_install_total") and self._install_total:
                    self._install_completed = getattr(self, "_install_completed", 0) + 1
                    pct = int(
                        (self._install_completed / max(1, self._install_total)) * 100
                    )
                    self._set_progress_percent(pct)
            except Exception:
                pass
        elif state in ("failed", "cancelled"):
            self._log(f"Failed to install {tool_name}: {message}")
            if getattr(self, "status_bar", None):
                self.status_bar.configure(text=f"Failed {tool_name}: {message}")
        elif state == "log":
            # streaming build output lines
            if message is not None:
                self._log(f"[{tool_name}] {message}")


def main():
    config_file = Path(__file__).parent / "tools_config.json"
    gui = SNESTkGui(config_file)
    gui.run()


if __name__ == "__main__":
    main()
