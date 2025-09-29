<!-- markdownlint-disable-file -->
# Task Research Notes: Next binaries to port after pvsneslib

## Research Executed

### File Analysis
- `libs/` (top-level)
  - Found these subfolders: `M8TE/`, `bsnes/`, `font/`, `include/`, `libs/`, `notepad++/`, `pvsneslib/`, `template/` (listed from the repository workspace).
  - Evidence: directory listing of `/Users/caseyjparker/Upstreams/SNES-IDE/libs`.

- `libs/pvsneslib/`
  - Present locally and contains: `LICENSE`, `devkitsnes/`, `lib/`, `readme.md`, `tools/`.
  - Evidence: directory listing of `libs/pvsneslib`.

- `libs/pvsneslib/devkitsnes/bin`
  - Contains (local): `816-tcc.exe`, `wla-65816.exe`, `wla-spc700.exe`, `wlalink.exe`.
  - Evidence: directory listing of `libs/pvsneslib/devkitsnes/bin`.

### Code Search Results
- `.exe` references (selected matches in repo):
  - `libs/bsnes/bsnes.exe` — shipped Windows emulator.
  - `libs/notepad++/notepad++.exe` — shipped Windows editor.
  - `libs/pvsneslib/devkitsnes/bin/*` (referenced and used by `automatizer` and other tools) — now populated by the prebuilt archive.
  - `src/tools/audio-tools.py` references `snesbrr.exe`, `smconv.exe`, and related tools.
  - `src/tools/audio-tools.py` also references `schismtracker.exe` (tracker tool used by audio workflows).
  - `src/tools/automatizer-batch.bat` and `src/tools/automatizer-batch.ps1` reference `automatizer.exe`.
  - Tests: `tests/test_devkits_redlight.py` explicitly expects `wla-65816`, `wlalink`, `816-tcc`.
  - Evidence: repository grep for "\\.exe" and targeted file searches.

### External Research
- #githubRepo:"alekmaul/pvsneslib releases"
  - #fetch:https://github.com/alekmaul/pvsneslib/releases/tag/4.4.0
  - Key info: Release `4.4.0` includes a `pvsneslib` top-level folder containing `pvsneslib/`, `devkitsnes/`, and `snes-examples`; the prebuilt darwin zip provides devkits binaries used to satisfy the devkits red-light.

- #githubRepo:"bsnes-emu/bsnes"
  - #fetch:https://github.com/bsnes-emu/bsnes/releases
  - Key info: bsnes provides macOS release artifacts (nightly and release zips) that are safe to fetch in CI for macOS runtimes.

## Project Conventions
- Platform-native binaries are expected to live under `libs/<component>/<platform>/` (we use `libs/bsnes/mac/` for bsnes and `libs/pvsneslib/devkitsnes/` for devkits).
- Where possible we prefer system `PATH` tools; otherwise CI downloads place platform binaries in `libs/` for runtime detection by `platform_bridge` and tools.
- The project currently maintains Windows binaries in `libs/*` (do not remove or overwrite them) and adds platform-specific artifacts in parallel directories.

## Key Discoveries
- What the pvsneslib import accomplished (local evidence):
  - The prebuilt `pvsneslib_440_64b_darwin.zip` populates `libs/pvsneslib/devkitsnes/bin` with `816-tcc.exe`, `wla-65816.exe`, `wla-spc700.exe`, and `wlalink.exe`.
  - This satisfies the core devkit toolchain expected by the automatizer and related tests — the devkits red-light is now green.
- Remaining Windows-only or Windows-centric artifacts referenced in the repo:
  1. Editor: `libs/notepad++/notepad++.exe` — Notepad++ is Windows-only and must be replaced with platform-appropriate editor detection or provide an alternative on macOS (VS Code / Sublime / open).
  2. Audio tooling: `libs/pvsneslib/tools/*.exe` references (e.g., `snesbrr.exe`, `smconv.exe`, `snesmod` tooling), and external tracker `schismtracker.exe` — these are used by audio workflows and need macOS equivalents (prebuilt binaries or native ports).
  3. `automatizer.exe` (Windows binary) — batch/PowerShell wrappers currently reference `automatizer.exe` for Windows automation flows; Python `automatizer.py` exists and may provide a cross-platform path, but the `.exe` is referenced in some helper scripts.
  4. Other shipped Windows utilities across `tools/` and `libs/` (e.g., `schismtracker.exe`, `snesbrr.exe`, `smconv.exe`, `smconv.exe` references in `src/tools/audio-tools.py`).

