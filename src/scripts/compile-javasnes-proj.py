"""
SNES-IDE - compile-javasnes-proj.py
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
import sys
import os

# Import platform utilities and path manager
sys.path.append(str(Path(__file__).parent.parent))
from platform_utils import platform_manager
from path_utils import path_manager
from subprocess_utils import subprocess_manager

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
            except: ...
        
        print(f"Error in file dialog: {e}")
        sys.exit(1)

def main() -> NoReturn:
    """Main logic of the compilation of the javasnes project"""

    # Get SNES-IDE home directory using subprocess_manager
    result = subprocess_manager.run_tool("get-snes-ide-home")

    if result.failed:
        print(
            f"get-snes-ide-home failed to execute due to {result.stderr}, exiting..."
        )
        exit(-1)

    pvsneslib_home: Path = Path(result.stdout.strip()) / "bin" / "pvsneslib"
    bin_dir: Path = Path(result.stdout.strip()) / "bin"
    java_home: Path = platform_manager.get_java_home(bin_dir)

    # Set up environment variables
    env_vars = {
        "PVSNESLIB_HOME": str(pvsneslib_home),
        "JAVA_HOME": str(java_home)
    }

    javasnes_proj_jar: Path = Path(str(get_file_path(
        "Select JavaSnes project's JAR output file",
        file_types=[("JAR files", "*.jar")],
        multiple=False, directory=False
    )))

    javasnes_proj: Path = javasnes_proj_jar.parent

    if not (javasnes_proj_jar).exists():
        print("No JAR file to build project found, exiting...")
        exit(-1)

    # Run Java JAR using subprocess_manager
    java_path = platform_manager.get_java_path(bin_dir)
    java_result = subprocess_manager.run_external_executable(
        java_path,
        args=["-jar", str(javasnes_proj_jar)],
        env=env_vars,
        check=False  # We handle errors manually
    )

    if java_result.failed:
        print(f"Error while building javasnes project: {java_result.stderr}")
        exit(-1)

    if not (javasnes_proj / "output").exists():
        print("No output path found, exiting...")
        exit(-1)

    if not (javasnes_proj / "output" / "Makefile").exists():
        print("No Makefile to build project found, exiting...")
        exit(-1)

    # Compile using subprocess_manager
    make_result = subprocess_manager.compile_with_make(
        makefile_dir=javasnes_proj / "output",
        env_vars=env_vars
    )

    if make_result.failed:
        print(f"Error while compiling the software {make_result.stderr}, exiting...")
        exit(-1)

    exit(0)

if __name__ == "__main__":
    main()
