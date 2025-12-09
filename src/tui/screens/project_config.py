"""
SNES Game Project Configuration File Format

Standard YAML/JSON format for SNES game projects that describes:
  • Project metadata
  • Build pipeline
  • Assets and compilation
  • ROM configuration
  • Bank layout

Example snes-project.yaml:
  
  project:
    name: MyGame
    sdk: pvsneslib
    version: "1.0.0"
  
  rom:
    type: lorom
    size: 2mb
    max_ram: 128kb
  
  assets:
    - name: sprites
      source: assets/sprites.png
      converter: png2snes
      args: [--mode, 4bpp]
    
    - name: music
      source: assets/music.wav
      converter: wav2brr
  
  compilation:
    targets:
      - name: main
        source: src/main.c
        language: c
      
      - name: startup
        source: src/startup.asm
        language: asm
    
    linker_script: src/link.ld
    optimization: O2
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from ..logic.project_builder import (
    BuildConfig, SDK, ROMType, Asset, CompileTarget
)


class ProjectConfigManager:
    """Load/save SNES game project configurations"""
    
    SUPPORTED_FORMATS = ["yaml", "yml", "json"]
    STANDARD_FILENAMES = ["snes-project.yaml", "snes-project.yml", "snes-project.json"]
    
    @staticmethod
    def find_project_file(search_dir: Path = Path(".")) -> Optional[Path]:
        """Find project configuration file in directory"""
        for filename in ProjectConfigManager.STANDARD_FILENAMES:
            candidate = search_dir / filename
            if candidate.exists():
                return candidate
        return None
    
    @staticmethod
    def load_yaml(path: Path) -> Dict[str, Any]:
        """Load YAML configuration"""
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML required for YAML support: pip install pyyaml")
        
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def load_json(path: Path) -> Dict[str, Any]:
        """Load JSON configuration"""
        with open(path, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def load(path: Path) -> "ProjectConfig":
        """Load project configuration from file"""
        
        if not path.exists():
            raise FileNotFoundError(f"Project file not found: {path}")
        
        suffix = path.suffix.lstrip('.')
        
        if suffix in ['yaml', 'yml']:
            data = ProjectConfigManager.load_yaml(path)
        elif suffix == 'json':
            data = ProjectConfigManager.load_json(path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")
        
        return ProjectConfig.from_dict(data, base_dir=path.parent)
    
    @staticmethod
    def save_yaml(config: "ProjectConfig", path: Path) -> None:
        """Save configuration as YAML"""
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML required for YAML support: pip install pyyaml")
        
        data = config.to_dict(relative_paths=True)
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    @staticmethod
    def save_json(config: "ProjectConfig", path: Path) -> None:
        """Save configuration as JSON"""
        data = config.to_dict(relative_paths=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


class ProjectConfig:
    """SNES game project configuration"""
    
    def __init__(self):
        self.project_name: str = "UntitledGame"
        self.version: str = "0.1.0"
        self.sdk: SDK = SDK.PVSNESLIB
        self.rom_type: ROMType = ROMType.LOROM
        
        self.source_dir: Path = Path("src")
        self.asset_dir: Path = Path("assets")
        self.build_dir: Path = Path("build")
        self.output_dir: Path = Path("dist")
        
        self.output_rom: Path = Path("dist/game.sfc")
        self.max_rom_size: int = 0x400000
        self.max_ram_size: int = 0x20000
        
        self.assets: List[Dict[str, Any]] = []
        self.compilation_targets: List[Dict[str, Any]] = []
        self.linker_script: Optional[Path] = None
        self.optimization: str = "O2"
    
    def to_build_config(self) -> BuildConfig:
        """Convert to ProjectBuilder configuration"""
        
        config = BuildConfig(
            project_name=self.project_name,
            sdk=self.sdk,
            rom_type=self.rom_type,
            output_rom=self.output_rom,
            source_dir=self.source_dir,
            asset_dir=self.asset_dir,
            build_dir=self.build_dir,
            output_dir=self.output_dir,
            max_rom_size=self.max_rom_size,
            max_ram_size=self.max_ram_size,
        )
        
        # Convert asset definitions
        for asset_def in self.assets:
            asset = Asset(
                name=asset_def.get("name", ""),
                source_path=Path(asset_def.get("source", "")),
                output_path=Path(asset_def.get("output", "")),
                converter=asset_def.get("converter", ""),
                converter_args=asset_def.get("args", []),
            )
            config.assets.append(asset)
        
        # Convert compilation targets
        for target_def in self.compilation_targets:
            target = CompileTarget(
                name=target_def.get("name", ""),
                source_path=Path(target_def.get("source", "")),
                output_path=Path(target_def.get("output", "")),
                language=target_def.get("language", ""),
                compile_args=target_def.get("args", []),
            )
            config.compile_targets.append(target)
        
        return config
    
    def to_dict(self, relative_paths: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        
        return {
            "project": {
                "name": self.project_name,
                "version": self.version,
                "sdk": self.sdk.value,
            },
            "rom": {
                "type": self.rom_type.name.lower(),
                "output": str(self.output_rom),
                "max_size": f"{self.max_rom_size / (1024*1024):.1f}MB",
                "max_ram": f"{self.max_ram_size / 1024:.0f}KB",
            },
            "directories": {
                "source": str(self.source_dir),
                "assets": str(self.asset_dir),
                "build": str(self.build_dir),
                "output": str(self.output_dir),
            },
            "assets": self.assets,
            "compilation": {
                "targets": self.compilation_targets,
                "linker_script": str(self.linker_script) if self.linker_script else None,
                "optimization": self.optimization,
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path = Path(".")) -> "ProjectConfig":
        """Load from dictionary"""
        
        config = cls()
        
        # Project metadata
        if "project" in data:
            project = data["project"]
            config.project_name = project.get("name", "UntitledGame")
            config.version = project.get("version", "0.1.0")
            sdk_str = project.get("sdk", "pvsneslib")
            config.sdk = SDK(sdk_str)
        
        # ROM configuration
        if "rom" in data:
            rom = data["rom"]
            rom_type_str = rom.get("type", "lorom").upper()
            config.rom_type = ROMType[rom_type_str]
            config.output_rom = base_dir / rom.get("output", "dist/game.sfc")
        
        # Directories
        if "directories" in data:
            dirs = data["directories"]
            config.source_dir = base_dir / dirs.get("source", "src")
            config.asset_dir = base_dir / dirs.get("assets", "assets")
            config.build_dir = base_dir / dirs.get("build", "build")
            config.output_dir = base_dir / dirs.get("output", "dist")
        
        # Assets
        config.assets = data.get("assets", [])
        
        # Compilation
        if "compilation" in data:
            comp = data["compilation"]
            config.compilation_targets = comp.get("targets", [])
            if "linker_script" in comp and comp["linker_script"]:
                config.linker_script = base_dir / comp["linker_script"]
            config.optimization = comp.get("optimization", "O2")
        
        return config


# Example configuration
EXAMPLE_CONFIG = """
project:
  name: MyGame
  version: "0.1.0"
  sdk: pvsneslib

rom:
  type: lorom
  output: dist/mygame.sfc
  max_size: "4MB"
  max_ram: "128KB"

directories:
  source: src
  assets: assets
  build: build
  output: dist

assets:
  - name: sprites
    source: assets/sprites.png
    output: build/sprites.bin
    converter: png2snes
    args:
      - --mode
      - 4bpp
  
  - name: music
    source: assets/music.wav
    output: build/music.brr
    converter: wav2brr

compilation:
  targets:
    - name: main
      source: src/main.c
      output: build/main.o
      language: c
    
    - name: startup
      source: src/startup.asm
      output: build/startup.o
      language: asm
  
  linker_script: src/link.ld
  optimization: "O2"
"""

if __name__ == "__main__":
    # Demo: Create example configuration
    print("Example SNES Project Configuration:")
    print(EXAMPLE_CONFIG)
