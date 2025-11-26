#!/usr/bin/env python3
"""Main entry point for the SNES Installer."""

import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from snes_installer.installer import ToolInstaller, add_to_path, setup_ides
from snes_installer.tui import SNESInstallerTUI


def main() -> None:
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="SNES Development Tools Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m snes_installer                    # Interactive TUI mode
  python -m snes_installer --tools ca65 asar  # Install specific tools
  python -m snes_installer --all              # Install all tools
  python -m snes_installer --list             # List available tools
        """
    )

    parser.add_argument(
        "--tools", "-t",
        nargs="+",
        metavar="TOOL",
        help="Install specific tools"
    )

    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Install all tools"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available tools"
    )

    args = parser.parse_args()

    config_file = Path(__file__).parent / "tools_config.json"
    installer = ToolInstaller(config_file)

    # Handle different modes
    if args.list:
        # List available tools
        tools_config = installer.load_config()
        print("Available tools:")
        for tool in tools_config['tools']:
            status = "✓" if installer.is_tool_installed(tool["name"]) else "✗"
            print(f"  {status} {tool['name']}: {tool.get('description', 'No description')}")
        return

    if args.tools or args.all:
        # CLI installation mode
        tools_config = installer.load_config()
        if args.all:
            tools_to_install = [tool["name"] for tool in tools_config['tools']]
        else:
            tools_to_install = args.tools or []

        print(f"Installing tools: {', '.join(tools_to_install)}")
        installer.install_selected_tools(tools_to_install)
        add_to_path()
        setup_ides()
        print("Installation complete!")
        return

    # Default: TUI mode
    tui = SNESInstallerTUI(config_file)
    tui.run()


if __name__ == "__main__":
    main()