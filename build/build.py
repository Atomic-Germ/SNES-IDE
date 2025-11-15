"""
SNES-IDE - build.py
Copyright (C) 2025 BrunoRNS and Atomic-Germ

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

from colorama import init, Fore, Style

from typing import Any, List, Tuple, Callable, Dict
from typing_extensions import Literal

from subprocess import CompletedProcess
from pathlib import Path
import subprocess
import traceback
import hashlib
import shutil
import locale
import stat
import json
import sys
import os

# Import platform utilities and path manager
sys.path.append(str(Path(__file__).parent.parent / "src"))
from platform_utils import platform_manager
from path_utils import path_manager

"""
Print functions
"""
def _supports_unicode() -> bool:
    encoding: Any | None = getattr(sys.stdout, "encoding", None)

    if not encoding:
        encoding = locale.getpreferredencoding(False)
    try:
        "✔".encode(encoding)
        "✖".encode(encoding)
        return True

    except Exception:
        return False

def print_step(msg: str) -> None:
    print(f"{COLOR_STEP}{STEP_SYMBOL} {msg}{COLOR_RESET}")

def print_ok(msg: str) -> None:
    print(f"{COLOR_OK}{OK_SYMBOL} {msg}{COLOR_RESET}")

def print_fail(msg: str) -> None:
    print(f"{COLOR_FAIL}{FAIL_SYMBOL} {msg}{COLOR_RESET}")

def print_summary(success: bool, failed_steps: List[str]) -> None:
    print("\n" + "="*40)
    if success:
        print_ok("BUILD SUCCESSFUL")
    else:
        print_fail("BUILD FAILED")
        print_fail(f"Failed steps: {', '.join(failed_steps)}")
    print("="*40 + "\n")

"""
Definitions
"""
init(autoreset=True)

COLOR_OK: str = Fore.GREEN + Style.BRIGHT
COLOR_FAIL: str = Fore.RED + Style.BRIGHT
COLOR_STEP: str = Fore.CYAN + Style.BRIGHT
COLOR_RESET: str = Style.RESET_ALL

USE_UNICODE: bool = _supports_unicode()

OK_SYMBOL: Literal['✔', '[OK]'] = "✔" if USE_UNICODE else "[OK]"
FAIL_SYMBOL: Literal['✖', '[FAIL]'] = "✖" if USE_UNICODE else "[FAIL]"
STEP_SYMBOL: Literal['==>'] = "==>"

# Enhanced path management using path_manager
ROOT: Path = path_manager.project_root
SNESIDEOUT: Path = ROOT / "SNES-IDE-out"

def ensure_directory_exists(path: Path) -> Path:
    """
    Ensure directory exists using path_manager's directory creation logic.
    
    Args:
        path: Path to directory or file (will create parent if file)
    
    Returns:
        Path: The directory path that was created/ensured
    """
    if path.suffix:  # Has file extension, get parent directory
        dir_path = path.parent
    else:
        dir_path = path
    
    return path_manager.ensure_directory_exists(dir_path)

def get_build_resource_path(relative_path: str) -> Path:
    """
    Get path to build resources using centralized path management.
    
    Args:
        relative_path: Relative path from project root
        
    Returns:
        Path: Full path to resource
    """
    return path_manager.project_root / relative_path

"""
Build python script
"""

def compile_python(
    python_file_path: Path, target_file_path: Path, windowed: bool,
    icon_path: Path, do_chmod_x: bool, clean_tmp_exec: bool
) -> int:
    """
    Compile a Python script to executable using PyInstaller.
    
    Args:
        python_file_path: Path to the source Python file
        target_file_path: Path where the executable should be placed
        windowed: Whether to run without console (windowed mode)
        icon_path: Path to icon file for the executable
        do_chmod_x: Whether to make executable with chmod +x (Unix-like systems)
        clean_tmp_exec: Whether to clean temporary build files
    
    Returns:
        int: Return code (0 for success, non-zero for failure)
    """
    
    if not python_file_path.exists():
        print(f"Error: Python file not found: {python_file_path}")
        return 1

    file_path: Path = target_file_path
    
    # Use enhanced directory creation
    ensure_directory_exists(file_path)
    
    cmd: List[str] = ["pyinstaller", "--onefile"]
    
    if platform_manager.is_macos():
        if windowed:
            cmd.remove("--onefile")
            cmd.append("--windowed")
            if not file_path.name.endswith(".app"):
                file_path: Path = file_path.parent / f"{file_path.stem}.app"
        else:
            cmd.append("--console")
            
    elif platform_manager.is_windows():
        if windowed:
            cmd.append("--windowed")
        else:
            cmd.append("--console")

        if not file_path.name.endswith(".exe"):
            file_path = file_path.parent / f"{file_path.stem}.exe"
            
    else:
        if windowed:
            cmd.append("--noconsole")
        else:
            cmd.append("--console")
    
    if icon_path and icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])
    
    cmd.append(str(python_file_path))
    
    try:
        print(f"Running PyInstaller with command: {' '.join(cmd)}")
        result: CompletedProcess[str] = subprocess.run(
            cmd, capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"PyInstaller failed with return code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return result.returncode
        
        dist_dir: Path = Path("dist")
        if not dist_dir.exists():
            print("Error: PyInstaller dist directory not found")
            return 1
        
        exec_name: str = python_file_path.stem

        generated_item: Path
        item_type: str

        if platform_manager.is_macos() and windowed:
            generated_item = dist_dir / f"{exec_name}.app"
            item_type = "app bundle"
            
        elif platform_manager.is_windows():
            generated_item = dist_dir / f"{exec_name}.exe"
            item_type = "executable"
            
        else:
            generated_item = dist_dir / exec_name
            item_type = "executable"
        
        if not generated_item.exists():
            print(f"Error: Generated {item_type} not found: {generated_item}")
            return 1
        
        if generated_item.is_dir():
            if file_path.exists():
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
            shutil.copytree(generated_item, file_path)
            shutil.rmtree(generated_item)
        else:
            shutil.move(str(generated_item), str(file_path))
        
        print(f"{item_type.capitalize()} created at: {file_path}")
        
        if do_chmod_x and not platform_manager.is_windows():
            
            if platform_manager.is_macos() and windowed:
                
                actual_executable: Path = file_path / "Contents" / "MacOS" / exec_name
                
                if actual_executable.exists():
                    
                    actual_executable.chmod(
                        actual_executable.stat().st_mode | stat.S_IEXEC
                    )
                    print(f"Set executable permissions on: {actual_executable}")
            else:
                
                file_path.chmod(file_path.stat().st_mode | stat.S_IEXEC)
                print(f"Set executable permissions on: {file_path}")
        
        if clean_tmp_exec:
            # Clean PyInstaller temporary files - be specific to avoid deleting source directories
            pyinstaller_build = Path("build") / exec_name  # PyInstaller's build directory
            pyinstaller_dist = Path("dist")
            spec_file = Path(f"{exec_name}.spec")
            
            cleanup_paths = [pyinstaller_build, pyinstaller_dist, spec_file]
            for path in cleanup_paths:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    print(f"Cleaned up: {path}")
        
        return 0
    
    except Exception as e:
        print(f"Error during compilation: {e}")
        return 1

"""
Reconstruct chunk files
"""

class FileJoiner:
    """
    Reconstructs original file from chunks using JSON manifest.
    Validates integrity using checksum verification.
    """
    
    def __init__(self, manifest_path: str, output_path: str):
        """
        Initialize the FileJoiner with manifest and output path.
        
        Args:
            manifest_path: Path to the JSON manifest file
            output_path: Path where reconstructed file will be saved
        """
        
        self.manifest_path: str = manifest_path
        self.output_path: str = output_path
        self.manifest_data: 'Dict[str, Any]|None' = None
    
    def load_manifest(self) -> bool:
        """
        Load and validate the manifest file.
        
        Returns:
            True if manifest is valid, False otherwise
        """
        
        try:
            
            if not os.path.exists(self.manifest_path):
                
                print(f"Error: Manifest file {self.manifest_path} not found")
                return False
            
            with open(self.manifest_path, 'r') as manifest_file:
                
                self.manifest_data = json.load(manifest_file)
            
            if self.manifest_data is None:
                
                print("Error: Failed to load manifest file")
                return False
            
            required_fields: List[str] = [
                'original_filename', 'total_size', 'checksum', 'chunks'
            ]
            
            if not all(field in self.manifest_data for field in required_fields):
                
                print("Error: Invalid manifest file structure")
                return False
            
            return True
            
        except Exception as e:
            
            print(f"Error loading manifest: {str(e)}")
            return False
    
    def verify_chunks(self) -> bool:
        """
        Verify all chunks exist and have correct sizes.
        
        Returns:
            True if all chunks are valid, False otherwise
        """
        
        if not self.manifest_data:
            
            return False
        
        print("Verifying chunks...")
        
        for chunk_info in self.manifest_data['chunks']:
            
            chunk_path: str = str(chunk_info['filename'])
            
            if not os.path.exists(str(Path(self.manifest_path).parent / chunk_path)):
                
                print(
                    "Error: "
                    f"Chunk file {Path(self.manifest_path).parent / chunk_path}"
                    " not found"
                )
                return False
            
            actual_size: int = os.path.getsize(
                str(Path(self.manifest_path).parent / chunk_path)
            )
            expected_size: str = str(chunk_info['size'])
            
            if actual_size != int(expected_size):
                
                print(f"Error: Chunk {Path(self.manifest_path).parent / chunk_path}"
                      " has incorrect size "
                      f"(expected: {expected_size}, actual: {actual_size})")
                
                return False
        
        print("All chunks verified successfully")
        return True
    
    def calculate_checksum(self, file_path: str) -> str:
        """
        Calculate MD5 checksum of reconstructed file.
        
        Args:
            file_path: Path to the file to checksum
            
        Returns:
            MD5 hash string
        """
        
        hash_md5 = hashlib.md5()
        
        with open(file_path, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_md5.update(chunk)
                
        return hash_md5.hexdigest()
    
    def join(self) -> bool:
        """
        Reconstruct the original file from chunks.
        
        Returns:
            True if successful, False otherwise
        """
        
        try:
            
            if not self.load_manifest():
                return False
            
            if not self.verify_chunks():
                return False
            
            if not self.manifest_data:
                return False
            
            print(
                "Reconstructing: "
                f"{
                    Path(self.manifest_path).parent /
                    self.manifest_data['original_filename']
                }"
            )
            
            print(
                "Target: "
                f"{
                    Path(self.output_path) /
                    self.manifest_data['original_filename']
                }"
            )
            
            print(f"Total chunks: {len(self.manifest_data['chunks'])}")
            
            sorted_chunks = sorted(self.manifest_data['chunks'], key=lambda x: x['index'])
            
            with open(
                str(Path(self.output_path) / self.manifest_data['original_filename']),
                'wb'
            ) as output_file:
                
                for i, chunk_info in enumerate(sorted_chunks):
                    
                    chunk_path = chunk_info['filename']
                    
                    with open(
                        Path(self.manifest_path).parent / chunk_path, 'rb'
                    ) as chunk_file:
                        
                        chunk_data = chunk_file.read()
                        output_file.write(chunk_data)
                    
                    progress = ((i + 1) / len(sorted_chunks)) * 100
                    
                    print(f"Processed chunk {chunk_info['index']:03d}:"
                          f" {Path(self.manifest_path).parent / chunk_path} "
                          f"({chunk_info['size'] / (1024 * 1024):.2f} MB) "
                          f"[{chunk_info['start_byte']}-{chunk_info['end_byte']}] - "
                          f"{progress:.1f}%")
            
            print("\nVerifying file integrity...")
            reconstructed_size = os.path.getsize(
                str(Path(self.output_path) / self.manifest_data['original_filename'])
            )
            expected_size = self.manifest_data['total_size']
            
            if reconstructed_size != expected_size:
                print(
                    f"Error: Size mismatch (expected:"
                    f" {expected_size}, actual: {reconstructed_size})"
                )
                return False
            
            actual_checksum = self.calculate_checksum(str(Path(
                Path(self.output_path) / self.manifest_data['original_filename']
            )))
            expected_checksum = self.manifest_data['checksum']
            
            print(f"Expected checksum: {expected_checksum}")
            print(f"Actual checksum: {actual_checksum}")
            
            if actual_checksum == expected_checksum:
                print("File integrity verified - checksums match!")
                return True
            
            else:
                print("Error: Checksum mismatch - file may be corrupted")
                return False
                
        except Exception as e:
            print(f"Error during file joining: {str(e)}")
            raise e
"""
Build Steps
"""

def clean_all() -> None:
    """
    Clean the SNES-IDE-out directory.
    """

    if SNESIDEOUT.exists():
        shutil.rmtree(SNESIDEOUT)

    return

def restore_big_files() -> None:
    """
    Restore all files that were previously split into chunks and stored in the resources directory.
    
    This function goes through all files with the extension "*.snes.ide.reconstruct.manifest.json" in the resources directory,
    and uses the FileJoiner class to join the chunks back into a single file. If the joining process is successful,
    it prints a message indicating the file that was reconstructed. If the joining process fails, it raises an exception.
    """
    resources_dir = get_build_resource_path('resources')
    
    for file in resources_dir.rglob("*.snes.ide.reconstruct.manifest.json"):
        
        if file.is_dir():
            continue
        
        joiner: FileJoiner = FileJoiner(str(file), str(file.parent))

        try:
            if joiner.join():
                print(f"Reconstructed file: {file}")
            
            else:
                raise Exception(f"Failed to reconstruct file: {file}")
            
        except Exception as e:
            
            traceback.print_exception(Exception, e, None)
            raise Exception(f"Failed to reconstruct file: {file}")
        
    return
    
def copy_root() -> None:
    """
    Copy all files from the root directory to the SNES-IDE-out directory.
    """
    ensure_directory_exists(SNESIDEOUT)

    for file in ROOT.glob("*.*"):
        if file.is_dir():
            continue

        shutil.copy(file, SNESIDEOUT / file.name)
    
    return


def copy_lib() -> None:
    """
    Copy all files from the lib directory to the SNES-IDE-out directory.
    """
    libs_output_dir = SNESIDEOUT / 'libs'
    ensure_directory_exists(libs_output_dir)

    libs_source = get_build_resource_path('resources/libs')

    for file in libs_source.rglob("*"):

        if file.is_dir():
            continue

        rel_path: Path = file.relative_to(libs_source)
        dest_path: Path = libs_output_dir / rel_path
        ensure_directory_exists(dest_path)
        shutil.copy(file, dest_path)
    
    return


def copy_docs() -> None:
    """
    Copy the docs directory to the SNES-IDE-out directory.
    """
    docs_output_dir = SNESIDEOUT / 'docs'
    ensure_directory_exists(docs_output_dir)

    docs_source = get_build_resource_path('docs')

    for file in docs_source.rglob("*"):

        if file.is_dir():
            continue

        rel_path: Path = file.relative_to(docs_source)
        dest_path: Path = docs_output_dir / rel_path
        ensure_directory_exists(dest_path)
        shutil.copy(file, dest_path)
    
    return

def copy_bin() -> None:
    """
    Copy the bin files to the SNES-IDE-out directory.
    """
    bin_output_dir = SNESIDEOUT / 'bin'
    ensure_directory_exists(bin_output_dir)

    # Get platform-specific directory name
    if platform_manager.is_windows():
        system = 'windows'
    elif platform_manager.is_macos():
        system = 'macos'
    else:  # Linux
        system = 'linux'

    # Copy COPYING.md
    copying_source = get_build_resource_path('resources/bin/COPYING.md')
    copying_dest = bin_output_dir / 'COPYING.md'
    ensure_directory_exists(copying_dest)
    shutil.copy(copying_source, copying_dest)

    # Copy platform-specific binaries
    platform_bin_source = get_build_resource_path(f'resources/bin/{system}')

    for file in platform_bin_source.rglob("*"):

        if file.is_dir():
            continue
        
        if len(file.suffixes) == 6:
            if \
                file.suffixes[1] == ".snes" and file.suffixes[2] == ".ide" and \
                file.suffixes[3] == ".reconstruct" and \
                file.suffixes[4] == ".manifest" and \
                file.suffixes[5] == ".json":
                    
                    continue
        
        if ".chunk" in file.suffix:
            continue

        rel_path: Path = file.relative_to(platform_bin_source)
        dest_path: Path = bin_output_dir / rel_path

        ensure_directory_exists(dest_path)
        shutil.copy(file, dest_path)
    
    return

def compile_and_copy_source() -> None:
    """
    Compile and copy the project's main source code.
    """
    source_dir = get_build_resource_path('src')

    for file in source_dir.rglob("*"):

        if file.is_dir():
            continue

        rel_path: Path = file.relative_to(source_dir)
        dest_path: Path = SNESIDEOUT / rel_path
        ensure_directory_exists(dest_path)

        # Get icon path using centralized path management
        icon_path = get_build_resource_path('icon.png')

        if file.name == "snes-ide.py":
            compile_python(
                file, dest_path.parent /
                (file.stem + ".exe" if platform_manager.is_windows() else file.stem),
                icon_path=icon_path,
                windowed=True, do_chmod_x=not platform_manager.is_windows(), clean_tmp_exec=True
            )
            
        elif file.suffix == ".py":
            compile_python(
                file, dest_path.parent /
                (file.stem + ".exe" if platform_manager.is_windows() else file.stem),
                icon_path=icon_path,
                windowed=False, do_chmod_x=not platform_manager.is_windows(), clean_tmp_exec=True
            )
            
        else:
            shutil.copy(file, dest_path)
    
    return

def decompress_zip_files_in_out():
    """
    Decompresses all zip files in the SNES-IDE-out directory by unpacking them into
    their parent directory and deleting the zip file.
    """
    
    for file in (SNESIDEOUT).rglob("*.zip"):
        
        if file.suffix == ".zip":
            shutil.unpack_archive(file, extract_dir=file.parent, format="zip")
            os.unlink(file)
            
    return

def run_step(step_name: str, func: Callable[..., None]) -> bool:
    """Pretty formatting for CI logs"""

    print_step(f"{step_name}...")

    try:
        func()
        print_ok(f"{step_name} completed.")
        return True

    except Exception as e:
        print_fail(f"{step_name} failed: {e}")
        traceback.print_exception(Exception, e, None)
        return False

def main() -> int:
    """
    Main function to run the build process.
    """

    steps: List[Tuple[str, Callable[..., None]]] = [
        ("Cleaning SNES-IDE-out", clean_all),
        ("Restoring big files", restore_big_files),
        ("Copying root files", copy_root),
        ("Copying libs", copy_lib),
        ("Copying docs", copy_docs),
        ("Copying binary files", copy_bin),
        ("Compiling and copying source", compile_and_copy_source),
        ("Decompressing zip files", decompress_zip_files_in_out),
    ]

    failed_steps: List[str] = []
    for name, func in steps:
        if not run_step(name, func):
            failed_steps.append(name)

    print_summary(len(failed_steps) == 0, failed_steps)

    return 0 if not failed_steps else -1

if __name__ == "__main__":
    """
    Run the main function.
    """
    
    exit(main())
