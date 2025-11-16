"""
SNES-IDE - audio-wav-brr-converter.py
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
from typing_extensions import Literal
from tkinter import Tk, filedialog
from pathlib import Path
import sys
import os

# Import platform utilities
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
            sys.sys.exit(1)
        
        if isinstance(selected_path, str) and not os.path.exists(selected_path):
            print(f"Selected path does not exist: {selected_path}")
            sys.sys.exit(1)
        
        return selected_path
        
    except Exception as e:
        if root:
            try:
                root.destroy()
            except:
                pass
        
        print(f"Error in file dialog: {e}")
        sys.sys.exit(1)

def get_home_path() -> str:
    """Get snes-ide home directory using subprocess_manager"""

    result = subprocess_manager.run_tool("get-snes-ide-home")
    
    if result.failed:
        raise RuntimeError(f"get-snes-ide-home failed: {result.stderr}")
        
    return result.stdout.strip()

def convert() -> Literal[-1, 0]:
    """Convert WAV files to BRR using snesbrr converter."""

    snesbrr: Path

    snesbrr = (
        Path(get_home_path()) / "bin" / "pvsneslib" / "tools" 
        / platform_manager.get_executable_name("snesbrr")
    )

    try:

        if not snesbrr.exists():
            print("snesbrr does not exist")
            return -1

        input_file: Path = Path(str(
            get_file_path(
                "Select a WAV file", [("WAV files", "*.wav")], 
                multiple=False, directory=False
            )
        ))

        if not input_file or not input_file.exists() or not str(input_file).endswith(".wav"):

            print("Input file does not exist or is not a brr file")
            return -1
            
        # Execute snesbrr conversion using subprocess_manager
        output_file = str(input_file).split('.')[0] + ".brr"
        result = subprocess_manager.run_external_executable(
            snesbrr, 
            args=["-e", str(input_file), output_file]
        )
        
        if result.failed:
            print(f"Error while executing snesbrr to convert your wav file: {result.stderr}")
            return -1

    except Exception as e:

        print(f"Error while executing snesbrr to convert your wav file: {e}")
        return -1
        
    print("Success!")
    return 0

if __name__ == "__main__":

    sys.exit(convert())
