"""
SNES-IDE - snes-ide.py
Copyright (C) 2025 BrunoRNS

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import sys
from typing_extensions import NoReturn
from pathlib import Path

# Import utilities  
from path_utils import path_manager
from subprocess_utils import subprocess_manager
from platform_utils import platform_manager

# GUI imports (only imported when needed)
try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtCore import QObject, Slot, Signal
    from PySide6.QtWebChannel import QWebChannel
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# Version information
__version__ = "1.0.0"
__author__ = "BrunoRNS"

class CLIRunner:
    """
    Command-line interface runner for executing SNES-IDE operations headlessly.
    """
    
    def __init__(self) -> None:
        """Initialize the CLI runner with script discovery."""
        self.scripts_dir = path_manager.executable_dir / "scripts"
        self.scripts = self._discover_scripts()
        
    def _discover_scripts(self) -> dict:
        """Discover available scripts and categorize them."""
        scripts = {
            'audio': [],
            'graphics': [],
            'build': [],
            'project': [],
            'utility': []
        }
        
        if not self.scripts_dir.exists():
            return scripts
        
        # Check if we're in a compiled/built environment (executables) or source environment (.py files)
        if path_manager.is_frozen:
            # Look for compiled executables (no extension)
            script_files = [f for f in self.scripts_dir.iterdir() 
                          if f.is_file() and not f.name.startswith('.') 
                          and not f.suffix and f.name != 'readme.md'
                          and f.name != '__pycache__']
        else:
            # Look for Python source files
            script_files = list(self.scripts_dir.glob("*.py"))
            
        for script_file in script_files:
            script_name = script_file.stem if not path_manager.is_frozen else script_file.name
            
            if script_name.startswith('audio-'):
                scripts['audio'].append(script_name)
            elif script_name.startswith('gfx-'):
                scripts['graphics'].append(script_name)
            elif script_name.startswith('compile-'):
                scripts['build'].append(script_name)
            elif script_name.startswith('create-'):
                scripts['project'].append(script_name)
            else:
                scripts['utility'].append(script_name)
                
        return scripts
        
    def list_scripts(self, category: str = None) -> None:
        """List available scripts, optionally filtered by category."""
        print("Available SNES-IDE Scripts:")
        print("=" * 50)
        
        if category and category in self.scripts:
            scripts_to_show = {category: self.scripts[category]}
        else:
            scripts_to_show = self.scripts
            
        for cat_name, script_list in scripts_to_show.items():
            if not script_list:
                continue
                
            print(f"\n{cat_name.title()} Scripts:")
            for script in sorted(script_list):
                print(f"  - {script}")
                
    def run_script(self, script_name: str, args: list = None) -> int:
        """Execute a script with optional arguments."""
        if path_manager.is_frozen:
            # In compiled environment, scripts are compiled executables  
            script_path = self.scripts_dir / script_name
        else:
            # In source environment, scripts are .py files
            script_path = self.scripts_dir / f"{script_name}.py"
        
        if not script_path.exists():
            print(f"Error: Script '{script_name}' not found.", file=sys.stderr)
            print(f"Available scripts in {script_path.parent}:", file=sys.stderr)
            
            # List available scripts based on environment
            if path_manager.is_frozen:
                for script_file in script_path.parent.iterdir():
                    if (script_file.is_file() and not script_file.name.startswith('.') 
                        and not script_file.suffix and script_file.name != 'readme.md'):
                        print(f"  - {script_file.name}", file=sys.stderr)
            else:
                for script_file in script_path.parent.glob("*.py"):
                    print(f"  - {script_file.stem}", file=sys.stderr)
            return 1
            
        try:
            print(f"Executing: {script_name}")
            if args:
                print(f"Arguments: {' '.join(args)}")
                
            if path_manager.is_frozen:
                # Execute compiled executable directly
                cmd_args = [str(script_path)]
                if args:
                    cmd_args.extend(args)
                    
                result = subprocess_manager.run_external_executable(
                    str(script_path),
                    args=args if args else [],
                    cwd=self.scripts_dir,
                    capture_output=False  # Show output in real-time
                )
            else:
                # Execute Python script with interpreter
                cmd_args = [str(script_path)]
                if args:
                    cmd_args.extend(args)
                    
                result = subprocess_manager.run_external_executable(
                    sys.executable,
                    args=cmd_args,
                    cwd=self.scripts_dir,
                    capture_output=False  # Show output in real-time
                )
            
            if result.success:
                print(f"Script '{script_name}' completed successfully.")
                return 0
            else:
                print(f"Script '{script_name}' failed with return code {result.returncode}.", file=sys.stderr)
                return result.returncode
                
        except Exception as e:
            print(f"Error executing script '{script_name}': {e}", file=sys.stderr)
            return 1
            
    def get_script_info(self, script_name: str) -> None:
        """Get information about a specific script."""
        if path_manager.is_frozen:
            script_path = self.scripts_dir / script_name
        else:
            script_path = self.scripts_dir / f"{script_name}.py"
        
        if not script_path.exists():
            print(f"Error: Script '{script_name}' not found.", file=sys.stderr)
            return
            
        try:
            print(f"Script Information: {script_name}")
            print("=" * 50)
            print(f"Path: {script_path}")
            print(f"Size: {script_path.stat().st_size} bytes")
            
            if path_manager.is_frozen:
                print("Type: Compiled executable")
                print("Note: Source code not available in compiled version")
            else:
                print("Type: Python source file")
                
                # Extract docstring if available for source files
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                lines = content.split('\n')
                in_docstring = False
                docstring_lines = []
                
                for line in lines:
                    if line.strip().startswith('"""') or line.strip().startswith("'''"):
                        if in_docstring:
                            break
                        in_docstring = True
                        continue
                    elif in_docstring:
                        docstring_lines.append(line.strip())
                        
                if docstring_lines:
                    print("\nDescription:")
                    for line in docstring_lines[:5]:  # First 5 lines
                        print(f"  {line}")
                    
        except Exception as e:
            print(f"Error reading script info: {e}", file=sys.stderr)


