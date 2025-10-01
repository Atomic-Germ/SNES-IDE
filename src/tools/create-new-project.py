from pathlib import Path
from re import match
from os import path
import subprocess
import sys
import argparse
import time
import json

class shutil:
    """Cross-platform shutil wrapper for the small tools.

    Previously this module invoked Windows-specific shell commands (copy, xcopy,
    rmdir, move) which fails on POSIX. Use the Python stdlib implementations so
    the same tool works when run on macOS or Linux.
    """

    @staticmethod
    def copy(src: str | Path, dst: str | Path) -> None:
        import shutil as _pyshutil
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        dst_parent = Path(dst).parent
        dst_parent.mkdir(parents=True, exist_ok=True)
        _pyshutil.copy2(str(src), str(dst))

    @staticmethod
    def copytree(src: str | Path, dst: str | Path) -> None:
        import shutil as _pyshutil
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
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

    @staticmethod
    def rmtree(path: str | Path) -> None:
        import shutil as _pyshutil
        p = Path(path).resolve()
        if p.exists():
            _pyshutil.rmtree(str(p))

    @staticmethod
    def move(src: str | Path, dst: str | Path) -> None:
        import shutil as _pyshutil
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        _pyshutil.move(str(src), str(dst))

class ProjectCreator:

    def __init__(self):
        """Initialize the project creator with user input for project name and path."""

        print("**Welcome to the SNES-IDE project creator!**")
        print("This tool will help you create a new SNES-IDE project.")
        print("Please follow the instructions below to create your project.\n")

        print("Write down the name of your new project:\n")
        self.project_name = input()

        print("Write down the Full path of the folder you want to create a project: \n(Use C:\\\\foo\\\\theFolder structure)\n\n")
        self.full_path = input()

    
    @staticmethod
    def get_executable_path():
        """Get the path of the executable or script based on whether the script is frozen (PyInstaller) or not."""

        if getattr(sys, 'frozen', False):
            # PyInstaller executable
            print("executable path mode chosen")

            return str(path.dirname(sys.executable))
        
        else:
            # Normal script
            print("Python script path mode chosen")

            return str(path.dirname(path.abspath(__file__)))


    def run(self):
        """Run the project creation process."""

        # Check if the specified path exists
        if path.isdir(self.full_path):

            if match(r"^[A-Za-z0-9_-]+$", self.project_name):

                target_path = path.join(self.full_path, self.project_name)
                template_path = path.abspath(path.join(self.get_executable_path(), "..", "libs", "template"))

                shutil.copytree(template_path, target_path)

                input("Project created successfully! Press any key to exit...")

            else:

                input("Invalid project name. Please use alphanumeric characters, underscores, or hyphens. Press any key to exit...")

        else:

            input("The specified path does not exist. Press any key to exit...")


def _write_log(log_path: str, payload: dict) -> None:
    try:
        with open(log_path, 'w') as lf:
            json.dump(payload, lf, indent=2)
    except Exception:
        # best-effort logging; do not raise
        pass


def headless_create(name: str, parent: str, log_file: str | None = None) -> int:
    """Create a project non-interactively for CI or automation.

    Returns 0 on success, non-zero on failure. Writes a JSON log file if
    log_file is provided or writes to /tmp by default.
    """
    ts = int(time.time())
    if not log_file:
        log_file = f"/tmp/create-new-project-ci-{ts}.log"

    entry = {
        'timestamp': ts,
        'action': 'create-new-project',
        'name': name,
        'parent': parent,
        'status': 'failed',
        'message': '',
        'created_path': None
    }

    if not path.isdir(parent):
        entry['message'] = f"Parent path does not exist: {parent}"
        _write_log(log_file, entry)
        print(entry['message'], file=sys.stderr)
        return 2

    if not match(r"^[A-Za-z0-9_-]+$", name):
        entry['message'] = "Invalid project name. Only alphanumeric, underscore and hyphen allowed."
        _write_log(log_file, entry)
        print(entry['message'], file=sys.stderr)
        return 3

    target_path = path.join(parent, name)
    try:
        template_path = path.abspath(path.join(Path(__file__).resolve().parent, '..', 'libs', 'template'))
        shutil.copytree(template_path, target_path)
        entry['status'] = 'ok'
        entry['message'] = 'Project created successfully.'
        entry['created_path'] = target_path
        _write_log(log_file, entry)
        print(entry['message'])
        return 0
    except Exception as e:
        entry['message'] = f'Exception during project creation: {e}'
        _write_log(log_file, entry)
        print(entry['message'], file=sys.stderr)
        return 4


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a new SNES-IDE project (interactive or headless).')
    parser.add_argument('--name', '-n', help='Project name (alphanumeric, underscore, hyphen)')
    parser.add_argument('--parent', '-p', help='Parent folder where project will be created')
    parser.add_argument('--headless', action='store_true', help='Run in non-interactive headless/CI mode')
    parser.add_argument('--ci', action='store_true', help='Alias for --headless')
    parser.add_argument('--log', help='Path to write a JSON log file when running in headless mode')

    args = parser.parse_args()

    if args.headless or args.ci:
        if not args.name or not args.parent:
            print('Error: --name and --parent are required in headless mode', file=sys.stderr)
            sys.exit(1)
        rc = headless_create(args.name, args.parent, args.log)
        sys.exit(rc)
    else:
        # Interactive mode: preserve original behavior
        try:
            ProjectCreator().run()
        except EOFError:
            # If interactive input is not available, provide a helpful message
            print('Interactive input not available. Use --headless with --name and --parent for automation.', file=sys.stderr)
            sys.exit(1)
