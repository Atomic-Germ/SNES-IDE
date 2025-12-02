# Tool Installer Quick Start Guide

## Overview

The Tool Installer feature has been successfully added to SNES-IDE. It provides a user-friendly interface to:
- ✅ View all configured tools
- ✅ Check installation status (installed/not installed)
- ✅ See tool paths and descriptions
- ✅ Refresh tool status
- 🔜 Install missing tools (future implementation)

## How to Use

### Opening the Tool Installer

1. Launch SNES-IDE application
2. Look for the **Utilities** section on the main screen
3. Click the **"Install Tools"** button
4. The Tool Installer dialog will appear

### Reading the Tool Status

The dialog displays tools organized by category:

- **Category Headers** (Assemblers, SDK, Emulators, etc.)
  - Each category groups related tools together
  
- **Tool Information**
  - **Tool Name** (bold text)
  - **Description** (gray text)
  - **Status** (green ✓ or red ✗)
    - Green ✓ = Tool is installed
    - Red ✗ = Tool is not installed
  - **Path** (if installed) - Shows where the tool is located

### Actions

- **Refresh Status** - Click the "Refresh Status" button to reload tool information
- **Close** - Click the "Close" button to close the dialog
- **Future Install Button** - Will allow installation of missing tools

## File Structure

```
src/
├── snes-ide.py                 # Main application (updated)
├── tool_manager.py             # NEW: Tool management logic
├── tools.json                  # Configuration file
├── assets/
│   ├── index.html             # UI interface (updated)
│   └── styles.css
└── scripts/
    └── *.py                   # Existing scripts
```

## What's New

### New File: `src/tool_manager.py`
- Core tool management functionality
- ~220 lines of code
- Standalone utility that can be reused
- No Qt dependency

### Updated: `src/snes-ide.py`
- Added imports for tool management (+12 lines)
- Enhanced ScriptRunner class (+30 lines)
- New ToolInstallerDialog class (+120 lines)
- Updated MainWindow (+10 lines)

### Updated: `src/assets/index.html`
- Added "Install Tools" button in Utilities section (+15 lines)
- Updated JavaScript to integrate with tool installer

## Technical Requirements

### Python Dependencies
- PySide6 (already required)
- Standard library modules: json, pathlib, sys, subprocess, shutil

### System Requirements
- Works on Windows, macOS, and Linux
- No additional system tools required for basic operation

## Configuration

Tool configuration is stored in `src/tools.json` with structure:

```json
{
  "tools": [
    {
      "name": "tool-name",
      "description": "What the tool does",
      "category": "category-name",
      "priority": "required|optional",
      "binary_name": {
        "linux": "binary-name",
        "darwin": "binary-name",
        "win32": "binary-name.exe"
      },
      "verify_command": ["command", "arg"]
    }
  ]
}
```

## Categories

Tools are organized into these categories:

| Category | Purpose | Examples |
|----------|---------|----------|
| assemblers | 65816/6502 assembly | wla-dx, ca65, 64tass |
| graphics | Image/sprite tools | superfamiconv, libresprite, tiled |
| audio | Sound tools | schismtracker |
| sdk | Development frameworks | pvsneslib, dotnet8, jdk8 |
| emulators | SNES emulators | lakesnes, bsnes |
| build-tools | Build utilities | make |

## Tool Priorities

- **required** - Must have for basic SNES development
- **optional** - Nice to have, enhances workflow

## Troubleshooting

### Tools Not Showing Up
1. Check that `tools.json` exists in `src/` directory
2. Verify JSON syntax is valid
3. Restart the application

### Tools Show as "Not Installed" When They Are
1. Click "Refresh Status" button
2. Check that the tool binary name in `tools.json` matches the actual binary name
3. Ensure the tool's installation directory is in system PATH
4. On Windows, verify the `.exe` extension is correct

### Dialog Won't Open
1. Check application console for error messages
2. Verify PySide6 is installed correctly
3. Ensure tool_manager.py is in the same directory as snes-ide.py

## Future Enhancements

The following features are planned:

1. **Automatic Installation**
   - Download source code from GitHub
   - Build from source using platform-specific build commands
   - Install to system or user-local directory

2. **Dependency Management**
   - Automatically install system dependencies
   - Support for apt, brew, dnf, pacman

3. **Patch Application**
   - Apply platform-specific patches
   - Handle 16K pagesize systems (Asahi Linux)

4. **Progress Tracking**
   - Show download/build progress
   - Estimate time remaining
   - Allow cancellation

5. **Configuration**
   - Customize tool installation paths
   - Manage multiple tool versions
   - Save preferences

6. **Update Checking**
   - Check for tool updates
   - Notify user of new versions
   - Quick update functionality

## Example: Adding a New Tool

To add a new tool to the installer:

1. Edit `src/tools.json`
2. Add an entry to the `tools` array:

```json
{
  "name": "New Tool",
  "description": "Tool description",
  "category": "category-name",
  "priority": "optional",
  "binary_name": {
    "linux": "binary-name",
    "darwin": "binary-name",
    "win32": "binary-name.exe"
  },
  "verify_command": ["binary-name", "--version"]
}
```

3. Save the file
4. Restart SNES-IDE or click "Refresh Status"
5. The new tool will appear in the Tool Installer dialog

## Code Examples

### Getting Tool Status from Python

```python
from tool_manager import ToolManager

# Initialize
manager = ToolManager("path/to/tools.json")

# Get all tools
all_tools = manager.get_all_tools()

# Check specific tool
status = manager.get_tool_status(all_tools[0])
print(f"Tool: {status['name']}")
print(f"Available: {status['available']}")
print(f"Path: {status['path']}")

# Get missing required tools
missing = manager.get_missing_required_tools()
for tool in missing:
    print(f"Missing: {tool['name']}")
```

### Using with Qt/Web Channel

```python
# The dialog handles it automatically:
# 1. MainWindow instantiates ToolInstallerDialog
# 2. User clicks "Install Tools" button
# 3. JavaScript calls toolInstaller.show_tool_installer()
# 4. Dialog displays with current tool status
```

## Support

For issues or questions:
1. Check the `ARCHITECTURE.md` file for detailed architecture
2. Review `TOOL_INSTALLER.md` for complete documentation
3. Check `IMPLEMENTATION_SUMMARY.md` for what was added
4. Open an issue on GitHub

## Version Information

- **Feature Added**: December 2025
- **SNES-IDE Version**: Mini Branch
- **Status**: Fully functional (display only, installation in progress)

---

**Happy Developing! 🎮**