class ScriptRunner(QObject):
    """
    Script runner for GUI mode - handles script execution from web interface.
    """
    
    scriptExecuted: Signal = Signal(str, str)
    
    def __init__(self) -> None:
        """
        Initializes the ScriptRunner object.

        Sets the path of the scripts directory to the directory containing the
        executable or script, depending on whether the script is frozen (PyInstaller)
        or not.

        :return: None
        """
        
        super().__init__()
        self.scripts_dir: Path = path_manager.executable_dir / "scripts"

    @Slot(str)
    def run_script(self, script_name: str) -> None:
        """Execute a script from the scripts directory"""
        
        try:
            # Remove .py extension if present (for backwards compatibility with HTML)
            if script_name.endswith('.py'):
                script_name = script_name[:-3]
                
            # Use same dual-mode logic as CLIRunner
            if path_manager.is_frozen:
                # In compiled environment, scripts are compiled executables  
                script_path = self.scripts_dir / script_name
                
                if script_path.exists():
                    # Execute compiled executable directly
                    result = subprocess_manager.run_external_executable(
                        str(script_path),
                        args=[],
                        cwd=self.scripts_dir,
                        capture_output=True
                    )
                else:
                    self.scriptExecuted.emit(script_name, f"Script not found: {script_path}")
                    return
            else:
                # In source environment, scripts are .py files
                script_path = self.scripts_dir / f"{script_name}.py"
                
                if script_path.exists():
                    # Execute Python script with interpreter
                    result = subprocess_manager.run_external_executable(
                        sys.executable,
                        args=[str(script_path)],
                        cwd=self.scripts_dir,
                        capture_output=True
                    )
                else:
                    self.scriptExecuted.emit(script_name, f"Script not found: {script_path}")
                    return
                    
            if result.success:
                self.scriptExecuted.emit(script_name, "Script executed successfully!")
            else:
                self.scriptExecuted.emit(script_name, f"Error: {result.stderr}")

        except Exception as e:
            self.scriptExecuted.emit(script_name, f"Exception: {str(e)}")
            
    @Slot(str)
    def runScript(self, scriptName: str) -> None:
        """
        Execute a Python script from the scripts directory.

        This slot is connected to the run_script method which takes a script name
        as a parameter and executes it using the subprocess module.

        :param scriptName: The name of the script to execute.
        :return: None
        """
        
        self.run_script(scriptName)

