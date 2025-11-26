# SNES Installer

A cross-platform application that downloads, builds, and configures tools for SNES programming IDE setup.

## Installation

1. Clone the repository.
2. Create a virtual environment: `python -m venv .venv`
3. Activate: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`

## Usage

Run the installer: `python -m snes_installer`

This will download, build, and install the tools, then set up IDE integrations for VS Code, Vim/NeoVim, and Notepad++ (on Windows).

## Tools Configured

- **ca65**: 6502 assembler from the cc65 project
- **asar**: SNES assembler
- **xkas**: SNES assembler

## IDE Integrations

The installer automatically configures syntax highlighting for:
- **VS Code**: Installs 6502 assembly and C++ tools extensions
- **Vim/NeoVim**: Adds assembly syntax for .asm and .s files
- **Notepad++** (Windows): Creates user-defined language for SNES assembly

## Development

Run tests: `pytest`