#!/usr/bin/env python3
"""
SNES Game Project Build Tool

Command-line interface for building SNES games:
  snes-build              - Build with default config (snes-project.yaml)
  snes-build --clean      - Clean and rebuild
  snes-build --config     - Specify config file
  snes-build --watch      - Watch for changes and rebuild
  snes-build --run        - Build and launch in emulator
"""

import sys
import argparse
from pathlib import Path
import json

from project_builder import ProjectBuilder
from project_config import ProjectConfigManager


def main():
    parser = argparse.ArgumentParser(
        prog="snes-build",
        description="Build SNES games with automated asset and code pipelines"
    )
    
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Project configuration file (default: snes-project.yaml)"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts before building"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch source files for changes and rebuild"
    )
    
    parser.add_argument(
        "--run",
        action="store_true",
        help="Build and launch in emulator"
    )
    
    args = parser.parse_args()
    
    # Find project configuration
    config_path = args.config
    if not config_path:
        config_path = ProjectConfigManager.find_project_file()
        if not config_path:
            print("❌ Error: No project configuration found")
            print("   Create snes-project.yaml in current directory")
            return 1
    
    if not config_path.exists():
        print(f"❌ Error: Config file not found: {config_path}")
        return 1
    
    try:
        # Load project configuration
        print(f"📖 Loading {config_path}...")
        project_config = ProjectConfigManager.load(config_path)
        
        # Convert to build configuration
        build_config = project_config.to_build_config()
        
        # Create builder
        builder = ProjectBuilder(build_config)
        
        # Run build
        success = builder.build(clean=args.clean)
        
        if not success:
            return 1
        
        # Optional: Run in emulator
        if args.run:
            print(f"\n🎮 Launching in emulator...")
            # TODO: Launch emulator with ROM
            print(f"   ROM: {build_config.output_rom}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
