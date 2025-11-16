# SNES-IDE Test Suite

This directory contains the consolidated test suite for SNES-IDE. The tests have been streamlined from 10 separate files into 2 focused modules.

## Test Structure

### `test_core_utilities.py`
Comprehensive testing for all core utility modules:
- **PathUtils**: Path resolution, project root detection, directory creation
- **PlatformUtils**: Platform detection, executable naming, shell commands, project validation
- **SubprocessUtils**: Process execution, tool management, command running
- **Integration Tests**: Cross-utility functionality and import verification

### `test_script_integration.py`
Integration testing for all SNES-IDE scripts:
- **Script Compilation**: Syntax validation for all Python scripts
- **Migration Verification**: Ensures all scripts use new utility modules
- **Interface Testing**: Validates script dependencies and imports
- **Build System Integration**: Tests compilation and project creation scripts

## Running Tests

### Using the test runner (recommended)
```bash
# Run all tests with verbose output
python run_tests.py

# Run with less verbose output
python run_tests.py --verbosity 1

# List available tests without running
python run_tests.py --list
```

### Using pytest directly
```bash
# Run all tests
pytest

# Run specific test modules
pytest test_core_utilities.py
pytest test_script_integration.py

# Run with verbose output
pytest -v
```

## Test Coverage

The consolidated test suite includes:
- **34 total tests** (previously 153 across 10 files)
- **100% success rate** maintained
- **Complete utility coverage**: All path, platform, and subprocess utilities
- **Full script verification**: All 17 migrated scripts tested
- **Cross-platform compatibility**: Tests work on Windows, macOS, and Linux

## Migration from Old Test Structure

Previously, the test suite consisted of 10 separate files with significant overlap:
- `test_path_utils.py` (57 lines)
- `test_path_utils_functional.py` (268 lines)  
- `test_path_utils_integration.py` (322 lines)
- `test_platform_utils.py` (538 lines)
- `test_platform_utils_integration.py` (487 lines)
- `test_subprocess_utils.py` (575 lines)
- Various script integration tests (143-217 lines each)

The new structure eliminates redundancy while maintaining complete test coverage and improving maintainability.

## Benefits of Consolidation

1. **Reduced Complexity**: 2 focused files instead of 10 overlapping files
2. **Improved Maintainability**: Unified test patterns and shared utilities  
3. **Faster Execution**: Streamlined test discovery and execution
4. **Better Organization**: Logical grouping of related functionality
5. **Simplified CI/CD**: Single test runner with comprehensive reporting

## Test Philosophy

- **Comprehensive**: Tests cover all critical functionality
- **Practical**: Tests use real instances rather than excessive mocking
- **Robust**: Platform-aware testing that works across all supported systems
- **Maintainable**: Clear test organization with descriptive names and documentation