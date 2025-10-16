#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import os
import platform
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

class PathManager:

    def __init__(self):
        """Initialize the PathManager to determine the root path based on execution context."""
        self.root = self._get_root_path()

    def _get_root_path(self) -> Path:
        """Determine the root path based on whether the script is run as a frozen executable or a Python script."""
        if getattr(sys, 'frozen', False):
            print("Executable path mode chosen")
            return Path(sys.executable).parent.parent
        else:
            print("Python script path mode chosen")
            return Path(__file__).absolute().parent.parent

    def get_tool_path(self, *parts) -> Path:
        """Construct a path to a tool within the 'libs' directory."""
        return self.root.joinpath(*parts)

class M8TEExecutor:

    def __init__(self, path_manager: PathManager, console: Console):
        """Initialize the M8TEExecutor with the path to the M8TE executable."""
        self.m8te_path = path_manager.get_tool_path("libs", "M8TE", "bin", "M8TE.exe")
        self.path_manager = path_manager
        self.console = console

    def run(self):
        """Run the M8TE executable and handle any errors."""
        try:
            if not self.m8te_path.exists():
                # Try alternative paths or provide helpful error
                alt_path = self.path_manager.get_tool_path("libs", "M8TE", "M8TE.exe")
                if alt_path.exists():
                    self.m8te_path = alt_path
                else:
                    self.console.print("\n[red]M8TE Not Found[/red]")
                    self.console.print("M8TE executable not found. This tool is only available on Windows builds of SNES-IDE.")
                    self.console.print("\nOn other platforms, you can:")
                    self.console.print("• Install M8TE via Wine/CrossOver")
                    self.console.print("• Use alternative tile editors")
                    self.console.print("• Check the PLATFORM_TOOLS_README.md file for more information")
                    return -1

            subprocess.run([str(self.m8te_path)], check=True)
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Error while executing {self.m8te_path}: {e}[/red]")
            return -1
        except FileNotFoundError:
            self.console.print(f"[red]M8TE executable not found at {self.m8te_path}.[/red]")
            self.console.print("This tool may not be available on your platform.")
            return -1

        self.console.print("[green]Success![/green]")
        return 0

class Gfx4SnesExecutor:

    def __init__(self, path_manager: PathManager, console: Console):
        """Initialize the Gfx4SnesExecutor with the path to the gfx4snes executable."""
        self.gfx4snes_path = path_manager.get_tool_path("libs", "pvsneslib", "tools", "gfx4snes.exe")
        self.root = path_manager.root
        self.console = console

    def run(self):
        """Run the gfx4snes tool with user-selected options and input file."""
        try:
            # Get input file from user
            input_file = self._get_input_file()
            if not input_file:
                return -1

            # Get options from user
            options = self._get_options()
            if options is None:
                return -1

            # Execute the command
            self._execute(input_file, options)

        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Error while executing {self.gfx4snes_path}: {e}[/red]")
            return -1
        except FileNotFoundError:
            self.console.print(f"[red]gfx4snes executable not found at {self.gfx4snes_path}[/red]")
            return -1

        self.console.print("[green]Success![/green]")
        return 0

    def _get_input_file(self):
        """Get input file path from user."""
        self.console.print("\n[yellow]Select your image file (PNG or BMP):[/yellow]")
        input_file = Prompt.ask("Enter the full path to your image file").strip()

        if not input_file:
            self.console.print("[red]No input file selected[/red]")
            return None

        input_path = Path(input_file)
        if not input_path.exists():
            self.console.print(f"[red]File not found: {input_file}[/red]")
            return None

        if input_path.suffix.lower() not in ['.png', '.bmp']:
            self.console.print("[red]Please select a PNG or BMP file[/red]")
            return None

        return str(input_path)

    def _get_options(self):
        """Get options from user input."""
        self.console.print("\n[yellow]Available options for gfx4snes:[/yellow]")
        options = [
            ("-b", "add blank tile management (for multiple bgs)"),
            ("-n", "no optimization of tile (keep all tiles)"),
            ("-s", "share duplicate tiles (tile optimization)"),
            ("-t", "output palette and tile data in binary format"),
            ("-m", "output map data in binary format"),
            ("-p", "output palette data in binary format"),
            ("-z", "compress the output files with gzip"),
            ("-q", "quiet mode (no output)"),
        ]

        for flag, desc in options:
            self.console.print(f"  {flag}: {desc}")

        self.console.print("\n[yellow]Enter options (space-separated, or 'none' for defaults):[/yellow]")
        option_input = Prompt.ask("Options").strip().lower()

        if option_input == 'none' or not option_input:
            return []

        return option_input.split()

    def _execute(self, input_file, options):
        """Execute the gfx4snes command."""
        cmd = [str(self.gfx4snes_path)] + options + [input_file]
        self.console.print(f"\n[blue]Running: {' '.join(cmd)}[/blue]")
        subprocess.run(cmd, check=True)

