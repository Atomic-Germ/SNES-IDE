from pathlib import Path
from re import match, sub
from os import path
import subprocess
import shutil
import sys
import json

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


    def detect_editors(self) -> list:
        """
        Detect which code editors are available on the system.
        
        Returns:
            List of available editors ('vscode', 'vim', 'emacs', etc.)
        """
        available_editors = []
        
        # Check for VS Code
        if self.is_command_available('code'):
            available_editors.append('vscode')
        
        # Check for Vim
        if self.is_command_available('vim'):
            available_editors.append('vim')
        
        # Check for Emacs
        if self.is_command_available('emacs'):
            available_editors.append('emacs')
        
        # Check for Sublime Text
        if self.is_command_available('subl'):
            available_editors.append('sublime')
        
        return available_editors


    def is_command_available(self, command: str) -> bool:
        """
        Check if a command is available on the system.
        
        Args:
            command: Command name to check
            
        Returns:
            True if command is available, False otherwise
        """
        try:
            subprocess.run([command, '--version'], 
                         capture_output=True, 
                         check=True, 
                         timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False


    def create_editor_configs(self, project_path: str) -> None:
        """
        Create editor-specific configuration files for the project.
        
        Args:
            project_path: Path to the created project directory
        """
        editors = self.detect_editors()
        
        if not editors:
            print("No supported code editors detected. Skipping editor configuration.")
            return
        
        print(f"Detected editors: {', '.join(editors)}")
        print("Creating editor configurations...")
        
        for editor in editors:
            try:
                if editor == 'vscode':
                    self.create_vscode_config(project_path)
                elif editor == 'vim':
                    self.create_vim_config(project_path)
                elif editor == 'emacs':
                    self.create_emacs_config(project_path)
                elif editor == 'sublime':
                    self.create_sublime_config(project_path)
                print(f"✓ Created {editor} configuration")
            except Exception as e:
                print(f"⚠ Failed to create {editor} configuration: {e}")


    def create_vscode_config(self, project_path: str) -> None:
        """
        Create VS Code configuration files for SNES development.
        """
        vscode_dir = Path(project_path) / '.vscode'
        vscode_dir.mkdir(exist_ok=True)
        
        # settings.json - C/C++ and assembly language settings
        settings = {
            "C_Cpp.default.includePath": [
                "${workspaceFolder}/**",
                "${workspaceFolder}/snes/**"
            ],
            "C_Cpp.default.defines": [
                "SNES"
            ],
            "C_Cpp.default.compilerPath": "gcc",
            "C_Cpp.default.cStandard": "c99",
            "C_Cpp.default.cppStandard": "c++98",
            "files.associations": {
                "*.asm": "asm-collection",
                "*.inc": "asm-collection",
                "data.asm": "asm-collection",
                "hdr.asm": "asm-collection"
            },
            "asm-collection.includePaths": [
                "${workspaceFolder}",
                "${workspaceFolder}/snes"
            ],
            "makefile.configureOnOpen": True,
            "files.exclude": {
                "**/*.o": True,
                "**/*.obj": True,
                "**/*.exe": True,
                "**/*.bin": True,
                "**/*.smc": True,
                "**/*.sfc": True
            },
            "search.exclude": {
                "**/node_modules": True,
                "**/build": True,
                "**/dist": True
            }
        }
        
        with open(vscode_dir / 'settings.json', 'w') as f:
            import json
            json.dump(settings, f, indent=2)
        
        # tasks.json - build tasks
        tasks = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "Build SNES Project",
                    "type": "shell",
                    "command": "make",
                    "group": {
                        "kind": "build",
                        "isDefault": True
                    },
                    "presentation": {
                        "echo": True,
                        "reveal": "always",
                        "focus": False,
                        "panel": "shared"
                    },
                    "problemMatcher": [
                        "$gcc"
                    ]
                },
                {
                    "label": "Clean Build",
                    "type": "shell",
                    "command": "make clean",
                    "group": "build",
                    "presentation": {
                        "echo": True,
                        "reveal": "always",
                        "focus": False,
                        "panel": "shared"
                    }
                },
                {
                    "label": "Run Emulator",
                    "type": "shell",
                    "command": "bsnes ${workspaceFolder}/game.sfc",
                    "group": "test",
                    "presentation": {
                        "echo": True,
                        "reveal": "always",
                        "focus": False,
                        "panel": "shared"
                    }
                }
            ]
        }
        
        with open(vscode_dir / 'tasks.json', 'w') as f:
            json.dump(tasks, f, indent=2)
        
        # launch.json - debugging configuration
        launch = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Debug SNES Game",
                    "type": "cppdbg",
                    "request": "launch",
                    "program": "${workspaceFolder}/game.sfc",
                    "args": [],
                    "stopAtEntry": False,
                    "cwd": "${workspaceFolder}",
                    "environment": [],
                    "externalConsole": True,
                    "MIMode": "gdb",
                    "miDebuggerPath": "gdb",
                    "setupCommands": [
                        {
                            "description": "Enable pretty-printing for gdb",
                            "text": "-enable-pretty-printing",
                            "ignoreFailures": True
                        }
                    ],
                    "preLaunchTask": "Build SNES Project"
                }
            ]
        }
        
        with open(vscode_dir / 'launch.json', 'w') as f:
            json.dump(launch, f, indent=2)


    def create_vim_config(self, project_path: str) -> None:
        """
        Create Vim configuration file for SNES development.
        """
        vimrc_content = r'''" SNES Development Vim Configuration
" Auto-generated for SNES-IDE project

" Basic settings
set nocompatible
set encoding=utf-8
set fileencoding=utf-8

" Indentation
set tabstop=4
set shiftwidth=4
set expandtab
set smarttab
set autoindent
set smartindent

" Search
set incsearch
set hlsearch
set ignorecase
set smartcase

" Display
set number
set relativenumber
set showcmd
set showmode
set ruler
set cursorline
syntax on

" File type specific settings
autocmd FileType c,cpp setlocal cindent
autocmd FileType asm setlocal syntax=asm
autocmd FileType make setlocal noexpandtab

" SNES-specific file associations
autocmd BufRead,BufNewFile *.asm set filetype=asm
autocmd BufRead,BufNewFile *.inc set filetype=asm
autocmd BufRead,BufNewFile data.asm set filetype=asm
autocmd BufRead,BufNewFile hdr.asm set filetype=asm

" Build shortcuts
nnoremap <F5> :make<CR>
nnoremap <F6> :make clean<CR>

" Quick navigation
nnoremap <C-n> :Explore<CR>

" Comments
autocmd FileType c,cpp nnoremap <C-c> :s/^/\/\//<CR>
autocmd FileType asm nnoremap <C-c> :s/^/;/<CR>

" Remove trailing whitespace on save
autocmd BufWritePre * :%s/\s\+$//e

" Set path for includes
set path+=./snes,./

" Highlight long lines
highlight OverLength ctermbg=red ctermfg=white guibg=#592929
match OverLength /\%81v.\+/
'''
        
        with open(Path(project_path) / '.vimrc', 'w') as f:
            f.write(vimrc_content)


    def create_emacs_config(self, project_path: str) -> None:
        """
        Create Emacs configuration for SNES development.
        """
        emacs_config = r''';; SNES Development Emacs Configuration
;; Auto-generated for SNES-IDE project

;; Basic settings
(setq-default indent-tabs-mode nil)
(setq-default tab-width 4)
(setq c-basic-offset 4)

;; Enable line numbers
(global-linum-mode t)
(global-hl-line-mode t)

;; File associations
(add-to-list 'auto-mode-alist '("\\.asm\\'" . asm-mode))
(add-to-list 'auto-mode-alist '("\\.inc\\'" . asm-mode))
(add-to-list 'auto-mode-alist '("data\\.asm" . asm-mode))
(add-to-list 'auto-mode-alist '("hdr\\.asm" . asm-mode))

;; C/C++ mode settings
(add-hook 'c-mode-hook
          (lambda ()
            (c-set-style "linux")
            (setq c-basic-offset 4)))

;; Assembly mode settings
(add-hook 'asm-mode-hook
          (lambda ()
            (setq asm-comment-char ?\;)))

;; Build commands
(global-set-key (kbd "<f5>") 'compile)
(global-set-key (kbd "<f6>") (lambda () (interactive) (compile "make clean")))

;; Remove trailing whitespace
(add-hook 'before-save-hook 'delete-trailing-whitespace)

;; Set include paths
(setq cc-search-directories '("." "./snes" "./include"))

;; Highlight long lines
(require 'whitespace)
(setq whitespace-line-column 80)
(setq whitespace-style '(face lines-tail))
(global-whitespace-mode t)
'''
        
        with open(Path(project_path) / '.dir-locals.el', 'w') as f:
            f.write(emacs_config)


    def create_sublime_config(self, project_path: str) -> None:
        """
        Create Sublime Text project file for SNES development.
        """
        sublime_project = {
            "folders": [
                {
                    "path": "."
                }
            ],
            "settings": {
                "tab_size": 4,
                "translate_tabs_to_spaces": True,
                "trim_trailing_white_space_on_save": True
            },
            "build_systems": [
                {
                    "name": "Build SNES Project",
                    "cmd": ["make"],
                    "working_dir": "${project_path}",
                    "keyfiles": ["Makefile"],
                    "variants": [
                        {
                            "name": "Clean",
                            "cmd": ["make", "clean"]
                        }
                    ]
                }
            ]
        }
        
        import json
        with open(Path(project_path) / f"{self.project_name}.sublime-project", 'w') as f:
            json.dump(sublime_project, f, indent=2)


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
        
        # Calculate template path based on execution mode
        if getattr(sys, 'frozen', False):
            # PyInstaller executable - libs are in the same directory as executable
            template_path = path.abspath(path.join(self.get_executable_path(), "libs", "template"))
        else:
            # Development mode - libs are two levels up from src/tools
            template_path = path.abspath(path.join(self.get_executable_path(), "..", "..", "libs", "template"))

        shutil.copytree(template_path, target_path)

        # Create editor-specific configuration files
        self.create_editor_configs(target_path)

        input("Project created successfully! Press any key to exit...")


if __name__ == "__main__":

    ProjectCreator().run()
