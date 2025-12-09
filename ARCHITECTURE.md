# Tool Installer Architecture

## System Components Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        SNES-IDE Application                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      MainWindow (QMainWindow)              │  │
│  │  • Manages main application window                         │  │
│  │  • Holds ToolInstallerDialog instance                      │  │
│  │  • Registers objects with QWebChannel                      │  │
│  │  • show_tool_installer() - Slot to display dialog          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                 │                                │
│                    ┌────────────┼────────────┐                   │
│                    ▼            ▼            ▼                   │
│   ┌──────────────────────┐  ┌─────────────────────────────┐      │
│   │  Web Channel Bridge  │  │   Web View (QWebEngineView) │      │
│   │  • scriptRunner      │  │   • Loads index.html        │      │
│   │  • toolInstaller     │  │   • Renders UI              │      │
│   │  (MainWindow ref)    │  │   • Handles user actions    │      │
│   └──────────────────────┘  └─────────────────────────────┘      │
│           │                         │                            │
│           │                         ▼                            │
│   ┌────────┴───────────────────────────────────────────────┐     │
│   │             JavaScript Layer (index.html)              │     │
│   │  • showToolInstaller() function                        │     │
│   │  • QWebChannel integration                             │     │
│   │  • UI event handlers                                   │     │
│   └────────────────────────────────────────────────────────┘     │
│           │ (Qt.connect)                                         │
│           ▼                                                      │
│   ┌────────────────────────────────────────────────────────┐     │
│   │             ScriptRunner (QObject)                     │     │
│   │  • Script execution                                    │     │
│   │  • ToolManager initialization                          │     │
│   │  • get_tools_status() - Returns JSON                   │     │
│   │  • get_missing_required_tools() - Returns JSON         │     │
│   └────────────────────────────────────────────────────────┘     │
│           │                                                      │
│           ▼                                                      │
│   ┌────────────────────────────────────────────────────────┐     │
│   │         ToolManager (Configuration + Logic)            │     │
│   │  • Loads tools.json configuration                      │     │
│   │  • Searches system PATH for binaries                   │     │
│   │  • Verifies tool functionality                         │     │
│   │  • Organizes tools by category/priority                │     │
│   └────────────────────────────────────────────────────────┘     │
│           │                                                      │
│           ▼                                                      │
│   ┌────────────────────────────────────────────────────────┐     │
│   │             tools.json (Configuration)                 │     │
│   │  • Tool definitions and metadata                       │     │
│   │  • Categories, priorities, descriptions                │     │
│   │  • Platform-specific binary names                      │     │
│   │  • Verification commands                               │     │
│   └────────────────────────────────────────────────────────┘     │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐     │
│   │      ToolInstallerDialog (QDialog - Optional Display)  │     │
│   │  • Displays tool status in scrollable dialog           │     │
│   │  • Groups tools by category                            │     │
│   │  • Shows installation status                           │     │
│   │  • Provides refresh capability                         │     │
│   │  • Future: Tool installation UI                        │     │
│   └────────────────────────────────────────────────────────┘     │
│           │                                                      │
│           ▼                                                      │
│   ┌────────────────────────────────────────────────────────┐     │
│   │        System PATH (Binary Detection)                  │     │
│   │  • Uses shutil.which() to find tools                   │     │
│   │ • Platform-aware binary name resolution                │     │
│   │  • Verification via subprocess execution               │     │
│   └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

### User Action → Tool Status Display

```
User clicks "Install Tools" button
        │
        ▼
    onClick event (HTML)
        │
        ▼
    showToolInstaller() (JavaScript)
        │
        ▼
    toolInstaller.show_tool_installer() (Qt Slot)
        │
        ▼
    MainWindow.show_tool_installer() method
        │
        ▼
    ToolInstallerDialog.show() (Display Dialog)
        │
        ▼
    Dialog references ScriptRunner.tool_manager
        │
        ▼
    ToolManager.get_tools_by_category()
        │
        ├─▶ Load tools.json  ◀─┐
        │                      │
        ├─▶ For each tool:     │
        │   • Check PATH       │
        │   • Get status       │ tools.json
        │   • Format data      │
        │    ◀─────────────────┘
        │
        ▼
    ToolInstallerDialog.create_tool_widget()
        │
        ├─▶ For each category:
        │   • Create QGroupBox
        │   ├─▶ For each tool:
        │   │   • Create widget
        │   │   • Display status
        │   │   • Show path
        │   └─▶ Add to group
        │
        ▼
    Display in QScrollArea
        │
        ▼
    User sees tool status
```

