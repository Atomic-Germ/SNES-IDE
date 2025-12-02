# SNES-IDE-MINI-out Implementation Notes

## Overview

This document outlines the architecture and requirements for building a "mini" version of SNES-IDE that compiles all tools locally from source on-demand, rather than bundling pre-built binaries. This is specifically designed for systems with non-standard requirements, such as Apple M1 running Asahi Fedora Remix (which requires 16K page size binaries, etc.).

---

## Current Architecture Summary

### Build System (`build/build.py`)

The current build process:
1. **Cleans** `SNES-IDE-out/` directory
2. **Restores big files** - uses `FileJoiner` to reconstruct large files from chunks (`.snes.ide.reconstruct.manifest.json`)
3. **Copies root files** - README, LICENSE, etc.
4. **Copies libs** - from `resources/libs/` → `SNES-IDE-out/libs/`
5. **Copies docs** - from `docs/` → `SNES-IDE-out/docs/`
6. **Copies binary files** - from `resources/bin/{platform}/` → `SNES-IDE-out/bin/`
7. **Copies source code** - from `src/` → `SNES-IDE-out/`
8. **Decompresses zip files** - unpacks any `.zip` files in output
9. **Generates bundle** - creates platform-specific bundle (AppImage/App/exe)

### Pre-Built Binaries Location (`resources/bin/`)

```
resources/bin/
├── COPYING.md           # Licenses for all bundled tools
├── linux/
│   ├── dotnet8/         # .NET 8 SDK (chunked zip)
│   ├── jdk8/            # Zulu OpenJDK 8 (chunked zip)
│   ├── make/            # GNU Make
│   ├── pvsneslib/       # PVSnesLib SDK (devkitsnes + pvsneslib)
│   ├── schismtracker/   # SchismTracker AppImage
│   ├── snes-emulator/   # LakeSnes emulator
│   ├── sprite-editor/   # Libresprite AppImage
│   └── tmx-editor/      # Tiled AppImage
├── macos/               # Same structure for macOS
└── windows/             # Same structure for Windows
```

### Library Dependencies (`resources/libs/`)

```
resources/libs/
├── COPYING.md
├── DntcTranspiler/      # .NET to C transpiler (for DotnetSnes)
├── DotnetSnesLib/       # DotnetSnes library source
├── SampleLibrary/       # Sample library
├── javasnes/            # JavaSnes library source
└── pvsneslib/           # PVSnesLib include/examples/templates
```

---

## Tools Configuration (`build/tools_.json`)

The `tools_.json` file defines all external tools with their:
- **name**: Tool identifier
- **description**: What it does
- **category**: Grouping (Compilers, Debugging Tools, Utilities, Sound & Music)
- **url**: Download URL (string or platform-specific object)
- **binary_path**: Relative path to the built binary
- **build_commands**: Platform-specific build commands
- **configure_commands**: Pre-build configuration (mostly empty)

### Tools Defined:

| Name | Build System | Notes |
|------|--------------|-------|
| ca65 | make | Part of cc65, 6502 assembler |
| asar | cmake + make | SNES assembler |
| xkas | make | SNES assembler |
| 64tass | make | 6502/65816 assembler |
| wla-dx | cmake + make | Multi-platform assembler |
| libsfx | N/A | Library only, no build |
| pvsneslib | Pre-built | Downloaded per-platform |
| superfamiconv | cmake + make | Graphics converter |
| bsnes | make | SNES emulator (complex deps) |
| no$snes | make | SNES emulator |
| ucon64 | Pre-built | ROM utility |
| snes_gss | N/A | GUI tool |
| furnace | N/A | Script-based |
| terrific_audio_driver | cargo (Rust) | Requires Rust toolchain |

---

## Script Dependencies on Binaries

The scripts in `src/scripts/` reference these binary paths:

### Compilation Scripts
- **compile-pvsneslib-proj.py**: `bin/pvsneslib`, `bin/make`
- **compile-javasnes-proj.py**: `bin/pvsneslib`, `bin/jdk8`, `bin/make`
- **compile-dotnetsnes-proj.py**: `bin/pvsneslib`, `bin/dotnet8`, `bin/make`, `libs/DntcTranspiler`, `libs/DotnetSnesLib`

### Graphics Tools
- **gfx-png-bmp-editor.py**: `bin/sprite-editor/libresprite`
- **gfx-tmx-editor.py**: `bin/tmx-editor/tiled`
- **gfx-png-bmp-snes-converter.py**: `bin/pvsneslib` (gfx2snes tool)
- **gfx-tmx-tmj-converter.py**: `bin/pvsneslib` (tilesetextractor)

