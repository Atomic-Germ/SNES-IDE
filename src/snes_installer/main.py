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

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't download, build, or configure; just show what would happen"
    )

    parser.add_argument(
        "--install-dir",
        metavar="DIR",
        help="Install tools under a specific directory (default ~/.snes_tools)."
    )

    parser.add_argument(
        "--min-space",
        type=int,
        metavar="MB",
        default=200,
        help="Minimum free disk space in MB required before building tools (default 200)."
    )

    args = parser.parse_args()

    config_file = Path(__file__).parent / "tools_config.json"
    install_dir = Path(args.install_dir) if args.install_dir else None
    min_space_bytes = int(args.min_space) * 1024 * 1024
    installer = ToolInstaller(config_file, dry_run=args.dry_run, min_free_bytes=min_space_bytes, install_dir=install_dir)

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
    tui = SNESInstallerTUI(config_file, install_dir=install_dir, min_free_bytes=min_space_bytes, dry_run=args.dry_run)
    tui.run()


if __name__ == "__main__":
    main()