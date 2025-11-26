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


def main() -> None:
    """Main function."""
    config_file = Path(__file__).parent / "tools_config.json"
    installer = ToolInstaller(config_file)
    installer.install_tools()


if __name__ == "__main__":
    main()