"""Simple Tk GUI wrapper for the SNES Installer.

This is intentionally minimal: it demonstrates a GUI with tool checkboxes, preview, and install.
It uses the same ToolInstaller API and honors dry_run/install_dir/min_space options.
"""
import threading
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent))
from snes_installer.installer import ToolInstaller


class SNESTkGui:
    def __init__(self, config_file: Path, install_dir: Path | None = None, min_space: int | None = None, dry_run: bool = False, create_root: bool = True):
        self.config_file = config_file
        self.install_dir = install_dir
        self.min_space = min_space
        self.dry_run = dry_run
        self.installer = ToolInstaller(config_file, dry_run=dry_run, min_free_bytes=(min_space or 200*1024*1024), install_dir=install_dir)
        self.tools = self.installer.load_config().get('tools', [])

        self.root = None
        self.frame = None
        self.create_root = create_root
        self.tool_vars: Dict[str, tk.IntVar] = {}
        if create_root:
            self.root = tk.Tk()
            self.root.title('SNES Installer GUI')
            self.frame = ttk.Frame(self.root, padding=10)
            self.frame.pack(fill='both', expand=True)
            self._build_ui()
        else:
            # headless mode for testing
            self.root = None
            self.tools_frame = None

    def _build_ui(self):
        label = ttk.Label(self.frame, text='Select tools to install')
        label.pack(anchor='w')
        canvas = tk.Canvas(self.frame)
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=canvas.yview)
        self.tools_frame = ttk.Frame(canvas)
        self.tools_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.tools_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        for t in self.tools:
            if self.create_root:
                var = tk.IntVar(value=0)
                cb = ttk.Checkbutton(self.tools_frame, text=f"{t['name']} - {t.get('description','')}", variable=var)
                cb.pack(anchor='w')
            else:
                var = 0
            self.tool_vars[t['name']] = var

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill='x', pady=8)
        preview_btn = ttk.Button(btn_frame, text='Preview', command=self.on_preview)
        preview_btn.pack(side='left', padx=4)
        install_btn = ttk.Button(btn_frame, text='Install', command=self.on_install)
        install_btn.pack(side='left', padx=4)
        close_btn = ttk.Button(btn_frame, text='Close', command=(self.root.destroy if self.root else (lambda: None)))
        close_btn.pack(side='right', padx=4)

        # Log area
        self.log_text = tk.Text(self.root, height=10, state='disabled')
        self.log_text.pack(fill='both', expand=False)

    def on_preview(self):
        selected = [name for name, var in self.tool_vars.items() if (var.get() if hasattr(var, 'get') else var)]
        if not selected:
            messagebox.showinfo('Preview', 'No tools selected')
            return
        preview = self.installer  # reuse TUI generator? instantiate a local TUI? Use installer directly
        # Summarize basic info
        summary = []
        for name in selected:
            tool = next((t for t in self.tools if t['name'] == name), None)
            if not tool:
                continue
            build_cmds = tool.get('build_commands', {}).get(__import__('sys').platform, [])
            summary.append(f"{name}: Build commands: {build_cmds}")
        messagebox.showinfo('Preview', '\n'.join(summary))

    def _log(self, msg: str) -> None:
        self.log_text.configure(state='normal')
        self.log_text.insert('end', msg + '\n')
        self.log_text.configure(state='disabled')
        self.log_text.see('end')

    def on_install(self):
        selected = [name for name, var in self.tool_vars.items() if (var.get() if hasattr(var, 'get') else var)]
        if not selected:
            messagebox.showinfo('Install', 'No tools selected')
            return

        if not messagebox.askyesno('Confirm Install', f'Proceed to install {len(selected)} tool(s)?'):
            return

        def run_installs():
            for name in selected:
                try:
                    self._log(f'Installing {name}...')
                    self.installer.install_selected_tools([name])
                    self._log(f'Installed {name}')
                except Exception as e:
                    self._log(f'Failed to install {name}: {e}')

        threading.Thread(target=run_installs, daemon=True).start()

    def run(self):
        self.root.mainloop()


def main():
    config_file = Path(__file__).parent / 'tools_config.json'
    gui = SNESTkGui(config_file)
    gui.run()

if __name__ == '__main__':
    main()