class SnesToolsExecutor:

    def __init__(self, path_manager: PathManager, console: Console):
        """Initialize the SnesToolsExecutor."""
        self.snestools_path = path_manager.get_tool_path("libs", "pvsneslib", "tools", "snestools.exe")
        self.console = console

    def run(self):
        """Run the snestools with user-selected file."""
        try:
            input_file = self._get_input_file()
            if not input_file:
                return -1

            cmd = [str(self.snestools_path), input_file]
            self.console.print(f"\n[blue]Running: {' '.join(cmd)}[/blue]")
            subprocess.run(cmd, check=True)

        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Error while executing snestools: {e}[/red]")
            return -1
        except FileNotFoundError:
            self.console.print(f"[red]snestools executable not found at {self.snestools_path}[/red]")
            return -1

        self.console.print("[green]Success![/green]")
        return 0

    def _get_input_file(self):
        """Get input file path from user."""
        self.console.print("\n[yellow]Select your SNES ROM file (SMC/SFC):[/yellow]")
        input_file = Prompt.ask("Enter the full path to your ROM file").strip()

        if not input_file:
            self.console.print("[red]No input file selected[/red]")
            return None

        input_path = Path(input_file)
        if not input_path.exists():
            self.console.print(f"[red]File not found: {input_file}[/red]")
            return None

        if input_path.suffix.lower() not in ['.smc', '.sfc']:
            self.console.print("[red]Please select a SMC or SFC file[/red]")
            return None

        return str(input_path)

class Tmx2SnesExecutor:

    def __init__(self, path_manager: PathManager, console: Console):
        """Initialize the Tmx2SnesExecutor."""
        self.tmx2snes_path = path_manager.get_tool_path("libs", "pvsneslib", "tools", "tmx2snes.exe")
        self.console = console

    def run(self):
        """Run the tmx2snes tool."""
        try:
            tmx_file = self._get_tmx_file()
            if not tmx_file:
                return -1

            map_file = self._get_map_file()
            if not map_file:
                return -1

            cmd = [str(self.tmx2snes_path), tmx_file, map_file]
            self.console.print(f"\n[blue]Running: {' '.join(cmd)}[/blue]")
            subprocess.run(cmd, check=True)

        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]Error while executing tmx2snes: {e}[/red]")
            return -1
        except FileNotFoundError:
            self.console.print(f"[red]tmx2snes executable not found at {self.tmx2snes_path}[/red]")
            return -1

        self.console.print("[green]Success![/green]")
        return 0

    def _get_tmx_file(self):
        """Get TMX file path from user."""
        self.console.print("\n[yellow]Select your TMX file:[/yellow]")
        input_file = Prompt.ask("Enter the full path to your TMX file").strip()

        if not input_file:
            self.console.print("[red]No TMX file selected[/red]")
            return None

        input_path = Path(input_file)
        if not input_path.exists():
            self.console.print(f"[red]File not found: {input_file}[/red]")
            return None

        if input_path.suffix.lower() != '.tmx':
            self.console.print("[red]Please select a TMX file[/red]")
            return None

        return str(input_path)

    def _get_map_file(self):
        """Get MAP file path from user."""
        self.console.print("\n[yellow]Select your MAP file:[/yellow]")
        input_file = Prompt.ask("Enter the full path to your MAP file").strip()

        if not input_file:
            self.console.print("[red]No MAP file selected[/red]")
            return None

        input_path = Path(input_file)
        if not input_path.exists():
            self.console.print(f"[red]File not found: {input_file}[/red]")
            return None

        return str(input_path)

