#!/usr/bin/env python3
"""Main entry point for the SNES Installer."""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from snes_installer.installer import ToolInstaller, add_to_path, setup_ides
# Defer importing the TUI until it's needed to keep CLI-only runs lightweight
SNESInstallerTUI = None


def main() -> None:
    """Main entry point with CLI argument parsing."""
    global SNESInstallerTUI
    parser = argparse.ArgumentParser(
        description="SNES Development Tools Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m snes_installer                    # Interactive TUI mode
  python -m snes_installer --tools ca65 asar  # Install specific tools
  python -m snes_installer --all              # Install all tools
  python -m snes_installer --list             # List available tools
        """,
    )

    parser.add_argument(
        "--tools", "-t", nargs="+", metavar="TOOL", help="Install specific tools"
    )

    parser.add_argument("--all", "-a", action="store_true", help="Install all tools")

    parser.add_argument(
        "--list", "-l", action="store_true", help="List available tools"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't download, build, or configure; just show what would happen",
    )

    parser.add_argument(
        "--install-dir",
        metavar="DIR",
        help="Install tools under a specific directory (default ~/.snes_tools).",
    )

    parser.add_argument(
        "--min-space",
        type=int,
        metavar="MB",
        default=200,
        help="Minimum free disk space in MB required before building tools (default 200).",
    )

    args = parser.parse_args()

    # Default config path (next to this module). If the package was installed
    # this file may not be present in site-packages during development runs
    # so provide a few sensible fallbacks (workspace `src/`, env override).
    config_file = Path(__file__).parent / "tools_config.json"

    # Allow override via environment variable for developers/tests
    import os

    env_path = os.environ.get("SNES_INSTALLER_CONFIG")
    if env_path:
        config_file = Path(env_path)

    # If default doesn't exist (e.g., running from an installed package),
    # try common workspace locations: `./src/snes_installer/tools_config.json`
    if not config_file.exists():
        alt = Path.cwd() / "src" / "snes_installer" / "tools_config.json"
        if alt.exists():
            config_file = alt
        else:
            # try one level up from cwd (in case running from project root)
            alt2 = Path.cwd().parent / "src" / "snes_installer" / "tools_config.json"
            if alt2.exists():
                config_file = alt2
    install_dir = Path(args.install_dir) if args.install_dir else None
    min_space_bytes = int(args.min_space) * 1024 * 1024
    installer = ToolInstaller(
        config_file,
        dry_run=args.dry_run,
        min_free_bytes=min_space_bytes,
        install_dir=install_dir,
    )

    # Handle different modes
    if args.list:
        # List available tools
        tools_config = installer.load_config()
        print("Available tools:")
        for tool in tools_config["tools"]:
            status = "✓" if installer.is_tool_installed(tool["name"]) else "✗"
            print(
                f"  {status} {tool['name']}: {tool.get('description', 'No description')}"
            )
        return

    if args.tools or args.all:
        # CLI installation mode
        tools_config = installer.load_config()
        if args.all:
            tools_to_install = [tool["name"] for tool in tools_config["tools"]]
        else:
            tools_to_install = args.tools or []

        print(f"Installing tools: {', '.join(tools_to_install)}")
        installer.install_selected_tools(tools_to_install)
        add_to_path()
        setup_ides()
        print("Installation complete!")
        return

    # Default: TUI mode — import the TUI implementation only when required
    if SNESInstallerTUI is None:
        from snes_installer.tui import SNESInstallerTUI as _TUIClass
        SNESInstallerTUI = _TUIClass

    tui = SNESInstallerTUI(
        config_file,
        install_dir=install_dir,
        min_free_bytes=min_space_bytes,
        dry_run=args.dry_run,
    )
    tui.run()


if __name__ == "__main__":
    main()
