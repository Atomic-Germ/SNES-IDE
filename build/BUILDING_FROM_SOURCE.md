# Build Instructions

This document explains the build process and provides a way to verify if the build executed successfully.

---

## Required Dependencies for building from source

- **Python 3.8 or newer:**  
  Required for running Python scripts and tooling.  
  - Windows/macOS: Download from the [official Python website](https://www.python.org/downloads/).
  - Linux: Install via package manager (`sudo apt install python3`).

- **PyInstaller (optional):**  
  For creating standalone executables. Install with: `pip install pyinstaller`

---

## Build Process Overview

To build this project from source, follow these steps:

1. **Install Dependencies:**  
  Ensure all required tools and libraries are installed on your system.

2. **Build the Project:**  
  Run the build script for your platform:

  **Windows:** `build\build.bat`
  **macOS/Linux:** `python3 build/build.py [platform]`
  
  Where `[platform]` is one of: `windows`, `macos`, `linux`

---

## Platform-Specific Build Instructions

### Windows

```bat
cd C:\path\to\SNES-IDE
build\build.bat
```

### macOS

```bash
cd /path/to/SNES-IDE
python3 build/build.py macos
```

### Linux

```bash
cd /path/to/SNES-IDE
python3 build/build.py linux
```

---

## Build Output

After a successful build, the `SNES-IDE-out` directory will contain installation scripts and files for your platform
