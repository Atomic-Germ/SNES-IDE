# SNES-IDE Build Systems Notes

## Overview
This project uses a multi-platform build strategy with separate scripts and tools for Windows, Linux, and macOS. Key build components include batch scripts, shell scripts, and Python automation.

## Build Tools & Scripts
- **Windows:**
  - `INSTALL.bat`, `build.bat` (batch scripts)
  - `bsnes.exe` (emulator binary)
- **Linux/macOS:**
  - `configure.sh`, `setup.sh`, `install.sh` (shell scripts)
  - Requires `zsh` (default shell), `oh-my-zsh`, and `gnu-sed` for advanced sed usage
  - Python3 available for automation
- **Python:**
  - `build.py` and other scripts in `src/` for build and tooling

## CI/CD
- **GitHub Actions:**
  - `.github/workflows/CI.yml` runs on Windows (`windows-latest`)
  - Executes `INSTALL.bat` for Windows builds
  - Triggers on pushes to main, feature, devel, bugfix branches, and tags

## Cross-Platform Strategy
- Windows uses batch scripts and Windows executables
- Linux/macOS use shell scripts and Python
- Platform-specific instructions likely in `BUILDING_FROM_SOURCE.md` and `README.md`
- Python scripts provide platform-independent automation

## Platform Requirements
- **macOS:**
  - `zsh` and `oh-my-zsh` for shell environment
  - `gnu-sed` for GNU-compatible sed commands
  - `python3` for scripting
- **Windows:**
  - Batch scripts and Windows binaries
- **Linux:**
  - Standard shell tools and Python

## Recommendations
- Always check platform-specific instructions in documentation
- Use Python scripts for automation when possible for cross-platform compatibility
- On macOS, prefer `gnu-sed` over BSD sed for script compatibility
