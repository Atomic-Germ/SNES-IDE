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
    # Optional smoke-run of the Python script's help
    if py.exists():
        res = subprocess.run(['python3', str(py), '--help'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert res.returncode in (0, 2), 'automatizer --help returned unexpected status'