### Audio Tools
- **audio-impulse-tracker-init.py**: `bin/schismtracker`
- **audio-wav-brr-converter.py**: `bin/pvsneslib` (snesbrr tool)
- **audio-brr-wav-converter.py**: `bin/pvsneslib` (snesbrr tool)

### Utilities
- **open-emulator.py**: `bin/snes-emulator/lakesnes` (or `bsnes` on macOS)

---

## SNES-IDE-MINI-out Implementation Plan

### Core Concept

Instead of bundling pre-built binaries, the MINI version will:
1. Ship with **source URLs and build instructions** only
2. Include a **tool manager** that:
   - Downloads sources on-demand
   - Applies platform-specific patches (e.g., 16K page size)
   - Builds tools locally
   - Caches built binaries for reuse
3. Detect system requirements and adapt builds accordingly

### New Files/Modules Needed

#### 1. `build/build_mini.py`
Main build script for SNES-IDE-MINI-out:
- Skip copying pre-built binaries
- Include tool manager and build configurations
- Create minimal bundle with build-on-demand capability

#### 2. `src/tool_manager.py`
Core module for on-demand tool building:
```python
class ToolManager:
    def __init__(self, tools_config: dict, cache_dir: Path)
    def check_tool_installed(self, tool_name: str) -> bool
    def install_tool(self, tool_name: str) -> bool
    def download_source(self, tool_name: str) -> Path
    def apply_patches(self, tool_name: str, source_dir: Path) -> bool
    def build_tool(self, tool_name: str, source_dir: Path) -> bool
    def get_tool_path(self, tool_name: str) -> Path
```

#### 3. `src/patches/`
Directory for platform-specific patches:
```
src/patches/
├── 16k-page-size/           # Patches for 16K page alignment
│   ├── pvsneslib.patch
│   ├── lakesnes.patch
│   └── ...
├── asahi-linux/             # Asahi-specific patches
├── aarch64/                 # ARM64-specific patches
└── README.md
```

#### 4. `build/tools_mini.json`
Extended tools configuration with:
- Source repository URLs (git/tarball)
- Build dependencies (packages to install)
- Patch sets to apply
- Environment variables needed
- Post-build verification commands

### Modified Scripts

All scripts in `src/scripts/` need modification to:
1. Check if tool is available via `ToolManager`
2. Trigger build if not installed
3. Use dynamic path resolution

Example modification pattern:
```python
# Before (current)
libresprite = Path(get_home_path()) / "bin" / "sprite-editor" / "libresprite.AppImage"

# After (mini version)
from tool_manager import ToolManager
tool_mgr = ToolManager.get_instance()
libresprite = tool_mgr.get_tool_path("libresprite")
if not libresprite.exists():
    tool_mgr.install_tool("libresprite")
    libresprite = tool_mgr.get_tool_path("libresprite")
```

---

## Required Build Dependencies by Tool

### System Package Dependencies

For building tools from source, users will need:

**All Platforms:**
- git
- make
- cmake
- gcc/g++ or clang
- python3

**Linux (apt/dnf):**
```bash
# Essential
build-essential cmake git

# For PVSnesLib/devkitsnes
# (These are typically pre-built, but for source builds:)
libpng-dev zlib1g-dev

# For bsnes
libgtk-3-dev libsdl2-dev libopenal-dev libpulse-dev

# For lakesnes
libsdl2-dev

# For Schismtracker
libsdl2-dev libasound2-dev

# For libresprite
libfreetype6-dev libpng-dev libjpeg-dev libgif-dev libtinyxml-dev

# For Tiled
qt6-base-dev qt6-declarative-dev
```

**macOS (Homebrew):**
```bash
brew install cmake sdl2 qt@6 libpng freetype
```

**Windows (MSYS2/MinGW):**
```bash
pacman -S mingw-w64-x86_64-cmake mingw-w64-x86_64-gcc mingw-w64-x86_64-SDL2
```

---

## Platform-Specific Patches for Asahi/16K Page Size

### Key Issues:
1. **Memory alignment**: Some tools assume 4K page size
2. **JIT compilation**: Some emulators use JIT that needs page alignment
3. **Pre-built binaries**: Won't work, need native compilation

### Tools Likely Needing Patches:

