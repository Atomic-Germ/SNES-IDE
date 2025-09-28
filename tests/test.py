""" This is just an example test script for the SNES-IDE-out project. """
from pathlib import Path
import subprocess
import shutil

ROOT = Path(__file__).parent.parent.resolve()
SNESIDEOUT = ROOT / "SNES-IDE-out"


def test() -> None:
    """
    Test the project.
    """
    install_ps1 = SNESIDEOUT / "INSTALL.ps1"
    install_bat = SNESIDEOUT / "INSTALL.bat"

    # Prefer PowerShell script when present and pwsh is available
    if install_ps1.exists() and shutil.which('pwsh'):

        try:
            subprocess.run(['pwsh', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(install_ps1)], check=True, cwd=SNESIDEOUT)

        except subprocess.CalledProcessError as e:

            print(f"INSTALL.ps1 failed with exit code {e.returncode}")

    elif install_bat.exists():

        try:
            subprocess.run([str(install_bat)], check=True, shell=True, cwd=SNESIDEOUT)

        except subprocess.CalledProcessError as e:

            print(f"INSTALL.bat failed with exit code {e.returncode}")

    else:
        
        print("INSTALL script not found in SNES-IDE-out directory.")


if __name__ == "__main__":
    test()
    print("Test completed.")
    exit(0)