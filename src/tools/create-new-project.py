#!/usr/bin/env python3
from pathlib import Path
from re import match
import subprocess
import sys
import argparse
import time
import json
import logging
import os
import shutil as _pyshutil

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import PathCompleter
    from prompt_toolkit.validation import Validator, ValidationError
    HAS_RICH_UI = True
except ImportError:
    HAS_RICH_UI = False
    print("Warning: rich or prompt_toolkit not installed. Using basic CLI interface.")

# Initialize rich console if available
console = Console() if HAS_RICH_UI else None


class CustomShutil:
    """Cross-platform shutil wrapper for the small tools.

    Previously this module invoked Windows-specific shell commands (copy, xcopy,
    rmdir, move) which fails on POSIX. Use the Python stdlib implementations so
    the same tool works when run on macOS or Linux.
    """

    @staticmethod
    def copy(src: str | Path, dst: str | Path) -> None:
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        dst_parent = dst.parent
        dst_parent.mkdir(parents=True, exist_ok=True)
        _pyshutil.copy2(str(src), str(dst))

    @staticmethod
    def copytree(src: str | Path, dst: str | Path, callback=None) -> None:
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        
        # Count files for progress bar
        if callback:
            file_count = sum(1 for _ in Path(src).rglob('*') if _.is_file())
            copied_files = 0
        
        try:
            if callback:
                # Manual copy with progress tracking
                Path(dst).mkdir(parents=True, exist_ok=True)
                for p in Path(src).rglob('*'):
                    rel = p.relative_to(src)
                    dest = Path(dst) / rel
                    if p.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        _pyshutil.copy2(str(p), str(dest))
                        copied_files += 1
                        callback(copied_files, file_count)
            else:
                # Standard copy without progress tracking
                try:
                    _pyshutil.copytree(str(src), str(dst), dirs_exist_ok=True)
                except TypeError:
                    # Fallback for older Python versions
                    Path(dst).mkdir(parents=True, exist_ok=True)
                    for p in Path(src).rglob('*'):
                        rel = p.relative_to(src)
                        dest = Path(dst) / rel
                        if p.is_dir():
                            dest.mkdir(parents=True, exist_ok=True)
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            _pyshutil.copy2(str(p), str(dest))
        except Exception as e:
            raise Exception(f"Error copying files: {e}")

    @staticmethod
    def rmtree(path: str | Path) -> None:
        p = Path(path).resolve()
        if p.exists():
            _pyshutil.rmtree(str(p))

    @staticmethod
    def move(src: str | Path, dst: str | Path) -> None:
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        _pyshutil.move(str(src), str(dst))


class ProjectNameValidator(Validator):
    def validate(self, document):
        text = document.text
        if not text:
            raise ValidationError(message="Project name cannot be empty")
            
        if not match(r"^[A-Za-z0-9_-]+$", text):
            raise ValidationError(
                message="Invalid project name. Please use only alphanumeric characters, underscores, or hyphens."
            )


class ParentPathValidator(Validator):
    def validate(self, document):
        text = document.text
        if not text:
            raise ValidationError(message="Path cannot be empty")
            
        # Handle ~ for home directory on Unix-like systems
        if text.startswith('~') and (sys.platform == 'darwin' or sys.platform.startswith('linux')):
            text = os.path.expanduser(text)
            
        try:
            path_obj = Path(text).expanduser().resolve()
            
            # Check if path exists
            if not path_obj.exists():
                raise ValidationError(message=f"The path does not exist: {path_obj}")
                
            # Check if path is a directory
            if not path_obj.is_dir():
                raise ValidationError(message=f"The path is not a directory: {path_obj}")
                
            # Check if we have write permission
            try:
                # Try to create a temporary file to test write permissions
                test_file = path_obj / f".write_test_{time.time()}"
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError) as e:
                raise ValidationError(message=f"Cannot write to directory {path_obj}: {e}")
                
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(message=f"Error validating path: {e}")


