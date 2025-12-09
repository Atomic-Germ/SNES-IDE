# SNES Developer Wishlist for SNES-IDE

As an active SNES homebrew developer, here's my realistic wishlist for SNES-IDE features, prioritized by impact:

## 🔴 Critical (Essential for Modern Development)

### 1. **Integrated Visual Debugger**
- **Memory Watch**: Real-time view of RAM/VRAM/WRAM with hex/decimal modes
- **Breakpoint System**: Conditional breakpoints (e.g., break when VRAM address $2000 is written)
- **Register Inspector**: Live view of PPU/APU/CPU registers with bitfield decoding
- **Trace Logging**: Instruction-by-instruction execution trace with cycle counts

### 2. **PPU Visual Debuggers**
- **VRAM Viewer**: Visual grid showing tiles, palettes, and map data
- **Sprite Table Inspector**: Show all 128 sprites with position, tile, and attribute editing
- **Layer Viewer**: Toggle BG1/BG2/BG3/BG4 and see tilemap addresses
- **Palette Editor**: Real-time color editing with SNES color math preview

### 3. **Performance Profiler**
- **CPU Cycle Counter**: Per-function cycle usage (SNES has ~3.5M cycles/frame)
- **VRAM Bandwidth Meter**: Warn when approaching DMA limits
- **SlowROM/FastROM Analyzer**: Highlight code that would benefit from FastROM

## 🟠 High Priority (Major Productivity Boost)

### 4. **Sprite Animation Editor**
- **Native Tile Editor**: Create/edit 8x8/16x16/32x32/64x64 tiles directly in IDE
- **Animation Timeline**: Frame-based animation with timing in SNES frames
- **Onion Skinning**: Preview previous/next frames while drawing
- **Export to SNES Format**: Direct output to `.pic` + `.pal` + `.map`

### 5. **Advanced Asset Pipeline**
- **Smart Asset Rebuilding**: Only rebuild changed assets (not everything)
- **Asset Dependency Graph**: Track which files use which assets
- **Compression Integration**: Built-in support for LZSS, Huffman, etc.
- **Batch Processing**: Convert entire folders of PNGs to SNES formats

### 6. **SNES-Specific Code Tools**
- **Register Auto-Complete**: Type `REG_` and get all SNES registers with descriptions
- **DMA Code Generator**: GUI to build DMA/HDMA tables with syntax highlighting
- **Mode 7 Assistant**: Visual matrix editor for Mode 7 transformations
- **Interrupt Handler Wizard**: Generate NMI/IRQ/BRK stubs with proper register preservation

### 7. **Audio Development Suite**
- **SPC700 Debugger**: Step through audio code, view DSP registers
- **BRR Sample Converter**: Import WAV → BRR with loop point detection
- **Music Sequence Editor**: Visual piano roll for SNES-specific sound engines (like SNESMOD)
- **SPC Player**: Preview songs directly in IDE without booting emulator

## 🟡 Medium Priority (Quality of Life)

### 8. **Project Management Enhancements**
- **Multi-Target Builds**: Debug, Release, PAL/NTSC versions with different defines
- **ROM Map Visualization**: Interactive memory map showing what's at each address
- **Size Optimization Reports**: Which functions/data are taking most space
- **Git Integration**: Built-in diff for binary assets (tilemaps, palettes)

### 9. **Advanced Emulator Integration**
- **Save State Management**: Named save states for different test scenarios
- **Frame Advance**: Step frame-by-frame to debug animations
- **Input Recording/Playback**: Record controller input for automated testing
- **Netplay Testing**: Test multiplayer features over network

### 10. **Documentation System**
- **Contextual Help**: Press F1 on `REG_INIDISP` → opens official docs
- **Interactive Register Reference**: Hover over register name to see bit meanings
- **Tutorial Engine**: Step-by-step guided tutorials with highlighted UI elements
- **Community Snippet Library**: Share reusable code (e.g., Mode 7 floor, sprite OAM sorting)

### 11. **Level Design Tools**
- **Native Tilemap Editor**: Paint tiles directly onto SNES layer formats -- **possiblely with Tiled integration**
- **Collision Map Editor**: Visual overlay for defining solid/tile attributes
- **Parallax Preview**: Real-time preview of multi-layer scrolling effects
- **TMX → SNES Converter**: Better Tiled integration with custom properties

## 🟢 Nice to Have (Polish & Community)

### 12. **Build & Deployment**
- **ROM Fixer**: Auto-calculate checksums, fix header flags
- **Release Packaging**: One-click ZIP creation with README, source, and ROM
- **ROM Comparison Tool**: Visual diff between two ROM versions (highlight changed bytes)
- **Flash Cartridge Support**: Direct flash to FXPAK Pro, SD2SNES

### 13. **Team Collaboration**
- **Asset Versioning**: Lock files when editing to prevent conflicts
- **Comment System**: Leave notes on specific tiles/code lines for team members
- **Build Server Integration**: CI/CD for automated testing on real hardware

### 14. **Hardware Testing**
- **BSNES Accuracy Mode**: Toggle between performance and cycle-accurate modes
- **Real Hardware Debugger**: USB2SNES integration for debugging on actual SNES
- **Compatibility Tester**: Auto-test on multiple emulator cores (Snes9x, Mesen-S, etc.)

---

## My Top 5 Must-Haves for v2.0:

1. **VRAM Viewer + Sprite Inspector** (saves hours of guesswork)
2. **Cycle Profiler** (essential for 60fps games)
3. **Sprite Animation Editor** (currently using external tools)
4. **Conditional Breakpoints** (debugging HDMA is nightmare without this)
5. **Smart Asset Pipeline** (rebuilding everything on each compile is painful)

The current IDE is solid for compilation, but these debugging and asset tools would make it a true *integrated* development environment rather than just a fancy build script runner.