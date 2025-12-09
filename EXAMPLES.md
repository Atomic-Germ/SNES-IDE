# Tool Installer Examples and Use Cases

## Example 1: Basic Tool Status Display

### User Perspective

1. Launch SNES-IDE
2. Navigate to Utilities section
3. Click "Install Tools" button
4. Dialog opens showing:
   ```
   ✓ wla-dx (Assemblers)
   ✗ ca65 (Assemblers)
   ✓ pvsneslib (SDK)
   ✗ dotnet8 (SDK)
   ✓ lakesnes (Emulators)
   ✗ bsnes (Emulators)
   ```

### Code Level

```python
# In ToolInstallerDialog
tools_by_category = self.script_runner.tool_manager.get_tools_by_category()

# Result:
{
    'assemblers': [
        {
            'name': 'wla-dx',
            'available': True,
            'path': '/usr/bin/wla-65816',
            'category': 'assemblers',
            'priority': 'required',
            'description': 'Multi-platform assembler with SNES support',
            'is_sdk': False
        },
        {
            'name': 'ca65',
            'available': False,
            'path': None,
            'category': 'assemblers',
            'priority': 'optional',
            'description': '6502 assembler (cc65 suite)',
            'is_sdk': False
        }
    ],
    # ... more categories
}
```

## Example 2: Checking for Missing Required Tools

### Use Case
A developer wants to know what critical tools are missing.

### Code

```python
from tool_manager import ToolManager

manager = ToolManager("src/tools.json")
missing = manager.get_missing_required_tools()

if missing:
    print("⚠️  Missing required tools:")
    for tool in missing:
        print(f"  • {tool['name']}: {tool['description']}")
else:
    print("✓ All required tools are installed!")
```

### Output Example
```
⚠️  Missing required tools:
  • pvsneslib: Complete SNES development framework - builds from source
  • wla-dx: Multi-platform assembler with SNES support (wla-65816)
```

## Example 3: Tool Organization by Category

### Use Case
Organizing tools for display in the UI.

### Code

```python
manager = ToolManager("src/tools.json")
tools_by_cat = manager.get_tools_by_category()

for category in sorted(tools_by_cat.keys()):
    print(f"\n{category.upper()}")
    print("=" * 40)
    
    for tool in tools_by_cat[category]:
        status_icon = "✓" if tool["available"] else "✗"
        priority = "[REQUIRED]" if tool["priority"] == "required" else "[OPTIONAL]"
        
        print(f"{status_icon} {tool['name']:<20} {priority}")
        if tool["available"]:
            print(f"  └─ {tool['path']}")
```

### Output Example
```
ASSEMBLERS
========================================
✓ wla-dx                 [REQUIRED]
  └─ /usr/bin/wla-65816
✗ ca65                   [OPTIONAL]
✗ 64tass                 [OPTIONAL]

SDK
========================================
✓ pvsneslib              [REQUIRED]
  └─ /usr/local/snesdev/pvsneslib
✗ dotnet8                [OPTIONAL]
✗ jdk8                   [OPTIONAL]

EMULATORS
========================================
✓ lakesnes               [REQUIRED]
  └─ /usr/bin/lakesnes
✗ bsnes                  [OPTIONAL]

GRAPHICS
========================================
✓ superfamiconv          [REQUIRED]
  └─ /usr/local/bin/superfamiconv
✓ tiled                  [REQUIRED]
  └─ /usr/bin/tiled
✗ libresprite            [OPTIONAL]

AUDIO
========================================
✗ schismtracker          [OPTIONAL]

BUILD-TOOLS
========================================
✓ make                   [REQUIRED]
  └─ /usr/bin/make
```

## Example 4: Verifying Tool Functionality

### Use Case
Ensuring a tool not only exists but actually works.

### Code

```python
manager = ToolManager("src/tools.json")

# Verify specific tool
is_valid = manager.verify_tool("wla-dx")

if is_valid:
    print("✓ wla-dx is properly installed and working")
else:
    print("✗ wla-dx failed verification")
    print("  Check that /path/to/wla-65816 -V works correctly")
```

## Example 5: Real-time Status Update

### Use Case
Dialog updates tool status when user clicks "Refresh Status".

### Code

```python
class ToolInstallerDialog(QDialog):
    def load_tools_status(self) -> None:
        """Reload and display current tool status."""
        try:
            # Force reload
            tools_by_category = self.script_runner.tool_manager.get_tools_by_category()
            
            # Update UI with fresh data
            self.tool_groups.clear()
            
            for category in sorted(tools_by_category.keys()):
                group = QGroupBox(category.title())
                # ... populate group with fresh tool data
                self.tool_groups[category] = group
                
            self.status_label.setText(
                f"Status updated at {time.strftime('%H:%M:%S')}"
            )
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
```

## Example 6: Tool Detection on Different Platforms

### Linux Example
```bash
# tools.json specifies binary names per platform
"binary_name": {
    "linux": "wla-65816",
    "darwin": "wla-65816",
    "win32": "wla-65816.exe"
}

# On Linux, searches PATH for 'wla-65816'
# Found at: /usr/bin/wla-65816
```

