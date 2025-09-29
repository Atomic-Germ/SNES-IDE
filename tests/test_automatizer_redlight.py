import platform
import subprocess
from pathlib import Path


def test_automatizer_available_on_macos_linux():
    if platform.system() == 'Windows':
        return
    # prefer a POSIX wrapper on PATH
    path = Path('libs/pvsneslib/devkitsnes/bin/automatizer')
    py = Path('libs/pvsneslib/devkitsnes/automatizer.py')
    assert path.exists() or py.exists(), (
        'automatizer not staged for POSIX: CI must place a Python wrapper (automatizer.py) into libs/pvsneslib/devkitsnes/'
    )
    # Verify the Python script is syntactically valid (compile-only) to avoid executing GUI/interactive code in CI
    if py.exists():
        res = subprocess.run(['python3', '-m', 'py_compile', str(py)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert res.returncode == 0, f"automatizer.py failed to compile: {res.stderr.decode('utf-8', errors='replace')}"
