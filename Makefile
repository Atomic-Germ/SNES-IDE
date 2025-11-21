# SNES-IDE Makefile
# This Makefile provides a cross-platform interface to the Python build system
# For Windows users without make, use: python build_system.py [command]

.PHONY: clean prepare build rebuild dev format lint help

help:
	@echo "SNES-IDE Build System"
	@echo "====================="
	@echo ""
	@echo "Available targets:"
	@echo "  make build    - Build SNES-IDE (runs clean first)"
	@echo "  make clean    - Clean build artifacts"
	@echo "  make prepare  - Setup development environment"
	@echo "  make rebuild  - Clean and rebuild"
	@echo "  make dev      - Run SNES-IDE in development mode"
	@echo "  make format   - Format code (requires black, isort)"
	@echo "  make lint     - Run linting checks (requires flake8)"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "Note: On Windows without make, use: python build_system.py [command]"
	@echo ""

build: clean
	@echo "Building SNES-IDE..."
	python build_system.py build

clean:
	@echo "Cleaning build artifacts..."
	python build_system.py clean

prepare:
	@echo "Preparing development environment..."
	python build_system.py prepare

rebuild:
	@echo "Rebuilding SNES-IDE..."
	python build_system.py rebuild

dev:
	@echo "Running SNES-IDE in development mode..."
	python build_system.py dev

format:
	@echo "Formatting code..."
	python build_system.py format

lint:
	@echo "Running linting checks..."
	python build_system.py lint
