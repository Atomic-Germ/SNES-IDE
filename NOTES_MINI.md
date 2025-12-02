# SNES-IDE Mini — Build-On-Demand Planning Notes

## Goals and Constraints
- Deliver an alternative distribution alongside the traditional AppImage/zip bundles that contains *no pre-built binaries* in `bin/`, yet can still bootstrap every required tool locally when the user asks SNES-IDE to install or run something.
- Support "odd" environments (e.g., Asahi Linux on Apple Silicon with 16K pages) by compiling from source, optionally applying patches, and detecting system traits dynamically.
- Re-use the existing desktop application (`src/snes-ide.py` + Qt/HTML front-end) as the *installer UI*. No separate installer binary should exist; the IDE already orchestrates tool setup through Python scripts.
- Preserve the existing UX for the regular distribution—`SNES-IDE-out` keeps shipping pre-built payloads—while the new `SNES-IDE-MINI-out` relies on the on-demand builder.

## Current Distribution Architecture
### Build pipeline (build/build.py)
1. `clean_all()` removes `SNES-IDE-out/`.
2. `restore_big_files()` scans `resources/` for `*.snes.ide.reconstruct.manifest.json` and reassembles large binaries from chunk files.
3. Copies root files, libraries, docs, and `resources/bin/<os>` payloads into `SNES-IDE-out/`.
4. `decompress_zip_files_in_out()` inflates archives (e.g., packaged SDK zips) so installers contain ready-to-run directories.
5. `generate_bundle()` wraps the output via `BundleCreator`, creating platform-specific bundles (AppDir/AppImage skeleton on Linux, `.app` on macOS, portable tree + launcher on Windows). Dependencies are installed into an embedded virtual environment (see `build/requirements.txt`).

### Runtime layout expectations
- When shipped, the bundle contains:
  - `bin/` — OS-specific executables (assemblies, emulators, SDKs). Copied from `resources/bin/<platform>`.
  - `libs/` — Shared libraries/templates (`resources/libs`). Scripts copy template projects from here.
  - `docs/` — Example projects and manuals.
  - `src/` — Application Python sources, Qt assets, and helper scripts.
- Every Python helper script (under `src/scripts/`) resolves `home_path = Path(script_dir).parent`. They assume `home_path/bin` already contains the necessary executables and SDKs. Example: `compile-pvsneslib-proj.py` expects `bin/pvsneslib/{devkitsnes,tools,...}` plus `bin/make/<make>`.

### Resource directories today
- `resources/bin/`
  - Subdirectories per platform (`linux`, `macos`, `windows`) sharing the same high-level tool names: `dotnet8`, `jdk8`, `make`, `pvsneslib`, `schismtracker`, `snes-emulator`, `sprite-editor`, `tmx-editor`.
  - Heavy payloads (dotnet SDK, JDK, bsnes, etc.) are chunked via `resources/split-big-files.py`; manifests live next to the chunks for reconstruction.
  - Some tools remain zipped (e.g., `tiled.AppImage`). Build script inflates these after copying.
- `resources/libs/`
  - `pvsneslib/` templates referenced by project creation scripts.
  - `DotnetSnesLib/`, `DntcTranspiler/`, `javasnes/`, `SampleLibrary/` for additional frameworks and examples consumed at runtime.

## Application Structure Recap
- `src/snes-ide.py` boots a PySide6 GUI window, loads `src/assets/index.html` into `QWebEngineView`, and exposes `ScriptRunner` via `QWebChannel`.
- The HTML (and `assets/styles.css`) provide the menu of actions (create project, compile, graphics/audio tools, open emulator, etc.). Buttons call `scriptRunner.runScript('...py')`.
- Every script under `src/scripts/` performs a focused task (compile, convert assets, open emulator). They all rely on `get_file_path.py` to prompt for files/dirs and on binaries placed in `home_path/bin`.
- Therefore, **SNES-IDE itself is the installer**: launching one of these scripts should ensure the dependencies exist (currently guaranteed because builders ship them). For the mini variant we must intercept these scripts (or provide a lower-level `ToolManager`) so they can trigger a build/install before running the external command.

## Tool Metadata Sources
### build/tools.json (missing locally)
- The instructions mention `build/tools.json` contains detailed metadata for the existing prebuilt toolchain, but the file is absent in the `mini` branch workspace. Need to confirm whether it lives in another branch or is generated during CI. If present elsewhere, it likely mirrors `src/tools_mini.json` but geared toward packaging binary artifacts.

### src/tools_mini.json (current mini config draft)
- Describes the prospective build-on-demand catalog.
- `system_requirements`: minimal packages per platform family (`apt`, `dnf`, `brew`, `msys2`).
- `tools`: array of tool definitions. Important fields:
  - `source`: `git`, `tarball`, or installer script, with optional branch/tag and strip options.
  - `build.commands`: shell snippets per OS. Many use `cmake && make`, others `autoreconf` or plain `make`.
  - `dependencies`: platform package hints (should map to whichever OS the user actually runs).
  - `binary_path`/`binary_name`: relative path inside the build directory and the final exe name per OS.
  - `is_sdk` toggles non-binary toolkits (pvsneslib, dotnet, jdk).
  - `patches`: references into `patch_sets` (currently only `16k-pagesize`).
  - `post_install` actions (e.g., for `pvsneslib`, create symlinks from `devkitsnes/bin` to `bin`).
  - `verify_command`: command used to confirm the install succeeded.