## Class Relationships

```
QObject
  │
  ├─▶ ScriptRunner
  │     • Manages script execution
  │     • Owns ToolManager instance
  │     • Emits signals to web view
  │
QDialog
  │
  ├─▶ ToolInstallerDialog
  │     • Uses ScriptRunner.tool_manager
  │     • Creates tool widgets
  │     • Manages dialog UI state

QMainWindow
  │
  ├─▶ MainWindow
  │     • Creates ScriptRunner
  │     • Creates ToolInstallerDialog
  │     • Manages QWebChannel
  │     • Exposes show_tool_installer slot

ToolManager (No Qt base)
  │
  └─▶ Utility class for tool operations
      • No Qt dependency
      • Can be used standalone
      • Reusable in CLI tools
```

## Configuration Loading Flow

```
Application Start
        │
        ▼
    MainWindow.__init__()
        │
        ├─▶ Creates ScriptRunner
        │     │
        │     ├─▶ Determines executable path
        │     │   (frozen vs development)
        │     │
        │     └─▶ Calls _init_tool_manager()
        │         │
        │         ▼
        │         ToolManager(tools_json_path)
        │         │
        │         └─▶ load_config()
        │             │
        │             ▼
        │             Load tools.json
        │             │
        │             ▼
        │             Parse JSON
        │             │
        │             ▼
        │             Store in tools_config
        │
        └─▶ Creates ToolInstallerDialog
            │
            ├─▶ init_ui()
            │   • Creates UI elements
            │   • Doesn't load tools yet
            │
            └─▶ load_tools_status()
                • Queries ToolManager
                • Builds category groups
```

## Error Handling Flow

```
ToolManager initialization
        │
        ├─▶ tools.json not found
        │   └─▶ FileNotFoundError
        │       └─▶ Caught in _init_tool_manager
        │           └─▶ Fallback to default path
        │
        ├─▶ Invalid JSON
        │   └─▶ json.JSONDecodeError
        │       └─▶ Caught in load_config
        │           └─▶ Error message to console
        │
        ├─▶ Tool not in PATH
        │   └─▶ shutil.which() returns None
        │       └─▶ Status marked as unavailable
        │
        └─▶ Verification command fails
            └─▶ subprocess exception
                └─▶ Tool marked as unverified
```

## Performance Considerations

1. **Lazy Loading**: Tool status only loaded when dialog opened
2. **Efficient Search**: Uses system PATH search via shutil.which()
3. **Caching**: Tool status cached during dialog lifetime
4. **Refresh**: User can refresh to reload status
5. **Scrollable UI**: Handles many tools without performance issues
6. **No Blocking**: Tool detection doesn't block main thread

## Integration Points

### With ScriptRunner
- Shares path resolution logic
- Uses same executable detection
- Tool verification alongside script execution

### With Web Channel
- Slots exposed for JavaScript calls
- JSON serialization for data transfer
- Qt signal-slot mechanism for events

### With tools.json
- Reads complete tool configuration
- Uses for tool discovery
- Provides metadata for display

## Future Integration Points

1. **Tool Installation Scripts** *COMPLETED*
   - Call download/build scripts
   - Track progress
   - Update status after installation

2. **Dependency Installation** *COMPLETED*
   - Read system_requirements from tools.json
   - Call package manager (apt, brew, dnf, etc.)
   - Handle platform differences

3. **Patch Application**
   - Read patch configuration
   - Apply patches to source
   - Detect when patches are needed

4. **Build Orchestration**
   - Execute build commands
   - Manage build environment
   - Handle build failures

5. **Configuration Management**
   - Allow custom tool paths
   - Save preferences
   - Restore on restart
