# SNES-IDE TUI - Full-Featured Terminal IDE

## Status: ✅ COMPLETE & PRODUCTION-READY

The Textual TUI is a comprehensive terminal-based IDE with code browsing, tool management, and full installation capabilities.

## What You Have Now

### Core Files

1. **`src/tools_browser.py`** (~2000+ lines)
   - Full IDE functionality
   - Code browser with syntax highlighting & Markdown rendering
   - Tool installation from source with real-time progress
   - Command palette (Ctrl+P) with contextual commands
   - Collapsible sidebar with Project and Tools sections
   - External editor integration ($EDITOR support)

2. **`src/snes-ide.py`** (updated)
   - Qt GUI mode (default)
   - Textual TUI mode (`--tui` / `-t` flags)
   - Routes to `tools_browser.py` for TUI

3. **`src/tools.json`** (enhanced)
   - Full build configurations per tool
   - Platform-specific commands (linux/darwin/win32)
   - Dependencies (apt/dnf/brew/msys2)
   - docs_url and custom commands per tool

### How It Works

```bash
# Qt GUI (original)
python src/snes-ide.py

# Textual TUI (full IDE)
python src/snes-ide.py --tui
python src/snes-ide.py --tui /path/to/project
```

## Why This Is Better

✓ **Full IDE** - Code browsing, not just tool status
✓ **Real Installation** - Downloads, builds, and installs tools from source
✓ **Progress Tracking** - Real-time output with progress bar and ETA
✓ **Command Palette** - Quick access to contextual commands
✓ **External Editor** - Launch $EDITOR directly from TUI
✓ **Cross-platform** - Works on Linux, macOS, Windows (with appropriate shells)
✓ **SSH-friendly** - Perfect for remote development

## The Implementation

### Key Components in tools_browser.py

1. **ToolInstaller class** (~300 lines)
   - Full install/uninstall workflow
   - Dependency installation (apt/dnf/brew/msys2)
   - Source download (git clone or tarball)
   - Build execution with real-time streaming
   - Binary installation to ~/.local/bin
   - Installation verification

2. **ToolCommandProvider class** (~150 lines)
   - Command palette provider
   - Contextual commands based on tool state
   - Category and per-tool custom commands

3. **CodeViewer class** (~100 lines)
   - Syntax highlighting via Rich Syntax
   - Markdown rendering via Rich Markdown
   - Reactive file_path property

4. **ProjectTree class** (~80 lines)
   - Filtered DirectoryTree widget
   - Smart file type filtering
   - Hides build artifacts and caches

5. **Sidebar class** (~100 lines)
   - Collapsible sections
   - Project file tree
   - Tool list with status indicators

6. **InstallScreen, VerifyScreen, UninstallScreen** (~400 lines)
   - Modal screens for tool operations
   - Progress bar with dynamic total
   - ETA calculation with outlier filtering
   - Real-time log output

7. **ToolBrowser class** (~400 lines)
   - Main application
   - Dual-panel view (tools/code)
   - Keybinding handlers
   - External editor integration

## Usage Examples

```bash
# Run TUI with current directory as project
python src/snes-ide.py --tui

# Run TUI with specific project
python src/snes-ide.py --tui ~/projects/my-snes-game

# Get help
python src/snes-ide.py --help
```

## Architecture

```
src/snes-ide.py
│
├─ main()
│  ├─ Parse arguments (--tui, -t)
│  ├─ If TUI:
│  │  └─ Import and run tools_browser.ToolBrowser
│  └─ Else:
│     └─ QApplication (Qt GUI)
│
src/tools_browser.py
│
├─ ToolInstaller - Download, build, install tools
├─ ToolCommandProvider - Command palette commands
├─ InstallScreen - Modal for installation progress
├─ VerifyScreen - Modal for verification
├─ UninstallScreen - Modal for uninstall
├─ CodeViewer - Syntax/Markdown viewer
├─ ProjectTree - Filtered file tree
├─ Sidebar - Collapsible sections
├─ ToolDetailPanel - Tool information
└─ ToolBrowser - Main application
```

## TUI Features

### Code Browser
- Syntax highlighting for C, ASM, Python, Java, JSON, YAML, and more
- Markdown rendering for `.md` files
- Project file tree with smart filtering (hides __pycache__, .git, build)
- Open files in external editor (`e` key or command palette)

### Tool Manager
- Install tools from source (git clone or tarball download)
- Real-time build output streaming
- Progress bar with ETA (filters outliers for accurate timing)
- Dependency installation with PATH checking (avoids unnecessary sudo)
- Update, verify, and uninstall tools
- Documentation links open in browser

### Command Palette (Ctrl+P)
- Always available: Refresh, Toggle Sidebar, Open Project
- Tool-specific: Install/Update/Verify/Uninstall/Documentation
- Per-tool custom commands from tools.json
- Category-based script commands

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `s` | Toggle sidebar visibility |
| `f` | Toggle between code and tools view |
| `e` | Open current file in external editor |
| `o` | Open project directory |
| `i` | Install selected tool |
| `r` | Refresh tool list |
| `Ctrl+P` | Open command palette |
| `Escape` | Return to tools view |
| `q` | Quit |

## Code Quality

- Type hints throughout
- Docstrings for all functions/classes
- PEP 8 compliant
- Comprehensive error handling
- Graceful sudo handling with dialogs
- No external dependencies beyond Textual and Rich
- Uses tools.json for all configuration

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `$EDITOR` | Preferred text editor for "Open in Editor" |
| `$VISUAL` | Fallback editor if $EDITOR not set |

If neither is set, falls back to: nano → vim → vi → code → gedit → kate

## Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the TUI
python src/snes-ide.py --tui

# Or run tools_browser.py directly
python src/tools_browser.py /path/to/project
```

## What Didn't Change

✓ Qt GUI works exactly as before
✓ tools.json structure backward compatible  
✓ No breaking changes to existing functionality
✓ ScriptRunner unchanged
✓ MainWindow unchanged

---

## Quick Reference

```bash
# Run in TUI mode
python src/snes-ide.py --tui

# With project path
python src/snes-ide.py --tui ~/my-project

# Original Qt GUI still works
python src/snes-ide.py
```

Full-featured terminal IDE with code browsing, tool management, and real installation capabilities!