class MainWindow(QMainWindow):
    
    def __init__(self) -> None:
        """
        Initializes the main window of the SNES IDE.

        Sets the window title to "SNES IDE - Super Nintendo Development Environment",
        sets the window size to 1200x800, and sets the layout to a vertical box layout.
        Creates a QWebEngineView and sets it as the central widget of the main window.
        Creates a QWebChannel and registers a ScriptRunner object with it.
        Loads the index.html file from the assets directory into the QWebEngineView.
        """
        
        super().__init__()
        self.setWindowTitle("SNES IDE - Super Nintendo Development Environment")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget: QWidget = QWidget()
        self.setCentralWidget(central_widget)
        layout: QVBoxLayout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view: QWebEngineView = QWebEngineView()
        
        self.channel: QWebChannel = QWebChannel()
        self.script_runner: ScriptRunner = ScriptRunner()
        self.channel.registerObject("scriptRunner", self.script_runner)
        self.web_view.page().setWebChannel(self.channel)
        
        html_path: Path = path_manager.executable_dir / "assets" / "index.html"
        self.web_view.load(f"file:///{html_path.resolve()}")
        
        layout.addWidget(self.web_view)

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for CLI operations."""
    parser = argparse.ArgumentParser(
        description="SNES-IDE - Super Nintendo Entertainment System Development Environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  snes-ide                                    # Start GUI mode
  snes-ide --version                          # Show version information
  snes-ide --list-scripts                     # List all available scripts
  snes-ide --list-scripts audio               # List audio scripts only
  snes-ide --run audio-wav-brr-converter      # Run audio converter
  snes-ide --run create-pvsneslib-proj -- --help  # Run project creator with help
  snes-ide --info create-pvsneslib-proj       # Get script information
  snes-ide --system-info                      # Show system information

Script Categories:
  audio      - Audio processing and conversion tools
  graphics   - Graphics and image processing tools  
  build      - Project compilation and build tools
  project    - Project creation and setup tools
  utility    - General utility and helper tools
        """
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f"SNES-IDE v{__version__} by {__author__}"
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Force headless mode (no GUI) even without other CLI arguments'
    )
    
    parser.add_argument(
        '--list-scripts', '-l',
        nargs='?',
        const='all',
        metavar='CATEGORY',
        help='List available scripts (optionally filter by category: audio, graphics, build, project, utility)'
    )
    
    parser.add_argument(
        '--run', '-r',
        metavar='SCRIPT_NAME',
        help='Run a specific script in headless mode'
    )
    
    parser.add_argument(
        '--info', '-i',
        metavar='SCRIPT_NAME', 
        help='Show information about a specific script'
    )
    
    parser.add_argument(
        '--system-info', '-s',
        action='store_true',
        help='Display system and environment information'
    )
    
    parser.add_argument(
        'script_args',
        nargs='*',
        help='Arguments to pass to the script (use -- to separate from SNES-IDE args)'
    )
    
    return parser


def print_system_info() -> None:
    """Print system and environment information."""
    print("SNES-IDE System Information")
    print("=" * 40)
    print(f"Version: {__version__}")
    print(f"Author: {__author__}")
    print(f"Platform: {platform_manager.current_platform.value}")
    print(f"Python: {sys.version}")
    print(f"Executable Dir: {path_manager.executable_dir}")
    print(f"Project Root: {path_manager.project_root}")
    print(f"Is Frozen: {path_manager.is_frozen}")
    
    # Check for GUI availability
    print(f"GUI Available: {GUI_AVAILABLE}")
    if GUI_AVAILABLE:
        try:
            app = QApplication.instance()
            if app is None:
                print("GUI Framework: PySide6 (available)")
            else:
                print("GUI Framework: PySide6 (active)")
        except Exception as e:
            print(f"GUI Framework: PySide6 (error: {e})")
    
    # Check scripts directory
    scripts_dir = path_manager.executable_dir / "scripts"
    if scripts_dir.exists():
        # Use same logic as CLIRunner to count scripts consistently  
        if path_manager.is_frozen:
            # Count compiled executables (no extension)
            script_files = [f for f in scripts_dir.iterdir() 
                          if f.is_file() and not f.name.startswith('.') 
                          and not f.suffix and f.name != 'readme.md'
                          and f.name != '__pycache__']
        else:
            # Count Python source files
            script_files = list(scripts_dir.glob("*.py"))
        script_count = len(script_files)
        print(f"Scripts Available: {script_count}")
    else:
        print("Scripts Available: None (directory not found)")


def run_cli_mode(args: argparse.Namespace) -> int:
    """Run SNES-IDE in CLI/headless mode."""
    runner = CLIRunner()
    
    if args.system_info:
        print_system_info()
        return 0
        
    if args.list_scripts:
        category = None if args.list_scripts == 'all' else args.list_scripts
        runner.list_scripts(category)
        return 0
        
    if args.info:
        runner.get_script_info(args.info)
        return 0
        
    if args.run:
        return runner.run_script(args.run, args.script_args)
        
    if args.headless:
        print("SNES-IDE running in headless mode. Use --help for available commands.")
        return 0
        
    # Should not reach here in normal operation
    print("No CLI operation specified. Use --help for available commands.")
    return 1


def run_gui_mode() -> NoReturn:
    """Run SNES-IDE in GUI mode."""
    if not GUI_AVAILABLE:
        print("Error: GUI libraries (PySide6) not available.", file=sys.stderr)
        print("Install PySide6 to use GUI mode, or use CLI options for headless operation.", file=sys.stderr)
        sys.exit(1)
        
    app: QApplication = QApplication(sys.argv)
    
    try:
        app.setStyle('Fusion')  # type: ignore
    except:
        pass
        
    window: MainWindow = MainWindow()
    window.show()
    
    sys.exit(app.exec())


def main() -> NoReturn:
    """
    Main entry point of the application.
    
    Parses command line arguments and determines whether to run in GUI mode
    or CLI mode. GUI mode is the default when no CLI arguments are provided.
    """
    parser = create_argument_parser()
    
    # Check if any CLI arguments are provided
    if len(sys.argv) == 1:
        # No arguments provided - start GUI mode
        run_gui_mode()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run in CLI mode
    exit_code = run_cli_mode(args)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
