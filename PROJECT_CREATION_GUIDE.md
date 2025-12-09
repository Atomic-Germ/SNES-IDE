# Project Creation & Management in SNES-IDE

## Quick Start: Creating Your First Project

### Method 1: Using the TUI (Recommended)

1. **Launch SNES-IDE**
   ```bash
   source .venv/bin/activate
   python -m src.tui.app
   ```

2. **Open Build System** (Press `Ctrl+B`)

3. **Click "New Project"**
   - Enter project name: `MyGame`
   - Choose location: (defaults to home directory)
   - Select SDK: `PVSnesLib` (default)
   - Choose ROM Type: `LOROM` (default)
   - Check "Initialize Git repository"
   - Check "Create README.md"

4. **Click "Create"**
   - Project is created with full directory structure
   - SDK template files are populated
   - Config file is auto-loaded

5. **Click "Build"**
   - Your game is ready to build!

## Project Creation Dialog

### Fields

**Project Name** (required)
- Name of your game/project
- Used for directory name and ROM output filename
- Example: `MyGame`, `Zelda`, `FinalFantasy`

**Location** (default: home directory)
- Where to create the project directory
- Can be any accessible path
- Example: `/home/user/Projects`, `~/Games`, `C:\Users\Dev`

**SDK** (dropdown)
- `PVSnesLib` (C-based, recommended for beginners)
- `DotnetSnes` (C#/.NET)
- `JavaSnes` (Java)

**ROM Type** (radio buttons)
- `LOROM` (LoROM - most common, 32KB banks)
- `HIROM` (HiROM - different memory layout, 8KB banks)
- `EXLOROM` (Extended LoROM - larger ROM support)
- `EXHIROM` (Extended HiROM - larger ROM support)

**Options** (checkboxes)
- Initialize Git repository (.gitignore included)
- Create README.md with project info

## Project Structure Created

After creating a project, you'll have:

```
MyGame/
├── snes-project.yaml          ← Configuration file
├── README.md                   ← Project documentation
├── .gitignore                  ← Git ignore rules
├── src/
│   ├── main.c                  ← Main source code
│   ├── startup.asm             ← Assembly startup (PVSnesLib)
│   └── ...                     ← Other SDK files
├── assets/
│   ├── sprites.png             ← Graphics (you add these)
│   ├── music.wav               ← Audio (you add these)
│   └── ...
├── build/                      ← Build artifacts (auto-created)
│   ├── main.o
│   ├── startup.o
│   └── ...
└── dist/                       ← Output (auto-created)
    └── mygame.sfc              ← Final ROM
```

## SDK Templates

Each SDK comes with starter files configured for quick development:

### PVSnesLib (C-based)
```
src/main.c          - Hello world C program
src/startup.asm     - SNES bootstrap code
Makefile            - Build configuration
```

### DotnetSnes (C#/.NET)
```
src/Program.cs      - Hello world C# program
src/snes.csproj     - Project configuration
```

### JavaSnes (Java)
```
src/Game.java       - Hello world Java program
src/pom.xml         - Maven configuration
```

## Loading an Existing Project

### Method 1: Using "Load Project" Button

1. Open Build System (Press `Ctrl+B`)
2. Click "Load Project"
3. Choose one:
   - **Load File**: Browse directly to `snes-project.yaml`
   - **Load Directory**: Point to project folder, auto-detects config

### Method 2: Manual Configuration

1. Open Build System (Press `Ctrl+B`)
2. Type path in "Project Configuration" field
3. Click "Load Config"

Path can be:
- Full path: `/home/user/MyGame/snes-project.yaml`
- Relative: `./snes-project.yaml`
- Home-relative: `~/Games/MyGame/snes-project.yaml`

### Method 3: Auto-Detection

If you run SNES-IDE from your project directory, it auto-detects:
- `snes-project.yaml`
- `snes-project.yml`
- `snes-project.json`

## Configuration File (snes-project.yaml)

The generated config looks like:

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

compilation:
  targets:
    - name: main
      source: src/main.c
      output: build/main.o
      language: c
```

You can edit this file to:
- Add more assets
- Configure compilation targets
- Change output paths
- Adjust ROM constraints

## Workflow Example

### Step 1: Create Project
```
1. Press Ctrl+B (Build System)
2. Click "New Project"
3. Name: MyGame, SDK: PVSnesLib
4. Click Create
5. Wait for "Project created" message
```

### Step 2: Project Auto-Loaded
```
- Config automatically loaded
- Status shows "Ready to build"
- Click "Build" anytime
```

### Step 3: Develop
```
1. Edit code: src/main.c
2. Press Ctrl+B
3. Click Build
4. Watch progress
5. ROM ready: dist/mygame.sfc
6. Repeat
```

### Step 4: Save & Share
```
- Git repository initialized (.gitignore included)
- Push to GitHub: git push origin main
- Share with team
```

## Best Practices

### Naming
- Use descriptive project names: `TowerDefense`, `PuzzleGame`
- Avoid spaces: use `CamelCase` or `snake_case`
- Keep names reasonable length: 20 chars max

### Organization
- Keep all assets in `assets/` directory
- Organize assets by type:
  ```
  assets/
  ├── graphics/
  │   ├── sprites/
  │   ├── backgrounds/
  │   └── ui/
  ├── audio/
  │   ├── music/
  │   └── sfx/
  └── data/
  ```

### SDK Choice
| SDK | Best For | Language |
|-----|----------|----------|
| PVSnesLib | Beginners, most projects | C |
| DotnetSnes | .NET developers | C# |
| JavaSnes | Java developers | Java |

### Version Control
- Always initialize Git (checked by default)
- First commit: `git add . && git commit -m "Initial project"`
- Commit after each milestone
- Don't commit build artifacts (handled by .gitignore)

## Troubleshooting

### "Project already exists"
- Choose different name or location
- Or load existing project with "Load Project"

### "Config file not found"
- Ensure you're in correct directory
- Run `ls snes-project.yaml` to verify
- Or use full path when loading

### Build fails after creation
- This is normal in Phase 1 (scaffold)
- Phase 1B will add real tools
- Check SDK is installed: `sdk --version`

### Can't find project
- Use "Load Project" → "Load Directory"
- Browse to project folder
- Auto-detects config file

## Advanced: Custom Projects

### Multiple Configurations
Create separate files for different builds:
```
snes-project-dev.yaml       # Development build
snes-project-release.yaml   # Release build
```

Load with:
1. Click "Load Project"
2. Type full path to specific config
3. Click "Load File"

### Different SDKs
To switch SDKs:
1. Create new project with different SDK
2. Copy your `src/` files
3. Update compilation targets in config
4. Rebuild

## Features Coming Soon (Phase 1B)

✅ Currently Available:
- Project creation with templates
- Configuration management
- Project loading
- Multi-SDK support

🔄 Coming Soon:
- Real asset converters (PNG→SNES, WAV→BRR)
- Real compiler integration
- Build progress tracking
- Incremental builds
- Error reporting

🚀 Future Phases:
- Interactive debugger
- Memory watch
- Breakpoints
- Real-time emulator integration

---

**Questions?** See `BUILD_SYSTEM_PHASE1.md` for architecture details.

Your SNES game development is ready to begin! 🎮✨