class ProjectCreator:
    def __init__(self, debug=False, debug_log=None):
        """Initialize the project creator with user input for project name and path."""
        self.debug = debug
        self.debug_log = debug_log
        self.logger = self._setup_logging()
        
        self.project_name = None
        self.full_path = None
        
        self.logger.debug("ProjectCreator initialized with debug=%s, debug_log=%s", debug, debug_log)

    def log_debug(self, message, *args):
        """Log debug message if debug mode is enabled."""
        if self.debug:
            if HAS_RICH_UI:
                console.print(f"[dim][DEBUG][/dim] {message % args}")
            else:
                print(f"DEBUG: {message % args}")
        self.logger.debug(message, *args)

    def _setup_logging(self):
        """Set up logging configuration."""
        logger = logging.getLogger('create-new-project')
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
        
        # Add file handler if debug_log is specified
        if self.debug_log:
            try:
                file_handler = logging.FileHandler(self.debug_log)
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                logger.debug(f"Logging to file: {self.debug_log}")
            except Exception as e:
                logger.error(f"Failed to set up file logging to {self.debug_log}: {e}")
        
        return logger

    def show_welcome(self):
        """Display a welcome message with improved formatting."""
        if HAS_RICH_UI:
            console.print(Panel.fit(
                "[bold yellow]Welcome to the SNES-IDE project creator![/bold yellow]\n\n"
                "This tool will help you create a new SNES-IDE project.\n"
                "Please follow the instructions below to create your project.",
                border_style="green",
                padding=(1, 2),
                title="[bold blue]SNES-IDE[/bold blue]"
            ))
        else:
            print("**Welcome to the SNES-IDE project creator!**")
            print("This tool will help you create a new SNES-IDE project.")
            print("Please follow the instructions below to create your project.\n")

    def prompt_for_input(self):
        """Prompt the user for project name and path with improved UI."""
        self.show_welcome()
        
        # Get project name
        if HAS_RICH_UI:
            console.print("[bold]Project Name:[/bold]")
            console.print("[dim]Please enter a name using only alphanumeric characters, underscores, or hyphens.[/dim]")
            self.project_name = prompt(
                "\n> ", 
                validator=ProjectNameValidator()
            )
            
            # Get project path
            console.print("\n[bold]Project Path:[/bold]")
            if sys.platform == 'darwin' or sys.platform.startswith('linux'):
                console.print("[dim]Please enter the full path where you want to create the project.[/dim]")
                console.print("[dim]Example: ~/Projects or /Users/username/Documents[/dim]")
            else:
                console.print("[dim]Please enter the full path where you want to create the project.[/dim]")
                console.print("[dim]Example: C:\\Projects or D:\\Development[/dim]")
                
            path_completer = PathCompleter(only_directories=True)
            user_input = prompt(
                "\n> ", 
                completer=path_completer,
                validator=ParentPathValidator(),
                complete_while_typing=True
            )
        else:
            # Fallback to standard input
            print("Write down the name of your new project:\n")
            self.project_name = input()

            if sys.platform == 'darwin' or sys.platform.startswith('linux'):
                print("Write down the full path of the folder you want to create a project: \n(Use /path/to/folder format)\n\n")
            else:
                print("Write down the Full path of the folder you want to create a project: \n(Use C:\\\\foo\\\\theFolder structure)\n\n")
                
            user_input = input()
            
        self.full_path = self.normalize_path(user_input)
        
        self.log_debug("Project name: %s", self.project_name)
        self.log_debug("Full path (normalized): %s", self.full_path)

    def normalize_path(self, path_str):
        """Normalize a path string to the appropriate platform format."""
        try:
            # Handle ~ for home directory on Unix-like systems
            if path_str.startswith('~') and (sys.platform == 'darwin' or sys.platform.startswith('linux')):
                path_str = os.path.expanduser(path_str)
                self.log_debug("Expanded home directory: %s", path_str)
            
            # Convert to Path object to normalize
            normalized_path = Path(path_str).expanduser().resolve()
            self.log_debug("Normalized path: %s", normalized_path)
            return normalized_path
        except Exception as e:
            self.logger.error("Error normalizing path: %s", e)
            return Path(path_str)  # Return original as Path object
            
    def validate_project_name(self, name):
        """Validate the project name according to rules."""
        if not name or not isinstance(name, str):
            return False, "Project name cannot be empty"
            
        if not match(r"^[A-Za-z0-9_-]+$", name):
            return False, "Invalid project name. Please use only alphanumeric characters, underscores, or hyphens."
            
        return True, "Valid project name"

    def validate_parent_path(self, path):
        """Validate that the parent path exists and is a directory."""
        if not path:
            return False, "Path cannot be empty"
            
        path_obj = Path(path)
        
        # Check if path exists
        if not path_obj.exists():
            return False, f"The path does not exist: {path_obj}"
            
        # Check if path is a directory
        if not path_obj.is_dir():
            return False, f"The path is not a directory: {path_obj}"
            
        # Check if we have write permission
        try:
            # Try to create a temporary file to test write permissions
            test_file = path_obj / f".write_test_{time.time()}"
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            return False, f"Cannot write to directory {path_obj}: {e}"
            
        return True, "Valid parent directory"

    def validate_target_path(self, parent, name):
        """Validate that the target project path doesn't already exist or collide with something."""
        target = Path(parent) / name
        
        if target.exists():
            return False, f"Target project directory already exists: {target}"
            
        return True, "Valid target path"

    @staticmethod
    def get_executable_path():
        """Get the path of the executable or script based on whether the script is frozen (PyInstaller) or not."""
        if getattr(sys, 'frozen', False):
            # PyInstaller executable
            exe_path = Path(sys.executable).parent
            if HAS_RICH_UI:
                console.print(f"[dim]Executable path mode: {exe_path}[/dim]")
            else:
                print(f"Executable path mode: {exe_path}")
            return exe_path
        else:
            # Normal script
            script_path = Path(__file__).resolve().parent
            if HAS_RICH_UI:
                console.print(f"[dim]Python script path mode: {script_path}[/dim]")
            else:
                print(f"Python script path mode: {script_path}")
            return script_path

    def find_template_path(self):
        """Find the template path, trying multiple possible locations."""
        exe_path = self.get_executable_path()
        
        # Try multiple possible template locations
        template_candidates = [
            exe_path / ".." / "libs" / "template",  # Relative to executable/script
            Path(__file__).resolve().parent / ".." / "libs" / "template",  # Relative to this script
            Path(__file__).resolve().parent.parent.parent / "libs" / "template",  # From project root
        ]
        
        # Add platform-specific paths for macOS app bundle or Unix installation
        if sys.platform == 'darwin':
            # Check for macOS app bundle resources
            template_candidates.append(Path(exe_path) / "../Resources/libs/template")
            
        if sys.platform == 'darwin' or sys.platform.startswith('linux'):
            # Common Unix-like install locations
            template_candidates.extend([
                Path("/usr/local/share/snes-ide/libs/template"),
                Path("/usr/share/snes-ide/libs/template"),
                Path(os.path.expanduser("~/.local/share/snes-ide/libs/template"))
            ])
        
        for candidate in template_candidates:
            try:
                resolved = candidate.resolve()
                self.log_debug("Checking template candidate: %s", resolved)
                if resolved.exists() and resolved.is_dir():
                    self.log_debug("Found template path: %s", resolved)
                    return resolved
            except Exception as e:
                self.log_debug("Error resolving path %s: %s", candidate, e)
        
        # If we get here, we couldn't find the template
        self.logger.error("Could not find template path. Tried: %s", 
                         ", ".join(str(p) for p in template_candidates))
        return None

    def copy_with_progress(self, src_path, dst_path):
        """Copy files with a progress indicator."""
        if HAS_RICH_UI:
            with Progress(
                SpinnerColumn(),
                "[progress.description]{task.description}",
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%",
                "[progress.completed]{task.completed} of {task.total} files",
                console=console
            ) as progress:
                task = progress.add_task("[green]Copying files...", total=100)
                
                def update_progress(current, total):
                    progress.update(task, completed=current, total=total, 
                                   description=f"[green]Copying files ({current}/{total})")
                    
                CustomShutil.copytree(src_path, dst_path, callback=update_progress)
        else:
            print("Copying files...")
            CustomShutil.copytree(src_path, dst_path)
            print("Copy complete!")

    def run(self):
        """Run the project creation process."""
        if not self.project_name or not self.full_path:
            self.prompt_for_input()

        # Validate project name
        name_valid, name_msg = self.validate_project_name(self.project_name)
        if not name_valid:
            self.logger.error(name_msg)
            if HAS_RICH_UI:
                console.print(f"[bold red]Error:[/bold red] {name_msg}")
                console.print("\nPress Enter to exit...")
            else:
                print(name_msg)
                print("\nPress any key to exit...")
            input()
            return 1

        # Validate parent path
        path_valid, path_msg = self.validate_parent_path(self.full_path)
        if not path_valid:
            self.logger.error(path_msg)
            if HAS_RICH_UI:
                console.print(f"[bold red]Error:[/bold red] {path_msg}")
                console.print("\nPress Enter to exit...")
            else:
                print(path_msg)
                print("\nPress any key to exit...")
            input()
            return 1
        
        # Validate target path (doesn't already exist)
        target_valid, target_msg = self.validate_target_path(self.full_path, self.project_name)
        if not target_valid:
            self.logger.error(target_msg)
            if HAS_RICH_UI:
                console.print(f"[bold red]Error:[/bold red] {target_msg}")
                console.print("\nPress Enter to exit...")
            else:
                print(target_msg)
                print("\nPress any key to exit...")
            input()
            return 1

        # All validation passed
        self.log_debug("All validation passed")
        target_path = Path(self.full_path) / self.project_name
        self.log_debug("Target project path: %s", target_path)
        
        template_path = self.find_template_path()
        
        if not template_path:
            if HAS_RICH_UI:
                console.print("[bold red]Error:[/bold red] Could not find template directory.")
                console.print("\nPress Enter to exit...")
            else:
                print("Error: Could not find template directory.")
                print("\nPress any key to exit...")
            input()
            return 1
        
        self.log_debug("Copying from template: %s", template_path)
        self.log_debug("Copying to target: %s", target_path)
        
        try:
            self.copy_with_progress(template_path, target_path)
            if HAS_RICH_UI:
                console.print("\n[bold green]Project created successfully! ✓[/bold green]")
                console.print(f"Location: [bold]{target_path}[/bold]")
                console.print("\nPress Enter to exit...")
            else:
                print(f"\nProject created successfully at: {target_path}")
                print("\nPress any key to exit...")
            input()
            return 0
        except Exception as e:
            self.logger.error("Error during project creation: %s", e)
            if HAS_RICH_UI:
                console.print(f"[bold red]Error:[/bold red] {e}")
                console.print("\nPress Enter to exit...")
            else:
                print(f"Error creating project: {e}")
                print("\nPress any key to exit...")
            input()
            return 1


