from pathlib import Path
from array import array
import subprocess
import sys
import platform
import shutil as _shutil

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

        # Prefer the packaged tools directory when running from the bundle.
        base = self.get_executable_path()
        packaged_tools = base / "tools"
        if packaged_tools.exists():
            self.path: Path = packaged_tools
        else:
            # Fallback for development mode / manual installs
            self.path: Path = Path.home() / "Desktop" / "snes-ide"

        self.options: array = array("B", (0, 1, 2, 3, 4, 5, 6))

        option = self.give_options()

        sys.exit(self.execute_bat(option))


    @staticmethod
    def run(file: Path):
        """
        Executes the specified file using the Windows command prompt.

        Args:
            file (Path): The path to the file to be executed.

        Raises:
            subprocess.CalledProcessError: If the command returns a non-zero exit status.
        """

        system = platform.system().lower()
        p = Path(file)
        # Windows: use cmd
        if system == 'windows':
            subprocess.run(["cmd", "/c", str(p)], check=True)
            return

        # Non-Windows: prefer shell scripts (.sh) or native executables
        # If a .sh counterpart exists, run it. If the target is an .exe,
        # try to run the native counterpart (same name without .exe) or
        # use wine if available.
        if p.suffix == '.bat':
            sh = p.with_suffix('.sh')
            if sh.exists():
                subprocess.run(["sh", str(sh)], check=True)
                return
            # try executable without extension
            native = p.with_suffix('')
            if native.exists():
                subprocess.run([str(native)], check=True)
                return
            # try wine (disabled for mac builds)
            # wine = _shutil.which('wine') or _shutil.which('wine64')
            # if wine:
            #     subprocess.run([wine, str(p)], check=True)
            #     return
            raise FileNotFoundError(f"No macOS/Linux wrapper found for {p}. Create a .sh wrapper or install the macOS native binary. See docs/PORTING_MAC.md.")

        # If file is executable or script, run directly
        if p.exists():
            # Make sure it's executable on POSIX
            try:
                p.chmod(p.stat().st_mode | 0o111)
            except Exception:
                pass
            subprocess.run([str(p)], check=True)
            return

        raise FileNotFoundError(f"File to execute not found: {p}")


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

        # Map options to script base names
        mapping = {
            0: 'create-new-project',
            1: 'text-editor',
            2: 'audio-tools',
            3: 'graphic-tools',
            4: 'other-tools',
            5: 'compiler',
            6: 'emulator'
        }

        if option not in mapping:
            return -1

        base_name = mapping[option]

        # Candidates to try, in order: .bat (Windows), .sh (POSIX), no extension (native)
        candidates = [self.path / (base_name + ext) for ext in ('.bat', '.sh', '')]

        for candidate in candidates:
            if candidate.exists():
                try:
                    self.run(candidate)
                    return 0
                except Exception as e:
                    print(f"Error executing {candidate}: {e}")
                    return -1

        print(f"No suitable script found for option {option}. Looked for: {', '.join(str(p) for p in candidates)}")
        return -1
    

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
