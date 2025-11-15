# SNES-IDE Makefile

.PHONY: clean build

build: clean
	@echo "Building SNES-IDE..."
	python build/build.py
	@echo "Build complete!"

clean:
	@echo "Cleaning build artifacts..."
	# Remove everything in build/ except build.py, LICENSE.txt, and requirements.txt
	@find build/ -type f ! -name "build.py" ! -name "LICENSE.txt" ! -name "requirements.txt" -delete
	@find build/ -type d ! -path "build/" -exec rm -rf {} + 2>/dev/null || true
	# Remove SNES-IDE-out and dist directories
	@rm -rf SNES-IDE-out/ dist/
	# Remove .spec files from root
	@rm -f *.spec
	@echo "Clean complete!"