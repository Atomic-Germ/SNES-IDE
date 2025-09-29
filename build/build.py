#!/usr/bin/env python3
import os
import platform
import subprocess
import shlex
from pathlib import Path
from shutil import copy2

def list_directory(path: str = ".") -> list[str]:
    """
    Platform‑agnostic directory listing.
    Returns a list of entry names in *path*.
    """
    return [entry.name for entry in Path(path).iterdir()]

def open_file(path: str) -> None:
    """
    Open *path* with the default application on any OS.
    """
    system = platform.system()
    if system == "Windows":
        os.startfile(path)                     # Windows‑only builtin
    elif system == "Darwin":                   # macOS
        subprocess.run(["open", path], check=True)
    else:                                      # Linux / other Unix‑like
        subprocess.run(["xdg-open", path], check=True)

def ping(host: str, count: int = 4) -> str:
    """
    Cross‑platform ping wrapper.
    Returns the raw stdout of the ping command.
    """
    param = "-n" if platform.system().lower() == "windows" else "-c"
    result = subprocess.run(
        ["ping", param, str(count), host],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout

def copy_file(src: str, dst: str) -> None:
    """
    Copy a file using a pure‑Python implementation.
    """
    copy2(src, dst)   # preserves metadata and works everywhere

def get_environment() -> dict[str, str]:
    """
    Return a dictionary of the current process environment variables.
    """
    return dict(os.environ)

def run_command(command: str | list[str]) -> tuple[str, str, int]:
    """
    Execute *command* (string or list) safely on any platform.
    Returns (stdout, stderr, returncode).
    """
    args = shlex.split(command) if isinstance(command, str) else command
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout, result.stderr, result.returncode

# Example usage -------------------------------------------------------
if __name__ == "__main__":
    print("Current directory contents:", list_directory())
    # open_file("example.pdf")               # Uncomment to test opening a file
    print("Ping google.com:\n", ping("google.com"))
    # copy_file("src.txt", "dst.txt")        # Uncomment to test copying
    print("Environment variables:", get_environment())
    out, err, rc = run_command("python --version")
    print("Command output:", out.strip(), "Return code:", rc)
