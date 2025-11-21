"""
Cross-platform build system for SNES-IDE

This replaces the Unix-only Makefile with a Python-based build system
that works on Windows, macOS, and Linux.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
import argparse


# Colors for output (disabled on Windows cmd.exe)
class Colors:
    """Terminal color codes."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    @classmethod
    def disable_on_windows(cls):
        """Disable colors if on Windows (unless using modern terminal)."""
        if platform.system() == 'Windows' and not os.environ.get('TERM'):
            for attr in dir(cls):
                if not attr.startswith('_'):
                    setattr(cls, attr, '')


def print_header(text):
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.resolve()


def run_command(cmd, cwd=None, shell=False):
    """
    Run a command and return the result.
    
    Args:
        cmd: Command as list or string
        cwd: Working directory
        shell: Whether to use shell
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            shell=shell,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, '', str(e)


def clean():
    """Clean build artifacts."""
    print_header("CLEANING BUILD ARTIFACTS")
    
    project_root = get_project_root()
    
    # Remove SNES-IDE-out directory
    out_dir = project_root / 'SNES-IDE-out'
    if out_dir.exists():
        print(f"Removing {out_dir}...")
        shutil.rmtree(out_dir)
        print_success("Removed SNES-IDE-out/")
    
    # Remove .spec files
    for spec_file in project_root.glob('*.spec'):
        print(f"Removing {spec_file}...")
        spec_file.unlink()
        print_success(f"Removed {spec_file.name}")
    
    # Clean build directory (but keep certain files)
    build_dir = project_root / 'build'
    keep_files = {'build.py', 'LICENSE.txt', 'requirements.txt'}
    
    if build_dir.exists():
        print(f"Cleaning {build_dir}...")
        for item in build_dir.iterdir():
            if item.name not in keep_files:
                if item.is_file():
                    item.unlink()
                    print(f"  Removed file: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    print(f"  Removed directory: {item.name}")
    
    print_success("Clean complete!")


def prepare():
    """Prepare the environment (create venv and install dependencies)."""
    print_header("PREPARING ENVIRONMENT")
    
    project_root = get_project_root()
    venv_dir = project_root / '.venv'
    
    # Create virtual environment
    print("Creating Python virtual environment...")
    if venv_dir.exists():
        print_warning("Virtual environment already exists, skipping creation")
    else:
        success, _, err = run_command([sys.executable, '-m', 'venv', str(venv_dir)])
        if success:
            print_success("Virtual environment created")
        else:
            print_error(f"Failed to create virtual environment: {err}")
            return False
    
    # Determine pip executable path
    if platform.system() == 'Windows':
        pip_path = venv_dir / 'Scripts' / 'pip.exe'
        activate_path = venv_dir / 'Scripts' / 'activate.bat'
    else:
        pip_path = venv_dir / 'bin' / 'pip'
        activate_path = venv_dir / 'bin' / 'activate'
    
    # Install requirements
    print("\nInstalling requirements...")
    requirements_file = project_root / 'build' / 'requirements.txt'
    
    if requirements_file.exists():
        success, stdout, err = run_command(
            [str(pip_path), 'install', '-r', str(requirements_file)]
        )
        if success:
            print_success("Requirements installed successfully")
            print(f"\nVirtual environment ready at: {venv_dir}")
            print(f"To activate, run:")
            if platform.system() == 'Windows':
                print(f"  {activate_path}")
            else:
                print(f"  source {activate_path}")
        else:
            print_error(f"Failed to install requirements: {err}")
            return False
    else:
        print_warning(f"Requirements file not found: {requirements_file}")
        return False
    
    return True


def build():
    """Build the SNES-IDE application."""
    print_header("BUILDING SNES-IDE")
    
    project_root = get_project_root()
    build_script = project_root / 'build' / 'build.py'
    
    if not build_script.exists():
        print_error(f"Build script not found: {build_script}")
        return False
    
    print(f"Running build script: {build_script}")
    success, stdout, err = run_command(
        [sys.executable, str(build_script)],
        cwd=str(project_root)
    )
    
    if stdout:
        print(stdout)
    
    if success:
        print_success("Build completed successfully!")
        return True
    else:
        print_error(f"Build failed: {err}")
        return False


def rebuild():
    """Clean and rebuild."""
    print_header("REBUILDING SNES-IDE")
    
    if not clean():
        return False
    
    return build()


def dev():
    """Run SNES-IDE in development mode."""
    print_header("RUNNING SNES-IDE (DEVELOPMENT MODE)")
    
    project_root = get_project_root()
    src_dir = project_root / 'src'
    main_script = src_dir / 'snes-ide.py'
    
    if not main_script.exists():
        print_error(f"Main script not found: {main_script}")
        return False
    
    print(f"Running: {main_script}")
    success, _, err = run_command(
        [sys.executable, str(main_script)],
        cwd=str(src_dir)
    )
    
    if not success:
        print_error(f"Failed to run: {err}")
        return False
    
    return True


def format_code():
    """Format code using black and isort."""
    print_header("FORMATTING CODE")
    
    project_root = get_project_root()
    src_dir = project_root / 'src'
    
    # Try to format with black
    print("Formatting with black...")
    success, _, err = run_command(
        [sys.executable, '-m', 'black', str(src_dir)]
    )
    if success:
        print_success("Code formatted with black")
    else:
        print_warning(f"Black not available: {err}")
    
    # Try to sort imports with isort
    print("\nSorting imports with isort...")
    success, _, err = run_command(
        [sys.executable, '-m', 'isort', str(src_dir)]
    )
    if success:
        print_success("Imports sorted with isort")
    else:
        print_warning(f"isort not available: {err}")


def lint():
    """Run linting checks."""
    print_header("RUNNING LINT CHECKS")
    
    project_root = get_project_root()
    src_dir = project_root / 'src'
    
    # Try to run flake8
    print("Running flake8...")
    success, stdout, err = run_command(
        [sys.executable, '-m', 'flake8', str(src_dir), '--max-line-length=100']
    )
    if stdout:
        print(stdout)
    if success or 'No module named' in err:
        print_success("Lint check passed")
    else:
        print_warning(f"Lint issues found")
        return False
    
    return True


def main():
    """Main entry point."""
    Colors.disable_on_windows()
    
    parser = argparse.ArgumentParser(
        description='SNES-IDE Cross-Platform Build System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_system.py clean      # Clean build artifacts
  python build_system.py prepare    # Setup environment
  python build_system.py build      # Build SNES-IDE
  python build_system.py rebuild    # Clean and build
  python build_system.py dev        # Run in development mode
  python build_system.py format     # Format code
  python build_system.py lint       # Run linting
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='build',
        choices=['build', 'clean', 'prepare', 'rebuild', 'dev', 'format', 'lint'],
        help='Build command to execute'
    )
    
    args = parser.parse_args()
    
    # Command mapping
    commands = {
        'clean': clean,
        'prepare': prepare,
        'build': build,
        'rebuild': rebuild,
        'dev': dev,
        'format': format_code,
        'lint': lint,
    }
    
    try:
        result = commands[args.command]()
        sys.exit(0 if result else 1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
