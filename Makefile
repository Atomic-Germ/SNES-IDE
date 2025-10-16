.PHONY: clean

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf SNES-IDE-out
	@rm -rf build/snes-ide
	@rm -rf dist
	@rm -rf *.spec
	@echo "Clean complete."