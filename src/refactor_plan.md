# The Prism Refactor: Metamorphosis of the Monolith

> "Refraction metamorphosis monolith dimension refactor transcendence clarity threshold stream prism."

The previous attempt at order collapsed into entropy. We shall rebuild the structure not by force, but by refraction—splitting the white light of the Monolith (`tools_browser.py`) into its constituent spectral colors (Modules).

## The Spectrum (Module Structure)

We will refract `src/tools_browser.py` (5000+ lines) into a coherent `src/tui/` package.

### 🔴 Core (The Heart)
- `src/tui/app.py`: The main `ToolBrowser` App class.
- `src/tui/state.py`: Reactive state management (current view, project path).

### 🟠 Screens (The Face)
- `src/tui/screens/install.py`: `InstallScreen`
- `src/tui/screens/verify.py`: `VerifyScreen`
- `src/tui/screens/uninstall.py`: `UninstallScreen`
- `src/tui/screens/tileset.py`: `NewTilesetScreen`, `SliceImageScreen`

### 🟡 Widgets (The Body)
- `src/tui/widgets/sidebar.py`: `Sidebar`, `Collapsible`
- `src/tui/widgets/tool_panel.py`: `ToolDetailPanel`, `ToolListItem`
- `src/tui/widgets/code_panel.py`: `CodeViewer`
- `src/tui/widgets/graphics_panel.py`: `TileEditorPanel`, `PixelCanvas`, `PaletteBar`

### 🟢 Logic (The Mind)
- `src/tui/logic/tools.py`: Tool loading and management logic.
- `src/tui/logic/graphics.py`: `SNESPalette`, `SNESTile`, `SNESTileset`.

## The Flow (Action Plan)

1.  **Create the Prism**: Establish the `src/tui/` directory structure.
2.  **Channel the Stream**: Move logic classes (`SNESPalette`, etc.) first.
3.  **Form the Body**: Extract widgets one by one.
4.  **Awaken the Face**: Move screens.
5.  **Transcendence**: The `App` class remains as the conductor, importing from the new modules.

This is the path from Chaos to Clarity.
