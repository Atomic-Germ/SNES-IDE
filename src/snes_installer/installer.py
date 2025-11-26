"""SNES Installer main module."""

import json
import logging
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
        archive_path = tool_dir / Path(tool['url']).name
        extract_dir = tool_dir / 'source'
        self.extract_archive(archive_path, extract_dir)
        
        # Find the extracted directory (assuming it's the only one or named after tool)
        subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if subdirs:
            build_dir = subdirs[0]
        else:
            build_dir = extract_dir
        
        build_cmds = tool.get('build_commands', {}).get(sys.platform, [])
        for cmd in build_cmds:
            logger.info(f"Running: {cmd}")
            subprocess.run(cmd, cwd=build_dir, shell=True, check=True)

    def configure_tool(self, tool: Dict) -> None:
        """Configure a tool after installation."""
        name = tool['name']
        logger.info(f"Configuring {name}")
        # Placeholder: could set environment variables, create symlinks, etc.
        # For now, just log
        pass

    def install_tools(self) -> None:
        """Install all tools defined in config."""
        self.install_dir.mkdir(parents=True, exist_ok=True)
        for tool in self.config['tools']:
            try:
                logger.info(f"Installing {tool['name']}")
                # Download
                if 'url' in tool:
                    tool_dir = self.install_dir / tool['name']
                    archive_name = Path(tool['url']).name
                    archive_path = tool_dir / archive_name
                    if not archive_path.exists():
                        self.download_file(tool['url'], archive_path)
                    else:
                        logger.info(f"Archive already exists: {archive_path}")
                # Build
                self.build_tool(tool)
                # Configure
                self.configure_tool(tool)
                logger.info(f"Successfully installed {tool['name']}")
            except Exception as e:
                logger.error(f"Failed to install {tool['name']}: {e}")
                continue


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


def main() -> None:
    """Main function."""
    config_file = Path(__file__).parent / "tools_config.json"
    installer = ToolInstaller(config_file)
    installer.install_tools()
    setup_ides()


if __name__ == "__main__":
    main()