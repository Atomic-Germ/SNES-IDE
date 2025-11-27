import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

def test_tk_gui_imports():
    # Test that the tk GUI module and class are importable
    from snes_installer import tk_gui
    assert hasattr(tk_gui, 'SNESTkGui')
