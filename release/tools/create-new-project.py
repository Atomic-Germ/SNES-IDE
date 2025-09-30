from pathlib import Path
from re import match
from os import path
import subprocess
import sys

class shutil:
    """Cross-platform shutil wrapper for the release copy of create-new-project."""

    @staticmethod
    def copy(src: str | Path, dst: str | Path) -> None:
        import shutil as _pyshutil
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        _pyshutil.copy2(str(src), str(dst))

    @staticmethod
    def copytree(src: str | Path, dst: str | Path) -> None:
        import shutil as _pyshutil
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        try:
            _pyshutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        except TypeError:
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


if __name__ == "__main__":

    ProjectCreator().run()