## Recommended Approach (single selected solution)
- Strategy: Prioritize porting audio tooling and automation helpers (these are the most commonly used by workflows beyond compilation), then move to editor workflow improvements.
- Rationale: The devkits toolchain (assembler/linker/cc) is now available; the next blockers for a native macOS workflow are audio tooling and automation helpers which prevent running the test suite end-to-end or using audio features.

Priority list (recommended order):
1. Audio toolchain: `snesbrr`, `smconv`, `snesmod`, and `schismtracker` — provide macOS prebuilt binaries (if upstream provides), or build them in CI from source. Add red‑light tests that assert `libs/pvsneslib/tools/<tool>` or `shutil.which(<tool>)` exists on macOS CI.
2. Automation wrapper: `automatizer.exe` — evaluate whether `src/libs/pvsneslib/devkitsnes/automatizer.py` or other Python entrypoints can cover automation cross-platform; if not, add CI to build or provide a native replacement and update `src/tools/*` wrappers to detect platform and prefer Python wrapper on macOS.
3. Editor UX: Replace hard Windows-only editor references with macOS-friendly detection — prefer `code` (VSCode CLI), `subl`, `mate`, or `open`. Add a small red‑light test to assert that at least one editor launch path is available in CI (or document using `open`/TextEdit as minimal fallback).
4. Remaining small utilities in `libs` and `tools`: audit each `.exe` reference and either replace with a cross-platform Python script, fetch prebuilt macOS binaries, or add CI build steps.

## Implementation Guidance
- Objectives: Make macOS CI provide the missing runtime binaries so that the runtime, build tools, and tests can be executed natively on macOS runners.
- Key Tasks (actionable):
  - For each target tool (audio tools, automatizer, editor), add a red-light test to `tests/` asserting the presence of either a PATH-discoverable binary or a `libs/<component>/<platform>/` artifact.
  - For each target with an upstream that publishes macOS binaries, add a CI step (pattern used for pvsneslib and bsnes) that downloads the macOS release artifact, extracts canonical paths, and copies platform-specific binaries into `libs/`.
  - For targets without prebuilt macOS artifacts, add deterministic CI build steps (install build deps via Homebrew, run configure/make or waf) and copy produced binaries into `libs/` (mirroring the devkits fallback we already implemented).
  - For `automatizer.exe`, implement or reuse the Python automator entrypoint on macOS and update wrappers (`automatizer-batch.bat` / `.ps1`) to prefer the Python CLI on POSIX systems.
  - Add checksum verification and pin release tags for downloaded artifacts to make CI reproducible and auditable.

- Dependencies: Homebrew packages (build tools), Python 3.11, `tcl-tk` for GUI tests if needed, `pwsh` optionally for script compatibility.

- Success Criteria:
  - macOS CI tests that were previously failing for audio/automation now pass because the expected tools are available under `libs/` or on PATH.
  - The runtime `snes-ide.py` can perform the typical workflows (build, run emulator, process audio assets) on macOS without Wine.

## Next decision required
- Which target should I focus on next? Please choose one of the following and I will prepare a targeted implementation plan + CI changes (research files and red-light tests) for that item:
  - [ ] Audio tools (snesbrr, smconv, schismtracker)
  - [ ] Automation wrapper (`automatizer` / Python replacement)
  - [ ] Editor workflow (replace Notepad++ with macOS editor detection)
  - [ ] Full audit: add CI download/build steps for every `.exe` reference found and create per-tool red-light tests (larger change set)

**Selected file path:** `.copilot-tracking/research/20250928-next-binaries-research.md`

**Highlight:** The prebuilt pvsneslib archive already populated `libs/pvsneslib/devkitsnes/bin` with 816‑tcc/wla-65816/wla-spc700/wlalink, so the core compilation toolchain is now present. The most important remaining blockers for macOS native operation are audio tooling and the automatizer/editor wrappers — pick which I should tackle next.
