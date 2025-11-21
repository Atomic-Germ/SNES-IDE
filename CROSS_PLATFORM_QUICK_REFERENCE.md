# SNES-IDE Cross-Platform Quick Reference

## Building SNES-IDE

### Windows
```batch
build.bat build      REM Build application
build.bat clean      REM Clean artifacts
build.bat prepare    REM Setup environment
build.bat dev        REM Run in dev mode
build.bat lint       REM Run linting
```

### macOS / Linux
```bash
./build.sh build      # Build application
./build.sh clean      # Clean artifacts
./build.sh prepare    # Setup environment
./build.sh dev        # Run in dev mode
./build.sh lint       # Run linting
```

### All Platforms (Direct Python)
```bash
python build_system.py build
python build_system.py clean
python build_system.py prepare
python build_system.py rebuild
python build_system.py dev
python build_system.py lint
python build_system.py format
```

## Using Cross-Platform Utilities

### Path Operations
```python
from src.path_utils import (
    normalize_path,
    join_paths,
    get_platform,
    is_windows,
    get_executable_extension
)

# Join paths safely
config = join_paths('resources', 'config', 'settings.json')

# Platform detection
if is_windows():
    print("Running on Windows")

# Executable names with platform extension
exe = f'bsnes{get_executable_extension()}'  # bsnes.exe or bsnes
```

### Running Commands
```python
from src.process_runner import run_command, run_executable, run_script

# Run a command
code, stdout, stderr = run_command(['python', '--version'])

# Run an executable
code, stdout, stderr = run_executable('bsnes', ['game.rom'])

# Run a Python script
code, stdout, stderr = run_script('script.py', args=['--flag'])

# Check result
if code == 0:
    print("Success!")
else:
    print(f"Error: {stderr}")
```

## Common Tasks

### Adding a New Script Command
1. Create Python file in `src/scripts/`
2. Use `from src.path_utils import *` for paths
3. Use `from src.process_runner import *` for subprocess
4. Add entry point to `build_system.py`

### Creating Platform-Specific Code
```python
from src.path_utils import is_windows, is_macos, is_linux

if is_windows():
    # Windows-specific
    pass
elif is_macos():
    # macOS-specific
    pass
else:  # Linux
    # Linux-specific
    pass
```

### Running Project Scripts
```python
from src.process_runner import run_script
from src.path_utils import get_snes_ide_scripts, join_paths

script = join_paths(get_snes_ide_scripts(), 'compile-pvsneslib-proj.py')
code, out, err = run_script(script, args=['--project', 'MyGame'])
```

## File Structure
```
SNES-IDE/
├── build_system.py          ← Cross-platform build system
├── Makefile                 ← Make targets (delegates to build_system.py)
├── build.bat                ← Windows convenience script
├── build.sh                 ← Unix convenience script
├── src/
│   ├── snes-ide.py         ← Main application
│   ├── path_utils.py       ← Cross-platform path utilities
│   ├── process_runner.py   ← Subprocess execution utilities
│   └── scripts/            ← Helper scripts
├── CROSS_PLATFORM_GUIDE.md                ← Full documentation
├── CROSS_PLATFORM_IMPROVEMENTS.md         ← What's new
└── .gitattributes          ← Line ending configuration
```

## Troubleshooting

### Import Error: No module named 'src'
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
```

### Build System Not Running
```bash
# Ensure Python is in PATH
python --version

# Try direct path
python build_system.py build
```

### Permission Denied (Unix)
```bash
# Make script executable
chmod +x build.sh

# Then run
./build.sh build
```

### Wrong Path Separators
```python
# Instead of:
path = "resources\\bin\\tool"

# Use:
from src.path_utils import join_paths
path = join_paths('resources', 'bin', 'tool')
```

## Platform-Specific Notes

### Windows
- `.exe` automatically added to executable names
- Batch files for convenience (build.bat)
- Works with both Command Prompt and PowerShell
- Python installation required

### macOS
- ARM64 and Intel Macs supported
- Shell scripts for convenience (build.sh)
- Gatekeeper may need to approve downloaded binaries
- Multiple Python versions may exist (use `python3`)

### Linux
- All major distributions supported
- Shell scripts for convenience (build.sh)
- Package manager integration available
- Multiple Python versions may exist (use `python3`)

## Best Practices

✅ DO
- Use `path_utils` for all path operations
- Use `process_runner` for subprocess calls
- Test on multiple platforms before committing
- Use `build_system.py lint` to catch issues
- Check `CROSS_PLATFORM_GUIDE.md` for detailed info

❌ DON'T
- Hardcode path separators (`\` or `/`)
- Use `shell=True` in subprocess calls
- Assume OS-specific commands exist
- Hardcode `.exe` extensions
- Use `os.system()` for commands

## Resources

- **Full Documentation**: See `CROSS_PLATFORM_GUIDE.md`
- **What's New**: See `CROSS_PLATFORM_IMPROVEMENTS.md`
- **Code Examples**: In utility module docstrings
- **Python pathlib**: https://docs.python.org/3/library/pathlib.html
- **Python subprocess**: https://docs.python.org/3/library/subprocess.html

## Getting Help

1. Check this quick reference
2. Read the full `CROSS_PLATFORM_GUIDE.md`
3. Look at utility module docstrings
4. Check `CONTRIBUTING.md` for contribution guidelines
5. Open an issue on GitHub with platform details

---

Last Updated: 2025-11-20
SNES-IDE Version: 2.0+
