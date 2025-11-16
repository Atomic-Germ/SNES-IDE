"""
SNES-IDE - gfx-tmx-editor.py
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

from typing_extensions import NoReturn
from pathlib import Path
import shutil
import sys
import os

# Import platform utilities and path manager
sys.path.append(str(Path(__file__).parent.parent))
from platform_utils import platform_manager
from path_utils import path_manager
from subprocess_utils import subprocess_manager

def check_if_path(program: str) -> bool:
    """
    Check if a program is available in the system PATH.
    
    Args:
        program (str): The name of the program to check (e.g., 'make', 'tiled')
        
    Returns:
        bool: True if the program is found in PATH, False otherwise
    """
    return shutil.which(program) is not None

def get_home_path() -> str:
    """Get snes-ide home directory using subprocess_manager"""

    result = subprocess_manager.run_tool("get-snes-ide-home")
    
    if result.failed:
        raise RuntimeError(f"get-snes-ide-home failed: {result.stderr}")
        
    return result.stdout.strip()


def main() -> NoReturn:
    """Main logic to init tiled -> default tmx_editor"""

    tmx_editor: Path
    
    if platform_manager.is_windows():
        tmx_editor = Path(get_home_path()) / "bin" / "tmx-editor" / "tiled.exe"
    
    elif platform_manager.is_macos():
        tmx_editor = Path(get_home_path()) / "bin" / "tmx-editor" / "Tiled.app"

    else:
        tmx_editor = Path(get_home_path()) / "bin" / "tmx-editor" / "tiled.AppImage"

    if not tmx_editor or not tmx_editor.exists():
        print(f"Failed, tiled does not exist in: {tmx_editor}")
        sys.exit(-1)

    try:
        
        if platform_manager.is_macos():
            # Use macOS "open" command for applications
            result = subprocess_manager.run_shell_command(f'open -a "{tmx_editor}"')
        
        else:
            # Direct execution for Linux/Windows
            result = subprocess_manager.run_external_executable(tmx_editor)

        if result.failed:
            print(f"Error while executing {tmx_editor}: {result.stderr}")
            sys.exit(-1)

    except Exception as e:
        print(f"Error while executing {tmx_editor}: {e}")
        sys.exit(-1)

    print("Success")
    sys.exit(0)

if __name__ == "__main__":
    main()
