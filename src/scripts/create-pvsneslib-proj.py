"""
SNES-IDE - create-pvsneslib-proj.py
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

from typing import Union, List, NoReturn, Optional, Tuple
from tkinter import Tk, filedialog
from pathlib import Path
from re import match
import subprocess
import shutil
import sys
import os
from platform_helpers import runGetSnesIDEHome

def get_file_path(
    title: str = "Select file",
    file_types: List[Tuple[str, str]] = [("All files", "*.*")],
    multiple: bool = False,
    directory: bool = False
) -> Union[str, List[str], Tuple[str, ...], NoReturn]:
    """
    Replaces sys.argv with a graphical file/directory selection interface.
    
    Args:
        title: Dialog window title
        file_types: List of tuples with description and extension [(desc, *.ext)]
        multiple: Whether to allow multiple file selection
        directory: Whether to select directories instead of files
    
    Returns:
        str or List[str]: Selected path(s)
        NoReturn: Exits program if user cancels or error occurs
    
    Raises:
        SystemExit: Always exits program on cancellation or error
    """
    root: Optional[Tk] = None
    
    try:
        root = Tk()
        root.withdraw()

        try:
            root.attributes('-topmost', True)  # type: ignore
        except: ...

        selected_path: Union[str, List[str], Tuple[str, ...], None] = None
        
        if directory:
            selected_path = filedialog.askdirectory(title=title)

        elif multiple:
            selected_path = filedialog.askopenfilenames(
                title=title, 
                filetypes=file_types
            )
            if selected_path:
                selected_path = list(selected_path)
        else:
            selected_path = filedialog.askopenfilename(
                title=title, 
                filetypes=file_types
            )
        
        if root:
            root.destroy()
            root = None
        
        if not selected_path or (isinstance(selected_path, list) and len(selected_path) == 0):
            print("No file/directory selected. Application terminated.", file=sys.stderr)
            sys.exit(1)
        
        if isinstance(selected_path, str) and not os.path.exists(selected_path):
            print(f"Selected path does not exist: {selected_path}", file=sys.stderr)
            sys.exit(1)
        
        return selected_path

    except Exception as e:
        if root:
            try:
                root.destroy()
            except:
                pass

        print(f"Error in file dialog: {e}", file=sys.stderr)
        sys.exit(1)


class ProjectCreator:

    def __init__(self) -> None:

        self.full_path: Path = Path(str(
            get_file_path(
                "Select the directory of your project", [("Directories", "*")],
                directory=True
            )
        ))
        self.project_name: str = self.full_path.name

    @staticmethod
    def get_executable_path() -> str:
        """Get the path of the executable or script based on whether the script is frozen 
        (PyInstaller) or not."""

        if getattr(sys, 'frozen', False):
            print("executable path mode chosen")
            return str(Path(sys.executable).parent)
        
        else:
            print("Python script path mode chosen")
            return str(Path(__file__).resolve().parent)

    def get_home_path(self) -> str:
        """Get snes-ide home directory, can raise subprocess.CalledProcessError"""
        # Use centralized platform helper which searches cwd and PATH and
        # returns a Path or raises FileNotFoundError with a helpful message.
        cwd_path: Path = Path(self.get_executable_path())
        return str(runGetSnesIDEHome(cwd=cwd_path))


    def validate(self) -> None:
        """Check class attributes given as terminal parameters"""

        if not (
            Path(self.full_path).is_dir() and 
            Path(self.full_path).exists() and 
            match(r"^[A-Za-z0-9_-]+$", self.project_name)
        ):

            print("Illegal parameter was given to create-pvsneslib-proj", file=sys.stderr)
            exit(-1)

    def run(self) -> NoReturn:
        """Run the project creation process."""

        target_path: Path = self.full_path / self.project_name

        try:
            home = Path(self.get_home_path())

            # Historically templates have lived in different locations across
            # repository layouts (root/libs, resources/libs, src/libs). Try a
            # few common candidate locations derived from the helper's output
            # and from its parents (in case the helper returns the `src/` dir
            # instead of the repository root).
            bases = [home]
            if home.parent and home.parent != home:
                bases.append(home.parent)
            if home.parent.parent and home.parent.parent not in bases:
                bases.append(home.parent.parent)

            checked = []
            template_path = None
            for base in bases:
                checked.extend([
                    base / "libs" / "pvsneslib" / "template",
                    base / "resources" / "libs" / "pvsneslib" / "template",
                    base / "src" / "libs" / "pvsneslib" / "template",
                ])
                for c in checked:
                    if c.exists():
                        template_path = c
                        break
                if template_path:
                    break

            if template_path is None:
                tried = ", ".join(str(p) for p in checked)
                raise FileNotFoundError(f"pvsneslib template not found; looked in: {tried}")

        except FileNotFoundError as e:
            # runGetSnesIDEHome or our candidate lookup failed with a clear message
            print(f"Error while locating template: {e}", file=sys.stderr)
            sys.exit(1)

        except subprocess.CalledProcessError as e:
            print(f"Error while getting path to templates: {e}", file=sys.stderr)
            sys.exit(1)

        except Exception as e:
            print(f"Unexpected error while locating templates: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            shutil.copytree(template_path, target_path)

        except Exception as e:
            print(f"Error while copying the template: {e}", file=sys.stderr)
            exit(-1)

        print("Successfully copied template to target path, exiting...")
        exit(0)


if __name__ == "__main__":

    ProjectCreator().run()
