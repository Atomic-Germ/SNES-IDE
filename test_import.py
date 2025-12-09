import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from src.tui.app import SNESIDEApp
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
