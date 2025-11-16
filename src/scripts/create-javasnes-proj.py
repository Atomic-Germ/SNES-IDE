"""
SNES-IDE - create-javasnes-proj.py
Copyright (C) 2025 BrunoRNS

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

import argparse
from typing import Union, List, NoReturn, Optional, Tuple
from tkinter import Tk, filedialog, simpledialog, messagebox
from pathlib import Path
import sys
import os
import re

# Import platform utilities and path manager
sys.path.append(str(Path(__file__).parent.parent))
from platform_utils import platform_manager
from path_utils import path_manager
from subprocess_utils import subprocess_manager


def get_project_name(initial_name: str = "") -> str:
    """
    Get a valid project name from the user with validation.
    
    Args:
        initial_name: Initial project name suggestion
        
    Returns:
        str: Valid project name
        
    Raises:
        SystemExit: If user cancels or provides invalid input
    """
    root: Optional[Tk] = None
    
    try:
        root = Tk()
        root.withdraw()
        
        try:
            root.attributes('-topmost', True)  # type: ignore
        except: 
            pass
        
        while True:
            project_name = simpledialog.askstring(
                "Project Name",
                "Enter a name for your JavaSnes project:\n\n"
                "• Must start with a letter or underscore\n"
                "• Can contain letters, numbers, underscore, hyphen\n"
                "• Avoid reserved system names\n"
                "• Follow Java package naming conventions",
                initialvalue=initial_name
            )
            
            if project_name is None:  # User cancelled
                print("Project creation cancelled by user.")
                sys.exit(0)
                
            project_name = project_name.strip()
            
            if not project_name:
                messagebox.showerror("Invalid Name", "Project name cannot be empty.")
                continue
                
            # Validate project name
            if not platform_manager.validate_project_name(project_name):
                error_msg = get_validation_error_message(project_name)
                messagebox.showerror("Invalid Project Name", error_msg)
                initial_name = project_name  # Keep user's input for next attempt
                continue
                
            return project_name
            
    except Exception as e:
        print(f"Error getting project name: {e}")
        sys.exit(1)
    finally:
        if root:
            try:
                root.destroy()
            except:
                pass


def get_validation_error_message(name: str) -> str:
    """
    Get a detailed error message explaining why a project name is invalid.
    
    Args:
        name: The invalid project name
        
    Returns:
        str: Detailed error message
    """
    if not name or len(name) == 0:
        return "Project name cannot be empty."
    
    if not re.match(r'^[A-Za-z_]', name):
        return "Project name must start with a letter (A-Z, a-z) or underscore (_)."
        
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_-]*$', name):
        invalid_chars = [c for c in name if not re.match(r'[A-Za-z0-9_-]', c)]
        return f"Project name contains invalid characters: {', '.join(set(invalid_chars))}\n" \
               f"Only letters, numbers, underscore (_), and hyphen (-) are allowed."
    
    if platform_manager.is_windows():
        reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                   'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 
                   'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        if name.upper() in reserved:
            return f"'{name}' is a reserved Windows system name and cannot be used."
        
        if len(name) > 200:
            return f"Project name is too long ({len(name)} characters). Maximum is 200 characters."
    else:
        if name.startswith('.'):
            return "Project name cannot start with a dot (.) on Unix systems."
            
    return "Project name validation failed for unknown reasons."

def get_file_path(
    title: str = "Select file",
    file_types: List[Tuple[str, str]] = [("All files", "*.*")],
    multiple: bool = False,
    directory: bool = False
) -> Union[str, List[str], Tuple[str, ...], NoReturn]:
    """
    Replaces sys.argv with a graphical file/directory selection interface.
    
    Args:
        title: Dialog window title
        file_types: List of tuples with description and extension [(desc, *.ext)]
        multiple: Whether to allow multiple file selection
        directory: Whether to select directories instead of files
    
    Returns:
        str or List[str]: Selected path(s)
        NoReturn: Exits program if user cancels or error occurs
    
    Raises:
        SystemExit: Always exits program on cancellation or error
    """
    root: Optional[Tk] = None
    
    try:
        root = Tk()
        root.withdraw()

        try:
            root.attributes('-topmost', True)  # type: ignore
        except: ...

        selected_path: Union[str, List[str], Tuple[str, ...], None] = None
        
        if directory:
            selected_path = filedialog.askdirectory(title=title)

        elif multiple:
            selected_path = filedialog.askopenfilenames(
                title=title, 
                filetypes=file_types
            )
            if selected_path:
                selected_path = list(selected_path)
        else:
            selected_path = filedialog.askopenfilename(
                title=title, 
                filetypes=file_types
            )
        
        if root:
            root.destroy()
            root = None
        
        if not selected_path or (isinstance(selected_path, list) and len(selected_path) == 0):
            print("No file/directory selected. Application terminated.")
            sys.sys.exit(1)
        
        if isinstance(selected_path, str) and not os.path.exists(selected_path):
            print(f"Selected path does not exist: {selected_path}")
            sys.sys.exit(1)
        
        return selected_path
        
    except Exception as e:
        if root:
            try:
                root.destroy()
            except:
                pass
        
        print(f"Error in file dialog: {e}")
        sys.sys.exit(1)


class ProjectCreator:
    """Create a new JavaSnes project with improved error handling."""

    def __init__(self) -> None:
        """Initialize the project creator with user input."""
        try:
            self.parent_dir: Path = Path(str(
                get_file_path(
                    "Select parent directory for your JavaSnes project", 
                    [("Directories", "*")],
                    directory=True
                )
            ))
            
            # Get a suggested project name from the parent directory
            suggested_name = self._get_suggested_name(self.parent_dir)
            
            # Get project name from user with validation
            self.project_name: str = get_project_name(suggested_name)
            
            # Calculate full project path
            self.project_path: Path = self.parent_dir / self.project_name
            
        except KeyboardInterrupt:
            print("\nProject creation cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"Error during initialization: {e}")
            sys.exit(1)
    
    def _get_suggested_name(self, parent_dir: Path) -> str:
        """
        Generate a suggested project name based on the parent directory.
        
        Args:
            parent_dir: The parent directory where the project will be created
            
        Returns:
            str: A suggested project name
        """
        base_name = "my_javasnes_project"
        
        # Try to use a variation of the parent directory name
        if parent_dir.name and parent_dir.name not in {".", "..", "/"}:
            # Clean up the directory name to make it a valid project name
            cleaned = re.sub(r'[^A-Za-z0-9_-]', '_', parent_dir.name)
            cleaned = re.sub(r'_+', '_', cleaned)  # Remove multiple underscores
            cleaned = cleaned.strip('_')  # Remove leading/trailing underscores
            
            if cleaned and re.match(r'^[A-Za-z_]', cleaned):
                base_name = f"{cleaned}_java_project"
        
        # Ensure the name doesn't already exist
        counter = 1
        suggested = base_name
        while (parent_dir / suggested).exists():
            suggested = f"{base_name}_{counter}"
            counter += 1
            
        return suggested

    def get_home_path(self) -> str:
        """Get snes-ide home directory using subprocess_manager."""
        try:
            result = subprocess_manager.run_tool("get-snes-ide-home")
            
            if result.failed:
                raise RuntimeError(f"Failed to get SNES-IDE home directory. "
                                 f"Error: {result.stderr}")
                
            home_path = result.stdout.strip()
            if not home_path:
                raise RuntimeError("SNES-IDE home directory path is empty.")
                
            return home_path
            
        except Exception as e:
            raise RuntimeError(f"Could not determine SNES-IDE home directory: {e}")

    def validate(self) -> None:
        """Validate project creation prerequisites."""
        try:
            # Check parent directory exists and is writable
            if not self.parent_dir.exists():
                raise ValueError(f"Parent directory does not exist: {self.parent_dir}")
                
            if not self.parent_dir.is_dir():
                raise ValueError(f"Parent path is not a directory: {self.parent_dir}")
                
            # Check if we can write to the parent directory
            if not os.access(self.parent_dir, os.W_OK):
                raise ValueError(f"No write permission for parent directory: {self.parent_dir}")
                
            # Check if project directory already exists
            if self.project_path.exists():
                raise ValueError(f"Project directory already exists: {self.project_path}")
                
            # Validate project name again (defensive programming)
            if not platform_manager.validate_project_name(self.project_name):
                error_msg = get_validation_error_message(self.project_name)
                raise ValueError(f"Invalid project name: {error_msg}")
                
        except ValueError as e:
            print(f"Validation Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error during validation: {e}")
            sys.exit(1)

    def run(self) -> NoReturn:
        """Run the project creation process with comprehensive error handling."""
        print(f"Creating JavaSnes project '{self.project_name}'...")
        print(f"Parent directory: {self.parent_dir}")
        print(f"Project will be created at: {self.project_path}")
        
        try:
            # Validate prerequisites
            self.validate()
            
            # Get SNES-IDE home and template path
            print("Locating SNES-IDE installation...")
            snes_home = Path(self.get_home_path())
            print(f"SNES-IDE home: {snes_home}")
            
            template_path = platform_manager.get_template_path("javasnes/template", snes_home)
            print(f"Template path: {template_path}")
            
            # Verify template exists
            if not template_path.exists():
                raise RuntimeError(f"JavaSnes template not found at: {template_path}")
                
            if not template_path.is_dir():
                raise RuntimeError(f"Template path is not a directory: {template_path}")
            
            # Check if target directory already exists (copy_template_safely will handle creation)
            if self.project_path.exists():
                raise RuntimeError(f"Project directory already exists: {self.project_path}")
            
            # Copy template safely (this will create the target directory)
            print("Copying template files...")
            success = platform_manager.copy_template_safely(
                template_path, 
                self.project_path, 
                overwrite=False
            )
            
            if not success:
                raise RuntimeError("Failed to copy template files to project directory.")
            
            print(f"✓ Successfully created JavaSnes project '{self.project_name}'")
            print(f"✓ Project location: {self.project_path}")
            print("✓ Template files copied successfully")
            print("\nYour JavaSnes project is ready for development!")
            print("📝 Next steps:")
            print("   1. Open your project directory in your preferred Java IDE")
            print("   2. Review the template code and documentation")
            print("   3. Start building your SNES game in Java!")
            
            sys.exit(0)
            
        except RuntimeError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nProject creation cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"Unexpected error: {e}")
            sys.exit(1)


def main():
    """Main entry point with command-line argument support."""
    parser = argparse.ArgumentParser(
        description="Create a new JavaSnes project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Interactive mode with GUI dialogs
  %(prog)s --help                       # Show this help message
  
This script will:
1. Ask you to select a parent directory
2. Ask for a project name (with validation)
3. Create a new subdirectory with your project
4. Copy the JavaSnes template files

Project names must:
• Start with a letter (A-Z, a-z) or underscore (_)
• Contain only letters, numbers, underscore (_), and hyphen (-)
• Not be a reserved system name (Windows: CON, PRN, etc.)
• Not start with a dot (.) on Unix systems
• Follow Java package naming conventions

Note: JavaSnes allows you to develop SNES games using Java syntax
and tooling, while targeting the native SNES hardware.
        """
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='JavaSnes Project Creator v1.0'
    )
    
    args = parser.parse_args()
    
    try:
        print("=== JavaSnes Project Creator ===")
        print("This tool will help you create a new JavaSnes project.")
        print("JavaSnes enables SNES development using familiar Java syntax!\n")
        
        creator = ProjectCreator()
        creator.run()
        
    except KeyboardInterrupt:
        print("\nProject creation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
