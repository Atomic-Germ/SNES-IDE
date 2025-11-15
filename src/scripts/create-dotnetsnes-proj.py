"""
SNES-IDE - create-dotnetsnes-proj.py
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
from subprocess import CompletedProcess
from tkinter import Tk, filedialog
from pathlib import Path
import subprocess
import sys
import os

# Import platform utilities and path manager
sys.path.append(str(Path(__file__).parent.parent))
from platform_utils import platform_manager
from path_utils import path_manager

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
            print("No file/directory selected. Application terminated.")
            sys.exit(1)
        
        if isinstance(selected_path, str) and not os.path.exists(selected_path):
            print(f"Selected path does not exist: {selected_path}")
            sys.exit(1)
        
        return selected_path
        
    except Exception as e:
        if root:
            try:
                root.destroy()
            except:
                pass
        
        print(f"Error in file dialog: {e}")
        sys.exit(1)

def main() -> NoReturn:
    """Main logic to create dotnetsnes project"""

    snes_ide_home: CompletedProcess[str] = subprocess.run(
        [platform_manager.get_relative_executable_path("get-snes-ide-home")],
        cwd=str(path_manager.executable_dir), shell=True, capture_output=True, text=True
    )

    if snes_ide_home.returncode != 0:
        print(
            f"get-snes-ide-home failed to execute duel to {snes_ide_home.stderr}, exiting..."
        )
        exit(-1)

    snes_home = Path(snes_ide_home.stdout.strip())
    dotnetsnes_proj = platform_manager.get_template_path(
        "DotnetSnesLib/template/DotnetSnes.Example.HelloWorld", snes_home
    )

    output_path: Path = Path(str(get_file_path(
        "Select directory to your project", [("Directories", "*")],
        multiple=False, directory=True
    )))

    project_name: str = output_path.name
    
    # Validate project name
    if not platform_manager.validate_project_name(project_name):
        print(f"Invalid project name: {project_name}")
        exit(-1)

    target_path = output_path / project_name
    success = platform_manager.copy_template_safely(dotnetsnes_proj, target_path, overwrite=False)
    
    if success:
        print("Successfully copied dotnetsnes template")
        exit(0)
    else:
        print(f"Failed to copy dotnetsnes template {dotnetsnes_proj} to {target_path}")
        exit(-1)

if __name__ == "__main__":
    main()
