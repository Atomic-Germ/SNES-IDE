# SNES-IDE Tool Installer Feature

## Overview

The Tool Installer feature in SNES-IDE provides an integrated interface for managing the installation and verification of development tools used in SNES game creation. This section documents the implementation and usage of this feature.

## Components

### 1. **tool_manager.py** - Tool Management Module

The `ToolManager` class handles all tool-related operations:

- **Configuration Loading**: Reads `tools.json` to get tool definitions
- **Tool Status Detection**: Checks if tools are available in system PATH
- **Tool Organization**: Groups tools by category and priority
- **Tool Verification**: Verifies tool functionality using verify commands

#### Key Methods

- `get_all_tools()` - Returns list of all configured tools
- `find_tool_in_path(tool_name)` - Checks if tool binary is in PATH
- `get_tool_status(tool)` - Returns installation status of a tool
- `get_all_tools_status()` - Returns status of all tools
- `get_tools_by_category()` - Groups tools by category
- `get_required_tools()` - Returns list of required tools
- `get_missing_required_tools()` - Returns unavailable required tools

### 2. **ToolInstallerDialog** - PyQt6 Dialog Window

The `ToolInstallerDialog` class provides a graphical interface for tool management:

#### Features

- **Tool Organization**: Tools displayed grouped by category
- **Status Indication**: Visual indicators show whether tools are installed
- **Tool Information**: Displays tool descriptions and paths
- **Refresh Capability**: Allows users to refresh tool status
- **Scrollable Interface**: Handles large numbers of tools

#### Layout

```
┌─ Tool Installer ─────────────────────┐
│ SNES-IDE Tool Manager                │
│ [Refresh Status]                     │
│                                      │
│ ┌─ Assemblers ────────────────────┐  │
│ │ • 64tass (Available)             │  │
│ │ • ca65 (Not installed)           │  │
│ │ • wla-dx (Available)             │  │
│ └──────────────────────────────────┘  │
│                                      │
│ ┌─ SDK ───────────────────────────┐  │
│ │ • pvsneslib (Available)          │  │
│ │ • dotnet8 (Not installed)        │  │
│ └──────────────────────────────────┘  │
│                                      │
│ ┌─ Emulators ─────────────────────┐  │
│ │ • lakesnes (Available)           │  │
│ │ • bsnes (Not installed)          │  │
│ └──────────────────────────────────┘  │
│                      [Close]         │
└──────────────────────────────────────┘
```

### 3. **Integration with snes-ide.py**

The main application has been enhanced with:

- **ScriptRunner Enhancement**: Added `ToolManager` initialization and tool status methods
- **MainWindow Enhancement**: Instantiates `ToolInstallerDialog` and exposes it via WebChannel
- **Web Channel Registration**: Registers the main window as "toolInstaller" for JavaScript access

#### New Methods in ScriptRunner

- `_init_tool_manager()` - Initializes tool manager with proper config path
- `get_tools_status()` - Returns all tools status as JSON
- `get_missing_required_tools()` - Returns missing required tools as JSON

#### New Method in MainWindow

- `show_tool_installer()` - Displays the tool installer dialog (Slot)

### 4. **HTML/JavaScript Integration**

Updated `index.html` to include:

- **New Button**: "Install Tools" button in the Utilities section
- **JavaScript Function**: `showToolInstaller()` to trigger dialog display
- **Web Channel**: Registers both scriptRunner and toolInstaller objects

#### Usage in HTML

```javascript
// Display the tool installer dialog
showToolInstaller();
```

## tools.json Structure

Each tool in `tools.json` requires:

```json
{
  "name": "tool-name",
  "description": "Tool description",
  "category": "category-name",
  "priority": "required|optional",
  "binary_name": {
    "linux": "binary-name",
    "darwin": "binary-name",
    "win32": "binary-name.exe"
  },
  "is_sdk": false,
  "verify_command": ["command", "arg"]
}
```

## Tool Categories

Tools are organized into the following categories:

- **assemblers** - 65816/6502 assemblers (64tass, ca65, wla-dx)
- **graphics** - Graphics tools (superfamiconv, libresprite, tiled)
- **audio** - Audio tools (schismtracker)
- **sdk** - Software Development Kits (pvsneslib, dotnet8, jdk8)
- **emulators** - SNES emulators (lakesnes, bsnes)
- **build-tools** - Build utilities (make)

## Tool Priorities

- **required** - Essential tools for SNES development
- **optional** - Enhancement tools not required for basic development

## Future Enhancements

The following features can be added in future versions:

1. **Tool Installation**: Implement automatic downloading and building from source
2. **Tool Patching**: Apply patches from `src/patches/` for specific systems
3. **Dependency Management**: Automatically install system dependencies
4. **Build Automation**: Orchestrate complex build processes
5. **Progress Indication**: Show installation progress with status updates
6. **Error Handling**: Provide detailed error messages and recovery suggestions
7. **Configuration**: Allow users to customize tool paths and versions
8. **Update Checking**: Notify users of tool updates

## Development Notes

### File Locations

- **Main Application**: `/src/snes-ide.py`
- **Tool Manager**: `/src/tool_manager.py`
- **Configuration**: `/src/tools.json`
- **UI Definition**: `/src/assets/index.html`
- **Patches**: `/src/patches/`

### Dependencies

- PySide6 - Qt framework for Python
- pathlib - Path utilities
- json - Configuration parsing
- subprocess - Tool verification
- shutil - System utilities

### Error Handling

The system includes robust error handling:

- Missing `tools.json` raises `FileNotFoundError`
- Invalid JSON raises `json.JSONDecodeError`
- Tool not found returns `None` or empty status
- Exceptions in dialog initialization are caught and logged

## Usage Example

```python
# Initialize tool manager
manager = ToolManager("/path/to/tools.json")

# Get all tools
all_tools = manager.get_all_tools()

# Check tool status
status = manager.get_tool_status(tool)
if status["available"]:
    print(f"✓ {status['name']} found at {status['path']}")
else:
    print(f"✗ {status['name']} not installed")

# Get missing required tools
missing = manager.get_missing_required_tools()
for tool in missing:
    print(f"Required tool missing: {tool['name']}")
```

## User Interface Flow

1. User clicks "Install Tools" button in Utilities section
2. `showToolInstaller()` JavaScript function is called
3. Web channel invokes `MainWindow.show_tool_installer()`
4. `ToolInstallerDialog` is displayed with current tool status
5. User can see which tools are installed
6. Future versions will allow installation of missing tools
7. User can refresh status or close the dialog

## System Compatibility

The tool installer is compatible with:

- **Linux**: Uses `which` command to find binaries
- **macOS**: Supports both Intel and Apple Silicon detection
- **Windows**: Handles `.exe` extensions and PATH detection

Platform-specific binary names are configured in `tools.json` for each tool.
