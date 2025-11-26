# SNES Installer

A cross-platform application that downloads, builds, and configures tools for SNES programming IDE setup.

## Installation

1. Clone the repository.
2. Create a virtual environment: `python -m venv .venv`
3. Activate: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`

## Usage

Run the installer: `python -m snes_installer`

## Tools Configured

- **ca65**: 6502 assembler from the cc65 project
- **asar**: SNES assembler

## Development

Run tests: `pytest`