#!/usr/bin/env python3
"""Main entry point for the SNES Installer."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from snes_installer.installer import main

if __name__ == "__main__":
    main()