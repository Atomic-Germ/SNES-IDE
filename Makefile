.PHONY: clean build

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf SNES-IDE-out
	@rm -rf build/snes-ide
	@rm -rf dist
	@rm -rf *.spec
	@rm -rf libs/pvsneslib
	@rm -rf libs/pvsneslib-tools
	@rm -rf libs/include/devkitsnes
	@rm -rf libs/include
	@rm -rf libs/font
	@rm -rf temp_download
	@echo "Clean complete."

build:
	@echo "Building SNES-IDE..."
	@build/build.py