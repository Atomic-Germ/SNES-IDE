#!/usr/bin/env python3
from pathlib import Path
from array import array
import subprocess
import sys
import platform
import os
import json
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

class SnesIde(object):

    def __init__(self, *args: object, **kwargs: object) -> None:
        """
        Initializes the class instance.

        - Detects the platform (Windows, macOS, Linux)
        - Sets platform-specific paths and configurations
        - Initializes the options array with values 0 through 6.
        - Prompts the user to select an option.
        - Executes a script based on the selected OS and options and exits the program.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """

        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        self.is_macos = self.platform == "darwin"
        self.is_linux = self.platform == "linux"

        # Set platform-specific paths
        self.executable_path = self.get_executable_path()
        self.config_file = self.executable_path / "snes-ide-config.json"

        # Load or create configuration
        self.config = self.load_config()

        # Initialize Rich console for TUI
        self.console = Console()

        # Set platform-specific installation paths
        self.install_path = self.get_install_path()
        self.tools_path = self.get_tools_path()

        self.options: array = array("B", (0, 1, 2, 3, 4, 5, 6, 7))

        option = self.give_options()

        sys.exit(self.execute_command(option))


    def load_config(self) -> dict:
        """
        Load configuration from file or create default configuration.

        Returns:
            dict: Configuration dictionary
        """
        default_config = {
            "text_editor": self.get_default_text_editor(),
            "last_used_editor": None
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults for any missing keys
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except (json.JSONDecodeError, IOError):
                print("Warning: Could not load config file, using defaults")

        return default_config


    def save_config(self) -> None:
        """
        Save current configuration to file.
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError:
            print("Warning: Could not save config file")


    def get_default_text_editor(self) -> str:
        """
        Get the default text editor for the current platform.

        Returns:
            str: Default text editor command
        """
        if self.is_macos:
            # Try VS Code first, then other editors
            editors = [
                "code",  # VS Code
                "vim",
                "nano",
                "open -a TextEdit"  # macOS default
            ]
        elif self.is_linux:
            editors = [
                "code",
                "vim",
                "nano",
                "gedit",
                "kate"
            ]
        else:  # Windows
            editors = [
                "code",
                "notepad++",
                "notepad"
            ]

        # Return the first available editor
        for editor in editors:
            if self.is_editor_available(editor):
                return editor

        return "notepad" if self.is_windows else "nano"


    def is_editor_available(self, editor_cmd: str) -> bool:
        """
        Check if a text editor command is available on the system.

        Args:
            editor_cmd: The editor command to check

        Returns:
            bool: True if the editor is available
        """
        try:
            # For commands that might have arguments, just check the base command
            base_cmd = editor_cmd.split()[0]
            subprocess.run([base_cmd, "--version" if base_cmd in ["code", "vim", "nano"] else "--help"],
                         capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False


    def get_install_path(self) -> Path:
        """
        Get the platform-specific installation path.

        Returns:
            Path: Installation directory path
        """
        if self.is_macos:
            return Path.home() / "Applications" / "SNES-IDE"
        elif self.is_linux:
            return Path.home() / ".local" / "share" / "snes-ide"
        else:  # Windows
            return Path.home() / "Desktop" / "snes-ide"


    def get_tools_path(self) -> Path:
        """
        Get the path to the tools directory, handling both development and installed modes.

        Returns:
            Path: Tools directory path
        """
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle - use install path
            return self.install_path / "tools"
        else:
            # Running in development - use src/tools relative to script
            return self.executable_path / "tools"


    @staticmethod
    def run_command(command: list, cwd: Path = None) -> None:
        """
        Execute a command using the appropriate shell for the platform.

        Args:
            command: Command to execute as a list
            cwd: Working directory (optional)
        """
        try:
            if platform.system().lower() == "windows":
                subprocess.run(command, check=True, cwd=cwd)
            else:
                # Use shell=True for Unix-like systems to handle shell commands properly
                subprocess.run(command, check=True, cwd=cwd)
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            raise


    def execute_command(self, option: int) -> int:
        """
        Executes a command corresponding to the given option.

        Parameters:
            option (int): An integer representing the command to execute.
                0 - create-new-project
                1 - text-editor
                2 - audio-tools
                3 - graphic-tools
                4 - other-tools
                5 - compiler
                6 - emulator

        Returns:
            int: 0 if the command executed successfully, -1 if an error occurred.
        """

        if option == 7:
            self.configure_text_editor()
            return 0

        # Handle graphics tools internally to maintain TUI
        if option == 3:
            return self.run_gfx_tools()

        commands = {
            0: self.get_create_project_command(),
            1: self.get_text_editor_command(),
            2: self.get_audio_tools_command(),
            3: self.get_gfx_tools_command(),
            4: self.get_other_tools_command(),
            5: self.get_compiler_command(),
            6: self.get_emulator_command()
        }

        if option in commands:
            try:
                self.run_command(commands[option])
                return 0
            except subprocess.CalledProcessError:
                print(f"Error executing option {option}")
                return -1

        return -1

    def run_gfx_tools(self) -> int:
        """Run the graphics tools menu internally."""
        try:
            # Import the graphics tools module
            import sys
            import importlib.util
            tools_path = self.tools_path
            gfx_tools_path = tools_path / "gfx-tools.py"

            # Load the module from file
            spec = importlib.util.spec_from_file_location("gfx_tools", str(gfx_tools_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load graphics tools from {gfx_tools_path}")

            gfx_tools_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gfx_tools_module)

            # Run the graphics tools app
            app = gfx_tools_module.GfxToolsApp()
            app.run()
            return 0
        except Exception as e:
            print(f"Error running graphics tools: {e}")
            return -1

    def get_create_project_command(self) -> list:
        """Get the command to create a new project."""
        script_path = self.tools_path / "create-new-project.py"
        if self.is_windows:
            return ["python", str(script_path)]
        else:
            return ["python3", str(script_path)]


    def get_text_editor_command(self) -> list:
        """Get the command to launch the text editor."""
        editor = self.config.get("text_editor", self.get_default_text_editor())

        # If it's a custom command with arguments, split it
        if " " in editor:
            return editor.split()
        else:
            return [editor]


    def get_audio_tools_command(self) -> list:
        """Get the command to launch audio tools."""
        script_path = self.tools_path / "audio-tools.py"
        if self.is_windows:
            return ["python", str(script_path)]
        else:
            return ["python3", str(script_path)]


    def get_gfx_tools_command(self) -> list:
        """Get the command to launch graphics tools."""
        script_path = self.tools_path / "gfx-tools.py"
        if self.is_windows:
            return ["python", str(script_path)]
        else:
            return ["python3", str(script_path)]


    def get_other_tools_command(self) -> list:
        """Get the command to launch other external tools."""
        script_path = self.tools_path / "externTools.py"
        if self.is_windows:
            return ["python", str(script_path)]
        else:
            return ["python3", str(script_path)]


    def get_compiler_command(self) -> list:
        """Get the command to launch the compiler."""
        script_path = self.tools_path / "automatizer-batch.bat" if self.is_windows else self.tools_path / "automatizer-batch.sh"
        if self.is_windows:
            return [str(script_path)]
        else:
            return ["/bin/bash", str(script_path)]


    def get_emulator_command(self) -> list:
        """Get the command to launch the emulator."""
        if self.is_windows:
            exe_path = self.install_path / "libs" / "bsnes" / "bsnes.exe"
            return [str(exe_path)]
        elif self.is_macos:
            app_path = self.install_path / "libs" / "bsnes" / "bsnes.app"
            return ["open", str(app_path)]
        else:  # Linux
            # Assume bsnes is installed system-wide or use a script
            return ["bsnes"]
    

    def configure_text_editor(self) -> None:
        """Configure the text editor preference."""
        print("\nCurrent text editor:", self.config.get("text_editor", "Not set"))

        if self.is_macos:
            editors = [
                ("code", "Visual Studio Code"),
                ("vim", "Vim"),
                ("nano", "Nano"),
                ("open -a TextEdit", "TextEdit (macOS default)"),
                ("open -a Xcode", "Xcode"),
            ]
        elif self.is_linux:
            editors = [
                ("code", "Visual Studio Code"),
                ("vim", "Vim"),
                ("nano", "Nano"),
                ("gedit", "Gedit"),
                ("kate", "Kate"),
                ("mousepad", "Mousepad"),
            ]
        else:  # Windows
            editors = [
                ("code", "Visual Studio Code"),
                ("notepad++", "Notepad++"),
                ("notepad", "Notepad"),
            ]

        print("\nAvailable editors:")
        for i, (cmd, name) in enumerate(editors):
            available = "✓" if self.is_editor_available(cmd.split()[0]) else "✗"
            print(f"  {i}: {name} ({available})")

        print("  c: Custom command")

        choice = input("\nSelect editor (number or 'c' for custom): ").strip().lower()

        if choice == 'c':
            custom_cmd = input("Enter custom editor command: ").strip()
            if custom_cmd:
                self.config["text_editor"] = custom_cmd
                self.save_config()
                print(f"Text editor set to: {custom_cmd}")
        elif choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(editors):
                cmd, name = editors[idx]
                if self.is_editor_available(cmd.split()[0]):
                    self.config["text_editor"] = cmd
                    self.save_config()
                    print(f"Text editor set to: {name}")
                else:
                    print(f"Warning: {name} doesn't appear to be available on your system.")
            else:
                print("Invalid selection.")
        else:
            print("Invalid input.")
    

    def give_options(self) -> int:
        """
        Presents a menu of SNES project-related options to the user and prompts for a selection.
        Uses Rich library to create a basic terminal user interface with a table of options.

        The available options include:
            0 - Create a new SNES project
            1 - Start code editor
            2 - Start an audio framework for SNES
            3 - Start a graphic framework for SNES
            4 - Run an external framework for SNES
            5 - Compile a SNES project
            6 - Emulate a SNES project with bsnes
            7 - Configure code editor

        Returns:
            int: The selected option as an integer.
        """

        # Create a welcome panel
        welcome_text = Text("SNES-IDE", style="bold magenta")
        welcome_panel = Panel(welcome_text, title="Welcome to", border_style="blue")
        self.console.print(welcome_panel)
        self.console.print()

        # Create options table
        table = Table(title="Available Options", show_header=True, header_style="bold blue")
        table.add_column("Option", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")

        editor_name = self.config.get("text_editor", "default").split()[0]

        options_data = [
            ("0", "Create a new SNES project"),
            ("1", f"Start {editor_name} text editor"),
            ("2", "Start an audio framework for SNES"),
            ("3", "Start a graphic framework for SNES"),
            ("4", "Run an external framework for SNES"),
            ("5", "Compile a SNES project"),
            ("6", "Emulate a SNES project with bsnes"),
            ("7", "Configure text editor"),
        ]

        for option_num, description in options_data:
            table.add_row(option_num, description)

        self.console.print(table)
        self.console.print()

        # Get user input with validation
        while True:
            try:
                choice = Prompt.ask("Choose an option", choices=[str(i) for i in self.options])
                option = int(choice)
                if option in self.options:
                    return option
                else:
                    self.console.print("[red]Invalid option selected. Please try again.[/red]")
            except (ValueError, EOFError):
                self.console.print("[red]Invalid input. Please enter a number.[/red]")



    @staticmethod
    def get_executable_path() -> Path:
        """
        Returns the directory path where the current executable or script is located.
        If the application is running as a PyInstaller bundle (frozen), it returns the directory containing the executable.
        Otherwise, it returns the directory containing the current Python script file.
        Returns:
            Path: The directory path of the executable or script.
        """

        if getattr(sys, 'frozen', False):
            # PyInstaller executable
            print("Executable path mode chosen")

            return Path(sys.executable).parent
    
        else:
            # Normal script
            print("Python script path mode chosen")

            return Path(__file__).absolute().parent


if __name__ == "__main__":

    SnesIde()
