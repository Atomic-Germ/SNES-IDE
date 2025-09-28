from pathlib import Path
from array import array
import platform
import os
import shutil
import subprocess
import sys

class SnesIde(object):

    def __init__(self, *args: object, **kwargs: object) -> None:
        """
        Initializes the class instance.

        - Sets the executable path.
        - Initializes the options array with values 0 through 6.
        - Prompts the user to select an option.
        - Executes a batch file based on the selected option and exits the program.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """

        # Resolve installation/project root
        env_root = os.environ.get('SNESIDE_ROOT')
        if env_root:
            self.path: Path = Path(env_root)
        elif (Path.home() / "Desktop" / "snes-ide").exists():
            self.path = Path.home() / "Desktop" / "snes-ide"
        else:
            # Fallback to repository layout
            self.path = Path(__file__).absolute().parent.parent

        self.options: array = array("B", (0, 1, 2, 3, 4, 5, 6))

        # Non-interactive option via env var or CLI
        opt = None
        dry_run = False

        # Environment overrides
        if os.environ.get('SNESIDE_OPTION'):
            try:
                opt = int(os.environ.get('SNESIDE_OPTION'))
            except Exception:
                pass

        if os.environ.get('SNESIDE_DRY_RUN'):
            dry_run = True

        # CLI parsing: support '--option N' and '--dry-run'
        args = sys.argv[1:]
        if args:
            if '--dry-run' in args:
                dry_run = True
            if '--option' in args:
                try:
                    idx = args.index('--option')
                    opt = int(args[idx + 1])
                except Exception:
                    pass
            else:
                # allow passing the option as the first positional argument
                try:
                    first = int(args[0])
                    opt = first
                except Exception:
                    pass

        if opt is None:
            option = self.give_options()
        else:
            option = opt

        # Execute and return exit code
        try:
            self.execute_bat(option) if not dry_run else self.execute_bat(option)
            sys.exit(0)
        except SystemExit:
            raise
        except Exception as e:
            print("Error executing option:", e)
            sys.exit(-1)


    def run_script(self, name: str, dry_run: bool = False):
        """
        Run a platform-appropriate script for the given base path.

        - On Windows: prefer .bat, .exe, then .py
        - On POSIX (Linux/macOS): prefer .sh, .py, then the basename executable if present

        The function will attempt to find an existing file with the expected
        extension and execute it using the right interpreter. It raises
        FileNotFoundError if no suitable script is found and subprocess.CalledProcessError on execution failure.
        """

        system = platform.system().lower()

        # Roots to search for the named tool. Prefer explicit SNESIDE_ROOT, then
        # Desktop installation, then repository layout (src/tools).
        roots = []

        env_root = os.environ.get("SNESIDE_ROOT")
        if env_root:
            roots.append(Path(env_root))

        desktop_root = Path.home() / "Desktop" / "snes-ide"
        roots.append(desktop_root)

        repo_root = Path(__file__).absolute().parent.parent
        roots.append(repo_root)
        roots.append(repo_root / "src" / "tools")
        roots.append(repo_root / "tools")

        exts = (['.bat', '.exe', '.py'] if system.startswith('win') else ['.sh', '.py', ''])

        found = None
        tried = []

        for r in roots:
            for ext in exts:
                candidate = (r / name).with_suffix(ext) if ext != '' else (r / name)
                tried.append(candidate)
                if candidate.exists() and candidate.is_file():
                    found = candidate
                    break
            if found:
                break

        if not found:
            raise FileNotFoundError(f"No suitable launcher found for {name} on {system}; tried: {tried}")

        # If dry-run mode requested, only validate presence and return the path
        if dry_run or os.environ.get('SNESIDE_DRY_RUN'):
            print(f"DRY-RUN: resolved launcher: {found}")
            return

        # Ensure executable permission for POSIX shell scripts or bare executables
        if not system.startswith("win") and found.suffix in (".sh", ""):
            try:
                found.chmod(found.stat().st_mode | 0o111)
            except Exception:
                pass

        # Dispatch execution
        if found.suffix == ".py":
            subprocess.run([sys.executable, str(found)] + sys.argv[1:], check=True)
        elif system.startswith("win") and found.suffix == ".bat":
            subprocess.run(["cmd", "/c", str(found)], check=True)
        else:
            subprocess.run([str(found)], check=True)


    def execute_bat(self, option: int) -> int:
        """
        Executes a batch file corresponding to the given option.

        Parameters:
            option (int): An integer representing the batch file to execute.
                0 - create-new-project.bat
                1 - text-editor.bat
                2 - audio-tools.bat
                3 - graphic-tools.bat
                4 - other-tools.bat
                5 - compiler.bat
                6 - emulator.bat

        Returns:
            int: 0 if the batch file executed successfully, -1 if an error occurred.

        Raises:
            subprocess.CalledProcessError: If the batch file execution fails.
        """

        match option:

            case 0:   self.run_script(self.path / "create-new-project"); return 0

            case 1:   self.run_script(self.path / "text-editor"); return 0

            case 2:   self.run_script(self.path / "audio-tools"); return 0

            case 3:   self.run_script(self.path / "graphic-tools"); return 0

            case 4:   self.run_script(self.path / "other-tools"); return 0

            case 5:   self.run_script(self.path / "compiler"); return 0

            case 6:   self.run_script(self.path / "emulator"); return 0

            case _:   return -1
    

    def give_options(self) -> int:
        """
        Presents a menu of SNES project-related options to the user and prompts for a selection.
        The available options include:

            0 - Create a new SNES project
            1 - Start Notepad++ text editor
            2 - Start an audio framework for SNES
            3 - Start a graphic framework for SNES
            4 - Run an external framework for SNES
            5 - Compile a SNES project
            6 - Emulate a SNES project with bsnes

        The method prints the options, reads user input, validates it against self.options,
        and recursively prompts again if the input is invalid.

        Returns:
            int: The selected option as an integer.

        """

        txt: str = "\
Create a new Snes project -> 0\n \
Start notepad++ text editor -> 1\n \
Start an audio framework for snes -> 2\n \
Start a graphic framework for snes -> 3\n \
Run an external framework for snes -> 4\n \
Compile a Snes project -> 5\n \
Emulate a Snes project with bsnes -> 6\n "

        print("Choose an option from the ones below: ", txt, sep="\n\n")

        option = int(input())

        if option not in self.options:

            print("\nINVALID ENTRY: try again\n")

            return self.give_options()

        return option



    @staticmethod
    def get_executable_path() -> Path:
        """
        Returns the directory path where the current executable or script is located.
        If the application is running as a PyInstaller bundle (frozen), it returns the directory containing the executable.
        Otherwise, it returns the directory containing the current Python script file.
        Returns:
            Path: The directory path of the executable or script.
        """

        if getattr(sys, 'frozen', False):
            # PyInstaller executable
            print("Executable path mode chosen")

            return Path(sys.executable).parent
    
        else:
            # Normal script
            print("Python script path mode chosen")

            return Path(__file__).absolute().parent


if __name__ == "__main__":

    SnesIde()
