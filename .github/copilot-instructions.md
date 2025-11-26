---
applyTo: '*'
description: A comprehensive set of safety and consistency rules for Python development, including best practices for virtual environments, coding standards, dependency management, and testing.
---
Always check for and create/activate a virtual environment before installing new Python packages or working with Python projects. This helps to manage dependencies and avoid conflicts between different projects, as well as avoid polluting the global Python environment. Use the following commands:
```bash
# Create a virtual environment
python -m venv .venv
# Activate the virtual environment
source .venv/bin/activate
```

## System Safety Rules

### 1. **Never Run Code from Untrusted Sources**
- Always review third-party code before executing it
- Verify libraries from PyPI by checking the package name, author, and download statistics
- Avoid executing code with `eval()`, `exec()`, or `__import__()` unless absolutely necessary
- Use static analysis tools like `bandit` to scan for security vulnerabilities

### 2. **File System Safety**
- Use absolute paths for critical operations
- Validate and sanitize all file paths to prevent directory traversal attacks
- Never use `os.system()` or `subprocess` with unsanitized user input
- Set appropriate file permissions (restrict to `0o644` for files, `0o755` for directories)
- Avoid operations in system directories (e.g., `/`, `/bin`, `/etc`, `/usr`)

### 3. **Network Safety**
- Validate all URLs and network addresses before connection attempts
- Use secure protocols (HTTPS, SSH) instead of insecure ones (HTTP, FTP)
- Set reasonable timeouts for network operations to prevent hanging
- Avoid exposing local services to the external network unnecessarily

### 4. **Resource Management**
- Always use context managers (`with` statements) for file and network operations
- Close database connections and release resources properly
- Monitor memory usage, especially when processing large files
- Use generators and iterators for memory-efficient processing of large datasets

### 5. **Dependency Safety**
- Pin versions in `requirements.txt` or `pyproject.toml`: `package==1.2.3` not `package>=1.2.3`
- Regularly update dependencies using tools like `pip-audit` or `safety`
- Review changelog and security advisories before updating packages
- Use tools like `pip-compile` to lock transitive dependencies

## Consistency Rules

### 1. **Code Style and Formatting**
- Follow **PEP 8** style guidelines consistently
- Use `black` for automatic code formatting (line length: 88 characters)
- Use `isort` for consistent import sorting (alphabetical, grouped by type)
- Use `flake8` or `ruff` for linting

### 2. **Project Structure**
- Use a consistent project layout:
```
project-name/
├── src/                    # Source code
│   └── package_name/
├── tests/                  # Test files
├── docs/                   # Documentation
├── pyproject.toml          # Project configuration
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
└── .venv/                  # Virtual environment
```

### 3. **Naming Conventions**
- Use `snake_case` for functions and variables: `def my_function()`
- Use `PascalCase` for classes: `class MyClass:`
- Use `UPPER_CASE` for constants: `MAX_RETRIES = 5`
- Use descriptive names: `user_data` not `ud`

### 4. **Type Hints**
- Add type hints for all function parameters and return values
- Use the `typing` module for complex types
- Configure static type checking with `mypy` or `pyright`

### 5. **Error Handling**
- Use specific exception types, never bare `except:`
- Log errors with appropriate severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Provide meaningful error messages for users
- Include exception chaining for better debugging: `raise MyError("Failed") from exc`

### 6. **Testing**
- Write unit tests for all functions (aim for >80% coverage)
- Use `pytest` as the testing framework
- Follow the `AAA` pattern: Arrange, Act, Assert
- Name test files as `test_*.py` and test functions as `test_*`

### 7. **Documentation**
- Write docstrings for all public functions and classes (follow PEP 257)
- Include `Args`, `Returns`, and `Raises` sections in docstrings
- Maintain a `README.md` with setup instructions and usage examples
- Keep `CHANGELOG.md` updated with version history

### 8. **Version Control**
- Use meaningful commit messages (conventional commits format)
- Add `.gitignore` for Python projects (use github/gitignore template)
- Never commit secrets, keys, or credentials to version control
- Use environment variables or configuration files (e.g., `.env` with `.gitignore`)

### 9. **Logging**
- Use the `logging` module, never `print()` for production code
- Configure logging at application startup
- Use appropriate log levels and provide context in log messages
- Avoid logging sensitive information (passwords, API keys)

## Quick Setup Commands

```bash
# Setup development environment
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install development tools
pip install black flake8 isort mypy bandit safety pytest

# Run safety checks
bandit -r src/
safety check --json
pytest tests/
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```
