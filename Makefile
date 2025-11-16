# SNES-IDE Makefile

.PHONY: build

build: 
	@echo "Building SNES-IDE..."
	cd build && python build.py
	@echo "Build complete!"

test: 
	@echo "Running tests..."
	python -m pytest tests/
	@echo "Tests complete!"

clean:
	@echo "Cleaning build artifacts..."
	# Remove everything in build/ except build.py, LICENSE.txt, and requirements.txt
	@find build/ -type f ! -name "build.py" ! -name "LICENSE.txt" ! -name "requirements.txt" -delete
	@find build/ -type d ! -path "build/" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf SNES-IDE-out/ dist/ **/__pycache__ resources/bin/**/dotnet8 resources/bin/**/jdk8 *.spec **/*.specs
	@echo "Clean complete!"