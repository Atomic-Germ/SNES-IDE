# Building and Environment Setup

This document lists the dependencies and suggestions for building tools with the SNES Installer.

## Recommended Disk Space

- Minimum: 1GB (light installs)
- Recommended: 2GB or more for full builds

If you receive a `No space left on device` error, free disk space before running the installer, or change the installation directory to a drive with more space.

You can run the installer in `--dry-run` mode to preview which tools would be processed without downloading or building anything. You can also override the installation directory and min-space threshold with `--install-dir DIR` and `--min-space MB`.

## Linux 

### Debian / Ubuntu

Install the basic build tools:

```bash
sudo apt update
sudo apt install -y build-essential cmake git curl unzip python3-pip
```

### Fedora

```bash
sudo dnf groupinstall "Development Tools"
sudo dnf install cmake git curl unzip python3-pip
```

**Optional (for Rust-based tools):**

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

## macOS

Install Xcode Command Line Tools:

```bash
xcode-select --install
```

Install Homebrew if needed and common dependencies:

```bash
brew install cmake git curl wget python3
```

## Windows

Using WSL is recommended for building CLI tools. Install WSL and a Linux distribution from the Microsoft Store, then follow the Linux instructions above.

For GUI tools, native Windows binaries (if available) or Visual Studio Build Tools may be required.

## Common Errors & Suggestions

- "No space left on device": Free disk space, remove old artifacts, or change the installation path (`~/.snes_tools` by default).
- "C compiler is not able to compile a simple test program": Install build tools such as `build-essential` (Linux), Xcode Command Line Tools (macOS), or Visual Studio Build Tools (Windows).
- "Download failed: 404 Not Found": Check the tool's URL in `tools_config.json` or update to a valid release tag.
- "Cargo not found": Install Rust via `rustup` for building Rust projects.

If problems persist, please file an issue with your OS, Python version, and the full install logs.