class FontCopier:

    def __init__(self, path_manager: PathManager, console: Console):
        """Initialize the FontCopier."""
        self.font_path = path_manager.get_tool_path("libs", "pvsneslib", "tools", "font.png")
        self.console = console

    def run(self):
        """Copy the font file to user-selected location."""
        try:
            dest_dir = self._get_destination()
            if not dest_dir:
                return -1

            dest_path = Path(dest_dir) / "font.png"
            import shutil
            shutil.copy2(str(self.font_path), str(dest_path))

            self.console.print(f"[green]Font copied to: {dest_path}[/green]")

        except Exception as e:
            self.console.print(f"[red]Error copying font: {e}[/red]")
            return -1

        return 0

    def _get_destination(self):
        """Get destination directory from user."""
        self.console.print("\n[yellow]Select destination folder for font.png:[/yellow]")
        dest_dir = Prompt.ask("Enter the full path to the destination folder").strip()

        if not dest_dir:
            self.console.print("[red]No destination selected[/red]")
            return None

        dest_path = Path(dest_dir)
        if not dest_path.exists():
            self.console.print(f"[red]Directory not found: {dest_dir}[/red]")
            return None

        if not dest_path.is_dir():
            self.console.print(f"[red]Path is not a directory: {dest_dir}[/red]")
            return None

        return str(dest_path)

class HTTPServer:
    """Simple HTTP server to serve the tileset extractor."""

    def __init__(self, path: Path):
        self.path = path
        self.process = None

    def run(self):
        """Start the HTTP server."""
        import http.server
        import socketserver
        import threading

        # Change to the directory containing the HTML file
        os.chdir(self.path.parent)

        # Find an available port
        port = 8000
        while port < 8100:
            try:
                with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
                    self.process = httpd
                    url = f"http://localhost:{port}/{self.path.name}"
                    print(f"Serving tileset extractor at: {url}")
                    print("Press Ctrl+C to stop the server")
                    httpd.serve_forever()
                break
            except OSError:
                port += 1

    def stop(self):
        """Stop the HTTP server."""
        if self.process:
            self.process.shutdown()
            self.process = None

class TilesetExtractorOpener:

    def __init__(self, path_manager: PathManager, console: Console):
        """Initialize the TilesetExtractorOpener."""
        self.tse_path = path_manager.get_tool_path("libs", "pvsneslib", "tools", "tilesetextractor", "index.html")
        self.console = console

    def run(self):
        """Open the tileset extractor in the default web browser."""
        try:
            if not self.tse_path.exists():
                self.console.print(f"[red]Tileset extractor not found at {self.tse_path}[/red]")
                return -1

            # Start HTTP server
            server = HTTPServer(self.tse_path)
            server.run()

        except Exception as e:
            self.console.print(f"[red]Error opening tileset extractor: {e}[/red]")
            return -1

        return 0

class GfxToolsApp:

    def __init__(self):
        """Initialize the GfxToolsApp with TUI interface."""
        self.path_manager = PathManager()
        self.console = Console()
        self.tools = [
            ("M8TE - Mode 3 and 7 tileset and tilemap editor", M8TEExecutor(self.path_manager, self.console).run),
            ("gfx4snes - Convert images to SNES format (.pic, .pal, .map)", Gfx4SnesExecutor(self.path_manager, self.console).run),
            ("snestools - SNES ROM file info viewer", SnesToolsExecutor(self.path_manager, self.console).run),
            ("tmx2snes - TMX and map converter", Tmx2SnesExecutor(self.path_manager, self.console).run),
            ("Font Generator - Copy pvsneslib font.png", FontCopier(self.path_manager, self.console).run),
            ("Tileset Extractor - Online tileset extractor by André Michelle", TilesetExtractorOpener(self.path_manager, self.console).run),
        ]

    def show_menu(self):
        """Display the graphics tools menu."""
        self.console.print("\n[bold cyan]SNES Graphics Tools[/bold cyan]")
        self.console.print("=" * 50)

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan", no_wrap=True)
        table.add_column("Tool", style="white")
        table.add_column("Description", style="yellow")

        for i, (name, _) in enumerate(self.tools):
            tool_name = name.split(" - ")[0]
            description = name.split(" - ")[1] if " - " in name else ""
            table.add_row(str(i), tool_name, description)

        self.console.print(table)
        self.console.print("\n[dim]Enter option number or 'q' to quit[/dim]")

    def run(self):
        """Run the TUI application."""
        while True:
            self.show_menu()
            choice = Prompt.ask("\nChoose a tool").strip().lower()

            if choice == 'q':
                break

            try:
                option = int(choice)
                if 0 <= option < len(self.tools):
                    tool_name, tool_func = self.tools[option]
                    self.console.print(f"\n[bold]Running {tool_name.split(' - ')[0]}...[/bold]")
                    result = tool_func()
                    if result == -1:
                        self.console.print("[red]Tool execution failed[/red]")
                    Prompt.ask("\nPress Enter to continue")
                else:
                    self.console.print("[red]Invalid option[/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number[/red]")

if __name__ == "__main__":
    """Run the GfxToolsApp if this script is executed directly."""
    app = GfxToolsApp()
    app.run()