def _write_log(log_path: str, payload: dict) -> None:
    try:
        with open(log_path, 'w') as lf:
            json.dump(payload, lf, indent=2)
    except Exception:
        # best-effort logging; do not raise
        pass


def headless_create(name: str, parent: str, debug: bool = False, debug_log: str = None, log_file: str | None = None) -> int:
    """Create a project non-interactively for CI or automation.

    Returns 0 on success, non-zero on failure. Writes a JSON log file if
    log_file is provided or writes to /tmp by default.
    """
    creator = ProjectCreator(debug=debug, debug_log=debug_log)
    creator.log_debug("Starting headless project creation")
    
    ts = int(time.time())
    if not log_file:
        log_dir = "/tmp" if sys.platform != "win32" else os.environ.get("TEMP", "C:/Temp")
        log_file = f"{log_dir}/create-new-project-ci-{ts}.log"

    entry = {
        'timestamp': ts,
        'action': 'create-new-project',
        'name': name,
        'parent': parent,
        'status': 'failed',
        'message': '',
        'created_path': None
    }

    # Normalize the parent path
    parent_path = creator.normalize_path(parent)
    creator.log_debug("Normalized parent path: %s", parent_path)

    # Validate project name
    name_valid, name_msg = creator.validate_project_name(name)
    if not name_valid:
        creator.logger.error(name_msg)
        entry['message'] = name_msg
        _write_log(log_file, entry)
        print(entry['message'], file=sys.stderr)
        return 2

    # Validate parent path
    path_valid, path_msg = creator.validate_parent_path(parent_path)
    if not path_valid:
        creator.logger.error(path_msg)
        entry['message'] = path_msg
        _write_log(log_file, entry)
        print(entry['message'], file=sys.stderr)
        return 3
        
    # Validate target path (doesn't already exist)
    target_valid, target_msg = creator.validate_target_path(parent_path, name)
    if not target_valid:
        creator.logger.error(target_msg)
        entry['message'] = target_msg
        _write_log(log_file, entry)
        print(entry['message'], file=sys.stderr)
        return 4

    target_path = parent_path / name
    creator.log_debug("Target project path: %s", target_path)
    
    try:
        # Set properties needed for find_template_path
        creator.project_name = name
        creator.full_path = parent_path
        
        template_path = creator.find_template_path()
        
        if not template_path:
            msg = "Could not find template directory"
            creator.logger.error(msg)
            entry['message'] = msg
            _write_log(log_file, entry)
            print(entry['message'], file=sys.stderr)
            return 4
            
        creator.log_debug("Found template path: %s", template_path)
        
        # Copy template files (with progress bar if running in Rich mode)
        creator.copy_with_progress(template_path, target_path)
        
        entry['status'] = 'ok'
        entry['message'] = 'Project created successfully.'
        entry['created_path'] = str(target_path)
        _write_log(log_file, entry)
        print(entry['message'])
        return 0
    except Exception as e:
        msg = f'Exception during project creation: {e}'
        creator.logger.error(msg)
        entry['message'] = msg
        _write_log(log_file, entry)
        print(entry['message'], file=sys.stderr)
        return 5


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a new SNES-IDE project (interactive or headless).')
    parser.add_argument('--name', '-n', help='Project name (alphanumeric, underscore, hyphen)')
    parser.add_argument('--parent', '-p', help='Parent folder where project will be created')
    parser.add_argument('--headless', action='store_true', help='Run in non-interactive headless/CI mode')
    parser.add_argument('--ci', action='store_true', help='Alias for --headless')
    parser.add_argument('--log', help='Path to write a JSON log file when running in headless mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--debug-log', help='Path to write debug log JSON')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')

    args = parser.parse_args()

    # Disable colored output if requested
    if args.no_color and HAS_RICH_UI and console:
        console.no_color = True

    if args.headless or args.ci:
        if not args.name or not args.parent:
            print('Error: --name and --parent are required in headless mode', file=sys.stderr)
            sys.exit(1)
        rc = headless_create(args.name, args.parent, debug=args.debug, debug_log=args.debug_log, log_file=args.log)
        sys.exit(rc)
    else:
        # Interactive mode: preserve original behavior
        try:
            creator = ProjectCreator(debug=args.debug, debug_log=args.debug_log)
            sys.exit(creator.run())
        except EOFError:
            # If interactive input is not available, provide a helpful message
            if HAS_RICH_UI:
                console.print("[bold red]Error:[/bold red] Interactive input not available.")
                console.print("Use --headless with --name and --parent for automation.")
            else:
                print('Interactive input not available. Use --headless with --name and --parent for automation.', file=sys.stderr)
            sys.exit(1)