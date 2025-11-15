"""
SNES-IDE - get-snes-ide-home.py
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

from pathlib import Path
import sys

# Import path utilities
sys.path.append(str(Path(__file__).parent.parent))
from path_utils import path_manager

if __name__ == "__main__":

    snes_ide_home: Path = path_manager.executable_dir.parent
    print(snes_ide_home)
