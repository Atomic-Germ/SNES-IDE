"""
SNES-IDE - open-emulator.py
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
from subprocess import CalledProcessError
from tkinter import Tk, filedialog
from typing import NoReturn
from pathlib import Path
import platform
import sys
import os

from platform_helpers import runGetSnesIDEHome, runCmd, openPath


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

def get_executable_path() -> Path:
        """Get the path of the executable or script based on whether the script is frozen 
        (PyInstaller) or not."""

        if getattr(sys, 'frozen', False):
            print("executable path mode chosen")
            return Path(sys.executable).resolve().parent
        
        else:
            print("Python script path mode chosen")
            return Path(__file__).resolve().parent

def main() -> NoReturn:
    """Main logic to open a snes emulator in snes-ide"""

    home_path: Path

    try:
        # Use runGetSnesIDEHome to locate and run the
        # helper that prints the snes-ide home path. The helper 
        # searches PATH and cwd
        home_path = runGetSnesIDEHome(cwd=get_executable_path())
    except FileNotFoundError as e:
        print(f"get-snes-ide-home helper not found: {e}")
        exit(-1)
    except Exception as e:
        print(f"Error while getting snes-ide home folder: {e}, exiting...")
        exit(-1)

    sbase: Path = home_path / "bin" / "snes-emulator"

    system_name = platform.system().lower()

    # Prefer platform-appropriate binary names
    if system_name == "windows":
        candidates = [sbase / "lakesnes.exe", sbase / "lakesnes"]
    elif system_name == "darwin":
        candidates = [sbase / "bsnes.app", sbase / "lakesnes"]
    else:
        candidates = [sbase / "lakesnes", sbase / "lakesnes.exe"]

    snes_emulator: Optional[Path] = None
    for c in candidates:
        if c.exists():
            snes_emulator = c
            break

    if not snes_emulator:
        print(f"Failed, snes emulator not found in any of: {', '.join(str(p) for p in candidates)}")
        exit(-1)

    rom_path: Path = Path(str(get_file_path(
        "Select your ROM", [("ROM files", "*.sfc")], multiple=False,
        directory=False
    )))

    try:
        if system_name == "darwin":
            # Open the .app bundle and forward the ROM path as
            # an argument if it accepts arguments this way; if not,
            # the app will simply be opened.
            openPath(snes_emulator, args=[str(rom_path)])
        else:
            # Execute the emulator binary directly and pass the ROM path
            runCmd([str(snes_emulator), str(rom_path)], check=True)

    except CalledProcessError as e:
        print(f"Error while executing {snes_emulator}: {e}")
        exit(-1)
    except Exception as e:
        print(f"Error while executing {snes_emulator}: {e}")
        exit(-1)

    exit(0)

if __name__ == "__main__":
    main()
