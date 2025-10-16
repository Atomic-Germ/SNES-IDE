from pathlib import Path
from re import match, sub
from os import path
import subprocess
import shutil

class ProjectCreator:

    def __init__(self):
        """Initialize the project creator with user input for project name and path."""

        print("**Welcome to the SNES-IDE project creator!**")
        print("This tool will help you create a new SNES-IDE project.")
        print("Please follow the instructions below to create your project.\n")

        print("Write down the name of your new project:\n")
        self.project_name = input()

        print("Write down the Full path of the folder you want to create a project: \n(Use C:\\\\foo\\\\theFolder structure)\n\n")
        self.full_path = input()

    
    @staticmethod
    def get_executable_path():
        """Get the path of the executable or script based on whether the script is frozen (PyInstaller) or not."""

        if getattr(sys, 'frozen', False):
            # PyInstaller executable
            print("executable path mode chosen")

            return str(path.dirname(sys.executable))
        
        else:
            # Normal script
            print("Python script path mode chosen")

            return str(path.dirname(path.abspath(__file__)))


    def sanitize_project_name(self, name: str) -> str:
        """
        Sanitize a project name to make it filesystem-safe.
        
        Args:
            name: The original project name
            
        Returns:
            A sanitized project name safe for filesystem use
        """
        if not name:
            return "unnamed_project"
        
        # Trim whitespace
        name = name.strip()
        
        # Replace invalid characters with underscores
        # Allow: letters, numbers, underscores, hyphens
        # Replace everything else with underscores
        sanitized = sub(r'[^A-Za-z0-9_-]', '_', name)
        
        # Remove multiple consecutive underscores
        sanitized = sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        # Ensure it's not empty after sanitization
        if not sanitized:
            return "unnamed_project"
        
        # Limit length to reasonable filesystem limits (255 chars is common)
        if len(sanitized) > 255:
            sanitized = sanitized[:255].rstrip('_')
        
        return sanitized


    def run(self):
        """Run the project creation process."""

        # Create the directory if it doesn't exist
        Path(self.full_path).mkdir(parents=True, exist_ok=True)

        # Sanitize the project name
        original_name = self.project_name
        self.project_name = self.sanitize_project_name(self.project_name)
        
        # Show user the sanitized name if it changed
        if original_name != self.project_name:
            print(f"Project name sanitized from '{original_name}' to '{self.project_name}'")

        target_path = path.join(self.full_path, self.project_name)
        template_path = path.abspath(path.join(self.get_executable_path(), "..", "..", "libs", "template"))

        shutil.copytree(template_path, target_path)

        input("Project created successfully! Press any key to exit...")


if __name__ == "__main__":

    ProjectCreator().run()
