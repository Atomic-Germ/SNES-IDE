"""
SNES-IDE - gfx-png-bmp-editor.py
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

from typing_extensions import Literal
from pathlib import Path
import sys
import os

# Import platform utilities and path manager
sys.path.append(str(Path(__file__).parent.parent))
from platform_utils import platform_manager
from path_utils import path_manager
from subprocess_utils import subprocess_manager

def get_home_path() -> str:
    """Get snes-ide home directory using subprocess_manager"""

    result = subprocess_manager.run_tool("get-snes-ide-home")
    
    if result.failed:
        raise RuntimeError(f"get-snes-ide-home failed: {result.stderr}")
        
    return result.stdout.strip()


def convert() -> Literal[-1, 0]:
    """Init libresprite png/bmp sprite/map editor."""

    libresprite: Path
    
    if platform_manager.is_windows():
        libresprite = Path(get_home_path()) / "bin" / "sprite-editor" / "libresprite.exe"
    
    elif platform_manager.is_macos():
        libresprite = Path(get_home_path()) / "bin" / "sprite-editor" / "libresprite.app"

    else:
        libresprite = Path(get_home_path()) / "bin" / "sprite-editor" / "libresprite.AppImage"

    if not libresprite or not libresprite.exists():

        print(f"Failed, libresprite not found in: {libresprite}")
        return -1

    try:
        
        if platform_manager.is_macos():
            # Use macOS "open" command for applications
            result = subprocess_manager.run_shell_command(f'open -a "{libresprite}"')
        
        else:
            # Direct execution for Linux/Windows
            result = subprocess_manager.run_external_executable(libresprite)

        if result.failed:
            print(f"Error while executing {libresprite}: {result.stderr}")
            return -1

    except Exception as e:
        print(f"Error while executing {libresprite}: {e}")
        return -1

    print("Success")
    return 0

if __name__ == "__main__":
    exit(convert())
