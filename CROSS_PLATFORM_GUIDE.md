# SNES-IDE Cross-Platform Compatibility Guide

## Overview

SNES-IDE is designed to work seamlessly across Windows, macOS, and Linux. This guide documents the cross-platform architecture, best practices, and utilities available for developers.

## Key Components

### 1. Path Utilities (`src/path_utils.py`)

Provides platform-agnostic path handling. Use these instead of manual path operations:

```python
from path_utils import (
    normalize_path,
    join_paths,
    get_platform,
    is_windows,
    is_macos,
    is_linux,
    to_absolute_path,
    get_executable_extension,
    get_snes_ide_home,
    get_snes_ide_resources
)

# Examples
current_path = get_platform()  # 'windows', 'macos', 'linux'

if is_windows():
    # Windows-specific logic
    pass

# Cross-platform path joining
config_path = join_paths(get_snes_ide_home(), 'config', 'settings.json')

# Automatically adds .exe on Windows
emulator = f'bsnes{get_executable_extension()}'
```

### 2. Process Runner (`src/process_runner.py`)

Handles subprocess execution with cross-platform compatibility:

```python
from process_runner import (
    run_command,
    run_executable,
    run_script,
    ProcessRunner
)

# Run a command
return_code, stdout, stderr = run_command(['python', '--version'])

# Run an executable with automatic .exe handling
return_code, stdout, stderr = run_executable('bsnes', ['game.rom'])

# Run a Python script
return_code, stdout, stderr = run_script('script.py', args=['--flag', 'value'])

# Complex process management
env = ProcessRunner.get_env_with_path_addition('/usr/bin')
return_code, stdout, stderr = ProcessRunner.run_command(
    ['mycommand'],
    env=env,
    capture_output=True,
    timeout=30
)
```

### 3. Build System (`build_system.py`)

Cross-platform Python-based build system replacing Make:

```bash
# Using make (if available)
make build      # Build the application
make clean      # Clean artifacts
make prepare    # Setup development environment
make rebuild    # Clean and rebuild
make dev        # Run in development mode

# Using Python directly (works on all platforms)
python build_system.py build
python build_system.py clean
python build_system.py prepare
python build_system.py rebuild
python build_system.py dev
python build_system.py format
python build_system.py lint
```

### 4. Git Configuration (`.gitattributes`)

Ensures consistent line endings across all platforms:

```
* text=auto eol=lf           # Unix line endings for text files
*.bat text eol=crlf          # Windows batch files use CRLF
*.exe binary                 # Binary files untouched
```

When cloning the repository:
- Files are automatically normalized to platform conventions locally
- Commits always use LF for consistency

## Best Practices

### Path Handling

❌ **DON'T** use hardcoded path separators:
```python
# Bad - breaks on Windows
path = "resources/bin/tool"
cmd = f"cmd /c resources\\bin\\executable.exe"
```

✅ **DO** use cross-platform utilities:
```python
# Good
from path_utils import join_paths, normalize_path
path = join_paths('resources', 'bin', 'tool')
normalized = normalize_path('C:\\Users\\name\\path')
```

### Process Execution

❌ **DON'T** assume OS-specific commands:
```python
# Bad - only works on Unix
subprocess.run("rm -rf build/", shell=True)
subprocess.run("export PATH=/usr/bin:$PATH && mycommand", shell=True)
```

✅ **DO** use cross-platform abstractions:
```python
# Good
from process_runner import run_command, ProcessRunner
import shutil

shutil.rmtree('build/')

env = ProcessRunner.get_env_with_path_addition('/usr/bin')
run_command(['mycommand'], env=env)
```

### Conditional Logic

❌ **DON'T** rely on sys.platform strings:
```python
# Bad - hard to maintain
if sys.platform == 'win32':
    # Windows code
elif sys.platform == 'darwin':
    # macOS code
else:
    # Linux code
```

✅ **DO** use semantic functions:
```python
# Good
from path_utils import is_windows, is_macos, is_linux

if is_windows():
    # Windows-specific
    pass
elif is_macos():
    # macOS-specific
    pass
else:
    # Linux-specific
    pass
```

### File Extensions

❌ **DON'T** hardcode executable names:
```python
# Bad - fails on non-Windows
exe_path = 'bsnes.exe'
```

✅ **DO** use automatic extension handling:
```python
# Good
from path_utils import get_executable_extension
exe_name = f'bsnes{get_executable_extension()}'  # bsnes.exe on Win, bsnes on *nix
```

## Platform-Specific Issues

### Windows

- **Path separators**: Use backslash internally, but use `pathlib` for abstraction
- **Executable extensions**: Add `.exe` automatically
- **Shell commands**: Some commands need `cmd /c` prefix
- **Path length limits**: 260 characters by default (use UNC paths for longer)
- **Line endings**: Configure git to handle CRLF/LF conversion

### macOS

- **Architecture**: May be ARM64 or x86_64
- **Gatekeeper**: Downloaded binaries may need approval
- **Home directory**: Use `Path.home()` not `~`
- **Python installation**: Multiple Python versions may exist
- **App bundles**: Executables may be in `.app/Contents/MacOS/`

### Linux

- **Distribution variations**: Different package managers, paths
- **Permissions**: Executables need execute permissions
- **Shell**: Various shells may be used (bash, zsh, etc.)
- **Package formats**: RPM vs DEB vs source compilation
- **Desktop integration**: Multiple desktop environments

## Troubleshooting

### Import Errors

```python
# If you get "ModuleNotFoundError: No module named 'path_utils'"
# Make sure src/ is in your Python path:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
```

### Process Execution Failures

```python
# Always check return codes and stderr:
return_code, stdout, stderr = run_command(['mycommand'])
if return_code != 0:
    print(f"Error: {stderr}")
    # Handle error appropriately
```

### Path Resolution Issues

```python
# Use to_absolute_path() for relative paths:
from path_utils import to_absolute_path
script = to_absolute_path('scripts/build.py')
# Always resolves to absolute path regardless of CWD
```

## Testing Across Platforms

Use GitHub Actions for automated testing:

```yaml
# .github/workflows/test.yml
name: Cross-Platform Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.10', '3.11']
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      - run: python build_system.py prepare
      - run: python build_system.py lint
      - run: python build_system.py build
```

## Migration Guide

If migrating existing code to use cross-platform utilities:

1. **Replace path operations**:
   ```python
   # Old
   path = os.path.join('a', 'b', 'c')
   
   # New
   from path_utils import join_paths
   path = join_paths('a', 'b', 'c')
   ```

2. **Replace subprocess calls**:
   ```python
   # Old
   subprocess.run('command arg1 arg2', shell=True)
   
   # New
   from process_runner import run_command
   run_command(['command', 'arg1', 'arg2'])
   ```

3. **Replace platform checks**:
   ```python
   # Old
   if sys.platform == 'win32':
   
   # New
   from path_utils import is_windows
   if is_windows():
   ```

## Resources

- **Python pathlib documentation**: https://docs.python.org/3/library/pathlib.html
- **Python subprocess documentation**: https://docs.python.org/3/library/subprocess.html
- **Git attributes documentation**: https://git-scm.com/docs/gitattributes
- **GitHub Actions matrix builds**: https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs

## Contributing

When contributing code:

1. Use the cross-platform utilities provided
2. Test on at least two platforms before submitting PR
3. Use `make format` to ensure consistent code style
4. Use `make lint` to catch issues
5. Document any platform-specific behavior

For more information, see [CONTRIBUTING.md](../CONTRIBUTING.md)