1. **LakeSnes**: May need page-aligned memory allocations
2. **bsnes**: Complex JIT, likely needs careful handling
3. **Schismtracker**: Should build cleanly
4. **Libresprite**: Should build cleanly
5. **Tiled**: Should build cleanly (Qt-based)
6. **PVSnesLib/devkitsnes**: The 816-tcc compiler may need patches

### Patch Strategy:

```bash
# Example: Force 16K page alignment in allocations
# Add to CFLAGS/CXXFLAGS:
-DPAGE_SIZE=16384
-faligned-new=16384

# For mmap-based allocations:
# Patch to use MAP_ALIGNED(14) on FreeBSD-derived systems
```

---

## Tool Manager GUI Integration

Add a new UI section to `src/assets/index.html`:

```html
<div class="category-card">
    <div class="category-header">
        <div class="category-icon"><i class="fas fa-download"></i></div>
        <h2 class="category-title">Tool Management</h2>
    </div>
    <div class="script-list">
        <button class="script-btn" onclick="runScript('tool-manager-gui.py')">
            <div>
                <div class="script-name">Install Tools</div>
                <div class="script-desc">Build and install development tools</div>
            </div>
        </button>
        <button class="script-btn" onclick="runScript('tool-manager-status.py')">
            <div>
                <div class="script-name">Tool Status</div>
                <div class="script-desc">Check installed tools</div>
            </div>
        </button>
    </div>
</div>
```

---

## Directory Structure for SNES-IDE-MINI-out

```
SNES-IDE-MINI-out/
├── snes-ide.py              # Main application
├── tool_manager.py          # On-demand tool builder
├── assets/
│   ├── index.html
│   └── styles.css
├── scripts/                  # Modified scripts using tool_manager
├── libs/                     # Same as current (source libraries)
├── docs/
├── config/
│   ├── tools.json           # Tool definitions with build instructions
│   └── patches/             # Platform-specific patches
├── cache/                    # Built tool cache (created at runtime)
│   ├── downloads/           # Downloaded sources
│   └── builds/              # Compiled binaries
└── bin/                      # Symlinks to cached builds (created at runtime)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Create `build/build_mini.py`
- [ ] Create `src/tool_manager.py` with basic download/build
- [ ] Create enhanced `build/tools_mini.json`
- [ ] Test with one simple tool (e.g., 64tass)

### Phase 2: Tool Integration
- [ ] Add all tools to configuration
- [ ] Create build scripts for each tool
- [ ] Test builds on standard Linux x64

### Phase 3: Patch System
- [ ] Create patch infrastructure
- [ ] Add 16K page size patches
- [ ] Add Asahi-specific patches
- [ ] Test on Asahi Fedora Remix

### Phase 4: Script Migration
- [ ] Modify all scripts to use `tool_manager`
- [ ] Add fallback to pre-built if available
- [ ] Test full workflow

### Phase 5: UI Integration
- [ ] Add tool management GUI
- [ ] Add progress indicators for builds
- [ ] Add dependency checking

---

## Critical Considerations

### 1. Build Time
- First-time setup will be slow (building all tools)
- Consider parallel builds where possible
- Provide clear progress feedback

### 2. Dependency Resolution
- Need to detect missing system packages
- Provide clear instructions for installing deps
- Consider using containers for reproducible builds

### 3. Disk Space
- Source + build artifacts can be large
- Implement cleanup options
- Cache management

### 4. Error Handling
- Build failures must be clearly reported
- Logs should be saved for debugging
- Fallback to pre-built when possible

### 5. Updates
- Need mechanism to update tool sources
- Version pinning for reproducibility
- Git submodules vs tarballs

---

## Testing Checklist

- [ ] Build on Ubuntu x64
- [ ] Build on Fedora Asahi (aarch64, 16K pages)
- [ ] Build on macOS ARM
- [ ] Build on Windows (MSYS2)
- [ ] All scripts work with built tools
- [ ] GUI shows correct tool status
- [ ] Updates work correctly
- [ ] Cache cleanup works

---

## References

- PVSnesLib: https://github.com/alekmaul/pvsneslib
- LakeSnes: https://github.com/angelo-wf/lakesnes
- bsnes: https://github.com/bsnes-emu/bsnes
- Schismtracker: https://github.com/schismtracker/schismtracker
- Libresprite: https://github.com/LibreSprite/LibreSprite
- Tiled: https://github.com/mapeditor/tiled
- Asahi Linux: https://asahilinux.org/
- 16K page size issues: https://github.com/AsahiLinux/docs/wiki/Software-known-to-have-issues-with-16k-page-size
