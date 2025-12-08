"""Project file browser with filtering for relevant files."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import DirectoryTree


class ProjectTree(DirectoryTree):
    """Project file browser with filtering for relevant files.
    
    Filters out common build artifacts, cache directories, and
    hidden folders while showing source code, assets, and config files.
    """
    
    DEFAULT_CSS = """
    ProjectTree {
        height: auto;
        max-height: 20;
        background: $panel;
        scrollbar-gutter: stable;
    }
    """

    # File extensions to show
    SHOW_EXTENSIONS = {
        # C/C++
        ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
        # Assembly
        ".asm", ".s", ".inc",
        # Scripting/high-level
        ".py", ".java", ".cs",
        # Config/data
        ".json", ".yaml", ".yml", ".toml",
        # Documentation
        ".md", ".rst", ".txt",
        # Shell/scripts
        ".sh", ".bash", ".bat", ".cmd", ".ps1",
        # Web
        ".xml", ".html", ".css",
        # Other languages
        ".lua", ".rb", ".rs", ".go",
        # Graphics files for tile editor
        ".png", ".bmp", ".gif", ".jpg", ".jpeg",
        # SNES-specific formats
        ".pic", ".pal", ".map", ".chr", ".sfc", ".smc",
    }
    
    # Filenames to always show (case-insensitive)
    SHOW_NAMES = {
        "makefile", "gnumakefile", "cmakelists.txt", 
        "readme", "license", "copying", "changelog",
        ".gitignore", ".gitattributes",
    }
    
    # Directories to hide
    HIDE_DIRS = {
        "__pycache__", ".git", ".svn", ".hg", 
        "node_modules", ".venv", "venv", ".env",
        "build", "dist", ".tox", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", "target",
        ".idea", ".vscode",
    }

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Filter paths to show only relevant files.
        
        Args:
            paths: List of paths in the current directory
            
        Returns:
            Filtered and sorted list of paths
        """
        filtered = []
        for path in paths:
            name_lower = path.name.lower()
            
            if path.is_dir():
                # Hide certain directories
                if name_lower not in self.HIDE_DIRS:
                    filtered.append(path)
            else:
                # Show files with relevant extensions or special names
                if (path.suffix.lower() in self.SHOW_EXTENSIONS or 
                    name_lower in self.SHOW_NAMES or
                    any(name_lower.startswith(n) for n in self.SHOW_NAMES)):
                    filtered.append(path)
        
        # Sort: directories first, then alphabetically by name
        return sorted(filtered, key=lambda p: (not p.is_dir(), p.name.lower()))
