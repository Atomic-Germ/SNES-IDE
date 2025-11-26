"""SNES Installer main module."""

import json
import logging
import platform
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ToolInstaller:
    """Handles downloading, building, and configuring SNES development tools."""

    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config = self.load_config()
        self.install_dir = Path.home() / ".snes_tools"

    def load_config(self) -> Dict:
        """Load tool configuration from JSON file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file {self.config_file} not found")
        with open(self.config_file, 'r') as f:
            return json.load(f)

    def need_patch(self) -> bool:
        """Check if we need to patch calloc calls for 16k page systems."""
        # Check for Apple Silicon (Darwin + ARM64) or Asahi Linux (Linux + ARM64)
        is_arm64 = platform.machine() == 'arm64' or platform.machine() == 'aarch64'
        is_supported_os = platform.system() in ['Darwin', 'Linux']
        
        if not (is_supported_os and is_arm64):
            return False
            
        try:
            result = subprocess.run(['getconf', 'PAGE_SIZE'], capture_output=True, text=True, check=True)
            page_size = result.stdout.strip()
            return page_size == '16384'
        except subprocess.CalledProcessError:
            return False

    def patch_source(self, build_dir: Path) -> None:
        """Apply patches to fix calloc argument order."""
        logger.info("Applying calloc patches for 16k page systems")
        # Use a more specific pattern that only matches calloc calls
        cmd = [
            'find', '.', '-name', '*.c', '-o', '-name', '*.cpp', '-o', '-name', '*.cc', '|',
            'xargs', 'sed', '-i', 's/calloc(sizeof(\\([^,]*\\)), \\([^)]*\\))/calloc(\\2, sizeof(\\1))/g'
        ]
        subprocess.run(cmd, cwd=build_dir, check=True, shell=True)

    def download_file(self, url: str, dest: Path) -> None:
        """Download a file from URL to destination."""
        logger.info(f"Downloading {url} to {dest}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    def extract_archive(self, archive_path: Path, extract_to: Path) -> None:
        """Extract an archive to the specified directory."""
        logger.info(f"Extracting {archive_path} to {extract_to}")
        extract_to.mkdir(parents=True, exist_ok=True)
        if archive_path.name.endswith('.tar.gz') or archive_path.name.endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(extract_to)
        elif archive_path.suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        else:
            raise ValueError(f"Unsupported archive format: {archive_path}")

    def build_tool(self, tool: Dict) -> None:
        """Build a tool based on its configuration."""
        name = tool['name']
        logger.info(f"Building {name}")
        tool_dir = self.install_dir / name
        
        # Handle platform-specific URLs
        url = tool['url']
        if isinstance(url, dict):
            url = url.get(sys.platform, url.get('linux', ''))  # fallback to linux if platform not found
        
        archive_path = tool_dir / Path(url).name
        extract_dir = tool_dir / 'source'
        self.extract_archive(archive_path, extract_dir)
        
        # Find the extracted directory (assuming it's the only one or named after tool)
        subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if subdirs:
            build_dir = subdirs[0]
        else:
            build_dir = extract_dir
        
        # Patch for Apple Silicon 16k pages if needed
        if (name in ['wla-dx', 'mesen']) and self.need_patch():
            self.patch_source(build_dir)
        
        build_cmds = tool.get('build_commands', {}).get(sys.platform, [])
        if build_cmds:
            for cmd in build_cmds:
                logger.info(f"Running: {cmd}")
                subprocess.run(cmd, cwd=build_dir, shell=True, check=True)
        else:
            logger.info(f"No build commands for {name}, skipping build step")

    def configure_tool(self, tool: Dict) -> None:
        """Configure a tool after installation."""
        name = tool['name']
        logger.info(f"Configuring {name}")
        # Copy binary to bin directory
        tool_dir = self.install_dir / name
        extract_dir = tool_dir / 'source'
        subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if subdirs:
            build_dir = subdirs[0]
        else:
            build_dir = extract_dir
        
        bin_dir = self.install_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        
        binary_path_str = tool.get('binary_path', '')
        if binary_path_str:
            binary_path = build_dir / binary_path_str
            if binary_path.exists():
                import shutil
                dest = bin_dir / Path(binary_path_str).name
                if sys.platform == "win32":
                    dest = dest.with_suffix('.exe')
                shutil.copy(binary_path, dest)
                dest.chmod(0o755)  # Make executable
                logger.info(f"Copied {binary_path} to {dest}")
            else:
                logger.warning(f"Binary not found at {binary_path}")
        elif name == 'pvsneslib':
            # Special handling for PVSnesLib - it's a pre-built framework
            import shutil
            
            # Copy compiler binaries
            compiler_dir = build_dir / "compiler"
            if compiler_dir.exists():
                for item in compiler_dir.rglob("*"):
                    if item.is_file() and item.suffix != '':  # executable files
                        rel_path = item.relative_to(compiler_dir)
                        dest = bin_dir / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(item, dest)
                        logger.info(f"Copied compiler binary {item} to {dest}")
            
            # Copy devkitsnes binaries
            devkitsnes_dir = build_dir / "devkitsnes"
            if devkitsnes_dir.exists():
                bin_src = devkitsnes_dir / "bin"
                if bin_src.exists():
                    for item in bin_src.iterdir():
                        if item.is_file():
                            dest = bin_dir / item.name
                            shutil.copy(item, dest)
                            logger.info(f"Copied devkitsnes binary {item} to {dest}")
                
                # Copy tools
                tools_dir = devkitsnes_dir / "tools"
                if tools_dir.exists():
                    for item in tools_dir.rglob("*"):
                        if item.is_file():
                            rel_path = item.relative_to(tools_dir)
                            dest = bin_dir / rel_path
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy(item, dest)
                            logger.info(f"Copied tool {item} to {dest}")
            
            # Copy library files
            lib_dir = self.install_dir / "lib" / name
            lib_dir.mkdir(parents=True, exist_ok=True)
            pvsneslib_dir = build_dir / "pvsneslib"
            if pvsneslib_dir.exists():
                for item in pvsneslib_dir.iterdir():
                    if item.is_file():
                        shutil.copy(item, lib_dir)
                    elif item.is_dir():
                        shutil.copytree(item, lib_dir / item.name, dirs_exist_ok=True)
                logger.info(f"Copied library files to {lib_dir}")
            
            # Copy include files
            include_dir = self.install_dir / "include" / name
            include_dir.mkdir(parents=True, exist_ok=True)
            include_src = build_dir / "pvsneslib" / "include"
            if include_src.exists():
                shutil.copytree(include_src, include_dir, dirs_exist_ok=True)
                logger.info(f"Copied include files to {include_dir}")
        else:
            # Handle libraries - copy include files
            include_dir = self.install_dir / "include" / name
            include_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            # Copy all files from build_dir to include_dir
            for item in build_dir.iterdir():
                if item.is_file():
                    shutil.copy(item, include_dir)
                elif item.is_dir() and not item.name.startswith('.'):
                    shutil.copytree(item, include_dir / item.name, dirs_exist_ok=True)
            logger.info(f"Copied library files to {include_dir}")

    def install_tools(self) -> None:
        """Install all tools defined in config."""
        self.install_dir.mkdir(parents=True, exist_ok=True)
        for tool in self.config['tools']:
            try:
                logger.info(f"Installing {tool['name']}")
                # Download
                if 'url' in tool:
                    tool_dir = self.install_dir / tool['name']
                    
                    # Handle platform-specific URLs
                    url = tool['url']
                    if isinstance(url, dict):
                        url = url.get(sys.platform, url.get('linux', ''))  # fallback to linux if platform not found
                    
                    if url:
                        archive_name = Path(url).name
                        archive_path = tool_dir / archive_name
                        if not archive_path.exists():
                            self.download_file(url, archive_path)
                        else:
                            logger.info(f"Archive already exists: {archive_path}")
                    else:
                        logger.warning(f"No URL found for {tool['name']} on platform {sys.platform}")
                        continue
                # Build
                self.build_tool(tool)
                # Configure
                self.configure_tool(tool)
                logger.info(f"Successfully installed {tool['name']}")
            except Exception as e:
                logger.error(f"Failed to install {tool['name']}: {e}")
                continue

    def is_tool_installed(self, tool_name: str) -> bool:
        """Check if a tool is already installed and available in PATH."""
        import shutil
        
        # Find the tool config
        tool_config = next((t for t in self.config['tools'] if t["name"] == tool_name), None)
        if not tool_config:
            return False
            
        # If binary_path is specified, check if that binary exists in PATH
        if tool_config.get('binary_path'):
            binary_name = Path(tool_config['binary_path']).name
            return shutil.which(binary_name) is not None
        
        # For libraries or tools with multiple binaries, check if installation directory exists
        tool_dir = self.install_dir / tool_name
        if tool_dir.exists():
            # For pvsneslib, check for key binaries
            if tool_name == "pvsneslib":
                return (self.install_dir / "bin" / "816-tcc").exists()
            # For libsfx, check for include files
            elif tool_name == "libsfx":
                return (self.install_dir / "include" / "libsfx").exists()
        
        # Fallback: check if the tool name itself is in PATH
        return shutil.which(tool_name) is not None

    def install_selected_tools(self, tool_names: List[str]) -> None:
        """Install only the specified tools."""
        for tool_name in tool_names:
            tool_config = next((t for t in self.config['tools'] if t["name"] == tool_name), None)
            if tool_config:
                try:
                    logger.info(f"Installing {tool_name}")
                    # Download
                    if 'url' in tool_config:
                        tool_dir = self.install_dir / tool_config['name']
                        
                        # Handle platform-specific URLs
                        url = tool_config['url']
                        if isinstance(url, dict):
                            url = url.get(sys.platform, url.get('linux', ''))  # fallback to linux if platform not found
                        
                        if url:
                            archive_name = Path(url).name
                            archive_path = tool_dir / archive_name
                            if not archive_path.exists():
                                self.download_file(url, archive_path)
                            else:
                                logger.info(f"Archive already exists: {archive_path}")
                        else:
                            logger.warning(f"No URL found for {tool_config['name']} on platform {sys.platform}")
                            continue
                    # Build
                    self.build_tool(tool_config)
                    # Configure
                    self.configure_tool(tool_config)
                    logger.info(f"Successfully installed {tool_name}")
                except Exception as e:
                    logger.error(f"Failed to install {tool_name}: {e}")
                    continue
            else:
                logger.warning(f"Tool '{tool_name}' not found in configuration")


def setup_ides() -> None:
    """Set up IDE integrations for SNES development."""
    logger.info("Setting up IDE integrations")
    platform = sys.platform
    if platform == "win32":
        setup_vscode_windows()
        setup_vim_windows()
        setup_notepad_plus_plus()
    else:  # linux, darwin
        setup_vscode_unix()
        setup_vim_unix()
        setup_neovim_unix()


def setup_vscode_unix() -> None:
    """Set up VS Code on Unix systems."""
    import shutil
    if shutil.which("code"):
        logger.info("Installing VS Code extensions for SNES development")
        # Install 6502 assembly extensions
        subprocess.run(["code", "--install-extension", "enginedesigns.retroassembler"], check=False)
        subprocess.run(["code", "--install-extension", "tlgkccampbell.code-ca65"], check=False)
        # Install general assembly support
        subprocess.run(["code", "--install-extension", "ms-vscode.cpptools"], check=False)
        logger.info("VS Code setup complete")
    else:
        logger.info("VS Code not found. Install VS Code and run: code --install-extension enginedesigns.retroassembler tlgkccampbell.code-ca65")


def setup_vscode_windows() -> None:
    """Set up VS Code on Windows."""
    import shutil
    if shutil.which("code"):
        logger.info("Installing VS Code extensions for SNES development")
        subprocess.run(["code", "--install-extension", "enginedesigns.retroassembler"], check=False)
        subprocess.run(["code", "--install-extension", "tlgkccampbell.code-ca65"], check=False)
        subprocess.run(["code", "--install-extension", "ms-vscode.cpptools"], check=False)
        logger.info("VS Code setup complete")
    else:
        logger.info("VS Code not found. Install VS Code and run: code --install-extension enginedesigns.retroassembler tlgkccampbell.code-ca65")


def setup_vim_unix() -> None:
    """Set up Vim on Unix systems."""
    vimrc = Path.home() / ".vimrc"
    syntax_config = '''
" SNES Assembly syntax
autocmd BufRead,BufNewFile *.asm set filetype=asm
autocmd BufRead,BufNewFile *.s set filetype=asm
syntax on
'''
    try:
        with open(vimrc, 'a') as f:
            f.write(syntax_config)
        logger.info("Vim syntax highlighting configured")
    except Exception as e:
        logger.warning(f"Could not configure Vim: {e}")


def setup_neovim_unix() -> None:
    """Set up NeoVim on Unix systems."""
    nvim_config = Path.home() / ".config" / "nvim" / "init.vim"
    nvim_config.parent.mkdir(parents=True, exist_ok=True)
    syntax_config = '''
" SNES Assembly syntax
autocmd BufRead,BufNewFile *.asm set filetype=asm
autocmd BufRead,BufNewFile *.s set filetype=asm
syntax on
'''
    try:
        with open(nvim_config, 'a') as f:
            f.write(syntax_config)
        logger.info("NeoVim syntax highlighting configured")
    except Exception as e:
        logger.warning(f"Could not configure NeoVim: {e}")


def setup_vim_windows() -> None:
    """Set up Vim on Windows."""
    vimrc = Path.home() / "_vimrc"
    syntax_config = '''
" SNES Assembly syntax
autocmd BufRead,BufNewFile *.asm set filetype=asm
autocmd BufRead,BufNewFile *.s set filetype=asm
syntax on
'''
    try:
        with open(vimrc, 'a') as f:
            f.write(syntax_config)
        logger.info("Vim syntax highlighting configured")
    except Exception as e:
        logger.warning(f"Could not configure Vim: {e}")


def setup_notepad_plus_plus() -> None:
    """Set up Notepad++ on Windows."""
    # Notepad++ uses User Defined Languages
    udl_path = Path.home() / "AppData" / "Roaming" / "Notepad++" / "userDefineLang.xml"
    udl_path.parent.mkdir(parents=True, exist_ok=True)
    # Simple assembly syntax definition
    udl_content = '''<?xml version="1.0" encoding="UTF-8"?>
<NotepadPlus>
    <UserLang name="SNES Assembly" ext="asm s">
        <Settings>
            <Global caseIgnored="yes"/>
            <TreatAsSymbol comment="yes" commentLine=";" commentStart="/*" commentEnd="*/"/>
            <Prefix words1="no" words2="no" words3="no" words4="no"/>
        </Settings>
        <KeywordLists>
            <Keywords name="Comments">; /* */</Keywords>
            <Keywords name="Numbers">0 1 2 3 4 5 6 7 8 9</Keywords>
            <Keywords name="Instructions">LDA STA INC DEC ADC SBC CMP AND ORA EOR ASL LSR ROL ROR JMP JSR RTS RTI BRA BEQ BNE BCS BCC BMI BPL BVS BVC CLC SEC CLI SEI CLV CLD SED</Keywords>
            <Keywords name="Directives">.org .db .dw .byte .word .include .macro .endmacro .if .endif</Keywords>
        </KeywordLists>
        <Styles>
            <WordsStyle name="DEFAULT" styleID="11" fgColor="000000" bgColor="FFFFFF" fontName="" fontStyle="0"/>
            <WordsStyle name="COMMENTS" styleID="1" fgColor="008000" bgColor="FFFFFF" fontName="" fontStyle="0"/>
            <WordsStyle name="NUMBERS" styleID="4" fgColor="FF0000" bgColor="FFFFFF" fontName="" fontStyle="0"/>
            <WordsStyle name="INSTRUCTIONS" styleID="5" fgColor="0000FF" bgColor="FFFFFF" fontName="" fontStyle="1"/>
            <WordsStyle name="DIRECTIVES" styleID="6" fgColor="800080" bgColor="FFFFFF" fontName="" fontStyle="1"/>
        </Styles>
    </UserLang>
</NotepadPlus>'''
    try:
        with open(udl_path, 'w') as f:
            f.write(udl_content)
        logger.info("Notepad++ syntax highlighting configured")
    except Exception as e:
        logger.warning(f"Could not configure Notepad++: {e}")


def add_to_path() -> None:
    """Add the tools bin directory to PATH in shell config files."""
    bin_dir = Path.home() / ".snes_tools" / "bin"
    path_export = f'\nexport PATH="{bin_dir}:$PATH"\n'
    
    # For bash
    bashrc = Path.home() / ".bashrc"
    try:
        with open(bashrc, 'a') as f:
            f.write(path_export)
        logger.info("Added to PATH in ~/.bashrc")
    except Exception as e:
        logger.warning(f"Could not update ~/.bashrc: {e}")
    
    # For zsh
    zshrc = Path.home() / ".zshrc"
    try:
        with open(zshrc, 'a') as f:
            f.write(path_export)
        logger.info("Added to PATH in ~/.zshrc")
    except Exception as e:
        logger.warning(f"Could not update ~/.zshrc: {e}")
    
    # For fish, if exists
    fish_config = Path.home() / ".config" / "fish" / "config.fish"
    if fish_config.exists():
        fish_path = f'\nset -x PATH "{bin_dir}" $PATH\n'
        try:
            with open(fish_config, 'a') as f:
                f.write(fish_path)
            logger.info("Added to PATH in ~/.config/fish/config.fish")
        except Exception as e:
            logger.warning(f"Could not update fish config: {e}")


def main() -> None:
    """Main function."""
    config_file = Path(__file__).parent / "tools_config.json"
    installer = ToolInstaller(config_file)
    installer.install_tools()
    add_to_path()
    setup_ides()


if __name__ == "__main__":
    main()


