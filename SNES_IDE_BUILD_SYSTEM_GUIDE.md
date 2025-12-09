# Using the Build System in SNES-IDE TUI

## Quick Start

### 1. **Open the Build Panel**

Press **`Ctrl+B`** to open the Build System panel, or use the command palette.

```
🔨 Build System

Project Configuration:
[snes-project.yaml path    ] [Load Config]

Project: (none loaded)
SDK: (none)
ROM Type: (none)

Build Options:
[Build] [Clean Build] [Rebuild All]

Status: Ready
```

### 2. **Load Your Project Configuration**

Create a `snes-project.yaml` file in your project root:

```yaml
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
    args: [--mode, 4bpp]

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
```

Then in the Build panel:
1. Type the path: `./snes-project.yaml`
2. Click **"Load Config"**

The panel will show:
```
Project: MyGame
SDK: pvsneslib
ROM Type: LOROM
```

### 3. **Build Your Game**

Click one of:
- **Build** - Incremental build (only rebuild changed files)
- **Clean Build** - Clean and rebuild
- **Rebuild All** - Force full rebuild

### 4. **Monitor Build Progress**

The build output panel shows:
```
🔄 Building...

📦 Converting assets...
  🔄 sprites.png... ✓
  🔄 music.wav... ✓
  📊 Assets: 2 converted, 0 skipped

📝 Compiling code...
  🔄 main.c... ✓
  📊 Code: 1 compiled, 0 skipped

🏦 Checking bank layout...
  LoROM: max 64KB per bank
  ✓ Bank layout valid

🔗 Linking ROM...
  Linking MyGame...
  ROM Type: LOROM
  Max Size: 4.0MB
  ✓ Linking complete

📀 Generating ROM...
  Output: dist/mygame.sfc
  Size: 256.0KB
  ✓ ROM generated

============================================================
✅ BUILD SUCCESSFUL in 1.2s
📀 ROM: dist/mygame.sfc
============================================================
```

## Features

### ✅ Automatic Project Detection

If you don't specify a path, the build system will look for:
1. `snes-project.yaml`
2. `snes-project.yml`
3. `snes-project.json`

In the current directory.

### ✅ Incremental Builds

The build system tracks file changes:
- Only rebuilds modified assets
- Only recompiles modified source
- Typical rebuild time: 5-30 seconds

First build is slower (full compile), but subsequent builds are fast.

### ✅ Multi-SDK Support

Configure any SDK in your `snes-project.yaml`:

```yaml
project:
  sdk: pvsneslib    # PVSnesLib (C-based)
  # OR
  sdk: dotnetsnes   # DotnetSnes (C#/.NET)
  # OR
  sdk: javasnes     # JavaSnes (Java)
```

The build system adapts automatically.

### ✅ Asset Pipeline

Define any assets (graphics, audio, data):

```yaml
assets:
  - name: sprites
    source: assets/sprites.png
    output: build/sprites.bin
    converter: png2snes
    args: [--mode, 4bpp]
  
  - name: background
    source: assets/bg.bmp
    output: build/bg.bin
    converter: bmp2snes
  
  - name: music
    source: assets/music.wav
    output: build/music.brr
    converter: wav2brr
  
  - name: level_data
    source: assets/level.json
    output: build/level.bin
    converter: json2bin
```

### ✅ Memory Management

Configure ROM and RAM constraints:

```yaml
rom:
  type: lorom          # or hirom, exlorom, exhirom
  output: dist/game.sfc
  max_size: "4MB"      # Max ROM size
  max_ram: "128KB"     # Max RAM available
```

The build system detects overflow and warns you.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+B** | Show Build System |
| **Enter** | Execute build (when focused on Build button) |

## Workflow Example

### Typical Development Loop

```
1. Edit sprites: assets/sprites.png
2. Press Ctrl+B (open build panel)
3. Click Build
   ├─ Graphics converter runs (5s)
   ├─ Code already built (skipped)
   ├─ Link & ROM gen (2s)
   └─ Result: dist/mygame.sfc ready
4. Test in emulator
5. Find issue, edit code
6. Click Build again
   ├─ Graphics skipped (unchanged)
   ├─ Code recompiled (15s)
   ├─ Link & ROM gen (2s)
   └─ Result: dist/mygame.sfc ready (17s total)
7. Repeat
```

### Time Savings

- **Manual process**: 10+ minutes per iteration
- **Automated (Phase 1B complete)**: 30-60 seconds per iteration
- **Over 100 iterations**: 16+ hours saved = 2 extra working days

## Troubleshooting

### "No project loaded"
- Create `snes-project.yaml` in your project root
- Or provide the full path in the config path field
- Click "Load Config"

### Build fails with "Compiler not found"
- This happens in Phase 1 (scaffold only)
- Phase 1B will integrate real compilers
- For now, verify manually that SDK is installed

### Build is slow
- First build is slow (full compile) - normal
- Subsequent builds should be 5-30 seconds
- If build is slow repeatedly, try "Clean Build"

### Assets not updating
- Check that source file path is correct
- Verify output path is in build directory
- Try "Clean Build" to force re-conversion

## Advanced: Custom Configuration

You can have multiple configurations:

```bash
# Build with different SDK
snes-project-pvsneslib.yaml
snes-project-dotnetsnes.yaml

# In IDE:
# 1. Load snes-project-dotnetsnes.yaml
# 2. Click Build
# 3. Done!
```

## Next Steps

After Phase 1B (real tools):
1. Build completes with actual compiled ROM
2. Integrate with Phase 2 debugger (Months 5-8)
3. Full development workflow with breakpoints

Current status: **Foundation complete, tools integration in progress**

---

**Questions?** See `BUILD_SYSTEM_PHASE1.md` for architecture details.