### macOS Example
```bash
# On macOS (darwin), searches PATH for 'wla-65816'
# Found at: /usr/local/bin/wla-65816
```

### Windows Example
```bash
# On Windows (win32), searches PATH for 'wla-65816.exe'
# Found at: C:\Tools\wla-65816.exe
```

## Example 7: Integration with Build System

### Future Use Case
Once tool installation is implemented, the system could:

```python
# After user clicks "Install wla-dx"
manager = ToolManager("src/tools.json")
tool = manager.get_tool_by_name("wla-dx")

# Download source
download_tool(tool)

# Apply patches if needed
for patch in tool.get("patches", []):
    apply_patch(patch)

# Build from source
build_command = tool["build"]["linux"]["commands"]
run_build(build_command)

# Verify installation
if manager.verify_tool("wla-dx"):
    show_notification("✓ wla-dx installed successfully!")
    refresh_ui()
else:
    show_error("Installation verification failed")
```

## Example 8: JSON Output for Web Integration

### Web Channel Communication

```python
# ScriptRunner.get_tools_status() returns JSON

json_output = {
    "assemblers": [
        {
            "name": "64tass",
            "available": False,
            "path": None,
            "category": "assemblers",
            "priority": "optional",
            "description": "6502/65816 assembler",
            "is_sdk": False
        }
    ],
    "sdk": [
        {
            "name": "pvsneslib",
            "available": True,
            "path": "/usr/local/snesdev/pvsneslib",
            "category": "sdk",
            "priority": "required",
            "description": "Complete SNES development framework",
            "is_sdk": True
        }
    ]
    # ... more categories
}

# JavaScript receives this as JSON and renders UI
```

## Example 9: Configuration Example (tools.json)

```json
{
  "version": "1.0.0",
  "tools": [
    {
      "name": "wla-dx",
      "description": "Multi-platform assembler with SNES support (wla-65816)",
      "category": "assemblers",
      "priority": "required",
      "binary_name": {
        "linux": "wla-65816",
        "darwin": "wla-65816",
        "win32": "wla-65816.exe"
      },
      "verify_command": ["wla-65816", "-V"],
      "is_sdk": false
    },
    {
      "name": "pvsneslib",
      "description": "Complete SNES development framework",
      "category": "sdk",
      "priority": "required",
      "is_sdk": true,
      "verify_command": ["bash", "-c", "test -d /usr/local/snesdev/pvsneslib"]
    }
  ]
}
```

## Example 10: Error Handling Scenarios

### Missing Configuration File

```python
try:
    manager = ToolManager("/nonexistent/tools.json")
except FileNotFoundError:
    print("Error: tools.json not found")
    # Fall back to default location
    manager = ToolManager()
```

### Invalid JSON

```python
try:
    manager = ToolManager("malformed.json")
except json.JSONDecodeError as e:
    print(f"Error parsing tools.json: {e}")
    # Show user-friendly error
```

### Tool Not Found

```python
manager = ToolManager("src/tools.json")
status = manager.get_tool_status(some_tool)

if not status["available"]:
    print(f"Tool '{status['name']}' not found in PATH")
    print(f"Install it or add its directory to PATH")
else:
    print(f"Tool found at: {status['path']}")
```

## Example 11: Batch Operations

### Get All Tool Information

```python
manager = ToolManager("src/tools.json")

# Get everything
all_tools_status = manager.get_all_tools_status()

# Filter operations
required_tools = [t for t in all_tools_status if t["priority"] == "required"]
available_tools = [t for t in all_tools_status if t["available"]]
sdk_tools = [t for t in all_tools_status if t["is_sdk"]]

print(f"Total tools: {len(all_tools_status)}")
print(f"Required: {len(required_tools)}")
print(f"Available: {len(available_tools)}")
print(f"SDKs: {len(sdk_tools)}")
```

## Example 12: Custom Tool Discovery

### Using ToolManager as a Library

```python
from tool_manager import ToolManager

class CustomToolDiscovery:
    def __init__(self, config_path):
        self.manager = ToolManager(config_path)
    
    def get_status_report(self):
        """Generate a detailed status report."""
        report = {}
        
        for tool_status in self.manager.get_all_tools_status():
            name = tool_status["name"]
            available = tool_status["available"]
            
            report[name] = {
                "status": "Ready" if available else "Missing",
                "path": tool_status["path"],
                "priority": tool_status["priority"]
            }
        
        return report
    
    def is_development_ready(self):
        """Check if all required tools are available."""
        missing = self.manager.get_missing_required_tools()
        return len(missing) == 0

# Usage
discovery = CustomToolDiscovery("src/tools.json")

if discovery.is_development_ready():
    print("✓ System is ready for SNES development!")
else:
    print("Install missing tools to begin development")
```

---

These examples demonstrate the flexibility and reusability of the Tool Installer system for various use cases and integration scenarios.