- Catalog overview (all entries already enumerated inside the JSON):
  - Assemblers: `64tass`, `ca65`, `wla-dx` (required), `superfamiconv` (graphics converter but tool-like).
  - SDKs/frameworks: `pvsneslib` (required, has patch + symlinks), `dotnet8`, `jdk8`.
  - Emulators: `lakesnes` (required) and `bsnes` (optional but patched for 16K).
  - Audio/graphics apps: `schismtracker`, `libresprite`, `tiled`.
  - Build essentials: `make` (prefers system binary but can fall back to source build).
- `patch_sets`: `16k-pagesize` has detection conditions but no files yet; we will need to populate `src/patches/16k-pagesize/<tool>/...` with actual diffs.
- `platform_detection`: helper probes for Asahi-based Linux and page-size detection.

## Patching & Special-Case Handling
- `src/patches/16k-pagesize/README.md` outlines how to organize per-tool patch folders (e.g., `lakesnes/mmap-alignment.patch`).
- Tool definitions referencing `"patches": ["16k-pagesize"]` will need automation to:
  1. Detect via `getconf PAGESIZE` whether the patch set applies.
  2. Copy/patch files from `src/patches/16k-pagesize/<tool>/` into the build tree before the `build.commands` run.
- Additional patch sets can be added the same way (e.g., for distro-specific quirks).

## Deliverable Layout for SNES-IDE-MINI-out
- Create a new build target (parallel to `SNES-IDE-out`) that runs all the same steps *except copying `resources/bin/<os>` and decompressing archives*. Instead, include:
  - `src/` (unchanged) plus the new `tools_mini.json`, patch folders, and any helper module that performs builds.
  - `libs/` and `docs/` (still needed for project templates and samples).
  - A lightweight bootstrapper script (maybe `src/tool_manager.py`) that can:
    * Parse `tools_mini.json`.
    * Detect the host OS/arch/page size.
    * Check/prepare system dependencies (inform user to install packages).
    * Download source archives or clone repos to a writable cache (e.g., `~/.snes-ide/tools/src/<tool>`).
    * Apply optional patches.
    * Run `build.commands` sequentially while streaming logs back to the UI.
    * Copy resulting binaries into `home/bin/<tool>` (matching the layout expected by existing scripts) and mark them as installed (maybe via a manifest in `bin/.installed-tools.json`).
    * Run `verify_command` to ensure success.
- Both distributions can share the same `src/` codebase if runtime checks (e.g., `if not tool_installed: install_tool(...)`) are added to each script or to a centralized wrapper invoked before launching external commands.
- Potential workflow for a script like `open-emulator.py` in the mini build:
  1. Ensure `bin/snes-emulator/lakesnes` exists; otherwise call `tool_manager.ensure("lakesnes")`.
  2. `ensure()` downloads/builds using `tools_mini.json`.
  3. Once done, run the emulator as today.
- Consider caching built artifacts to avoid re-compilation and enabling uninstall/upgrade commands.

## Integration Points and Required Work
1. **Tool manager module**
   - Lives under `src/` so both GUI and scripts can import it.
   - Provides a CLI (for debugging) and Python API (`ensure(tool_name)`, `list_installed()`, `install_all(priority=required)`, etc.).
   - Persists install metadata (versions, commit hashes) to a JSON file under `bin/` so we can skip rebuilds unless sources change.
2. **Script wrappers**
   - Either modify each script to call the manager for the tools it consumes or centralize the logic in a decorator/helper to minimize duplication.
   - Example mapping: `compile-pvsneslib-proj.py` depends on `make`, `pvsneslib`. `compile-dotnetsnes-proj.py` depends on `make`, `pvsneslib`, `dotnet8`. `open-emulator.py` depends on `lakesnes` (and optionally `bsnes`).
3. **Mini build pipeline**
   - Add a new entry point (maybe `build/build_mini.py`) or extend `build/build.py` with a flag to skip `copy_bin()` and instead place `src/tools_mini.json`, patch folders, and new python modules into `SNES-IDE-MINI-out/`.
   - Document the difference in `README.md` so users know when to pick the mini build.
4. **Dependency install guidance**
   - Provide user-facing docs (maybe extend this file or add `docs/MINI.md`) showing how to install `apt/dnf/brew/msys2` packages listed in `system_requirements` before running the builder.
5. **Patch content**
   - Fill in actual patches for `lakesnes`, `bsnes`, `pvsneslib` once failures are reproduced on 16K-page systems. The `files` array in `tools_mini.json.patch_sets` should reference those patch files.
6. **Logging & UX**
   - Decide how build logs surface in the Qt UI (e.g., reuse the status bar, add a dedicated log view, or stream to console only).

## Outstanding Questions / Open Items
- `build/tools.json` is mentioned but not present on the `mini` branch. Need to locate or reconstruct it to ensure parity between the legacy prebuilt flow and the new mini flow.
- Define where source tarballs/clones should live at runtime (inside the app directory vs user home). For writable installs we likely need to operate outside the read-only AppImage; consider using `~/.local/share/snes-ide/tools/`.
- Confirm how `SNES-IDE-MINI-out` will be distributed (AppImage skeleton without binaries? zipped source?). Might need to keep the embedded Python venv (like the standard build) so users still get PySide6 even though tools are absent.
- Establish security/trust model for fetching source tarballs at install time (checksum verification, pinned tags, optional offline mirrors).
- Decide whether `tools_mini.json` should support per-architecture overrides (x86_64 vs arm64) beyond the placeholder URLs in `jdk8`.
- Determine upgrade/uninstall story (e.g., rerun builder to install updated tool versions or rebuild when config version increments).

These notes capture the current repository layout, the expectations of every component that touches tool binaries, and the scaffolding already present (`tools_mini.json`, patch directories) for the new build-on-demand workflow. They should be sufficient context to start implementing the SNES-IDE Mini tool manager and the parallel packaging flow.
