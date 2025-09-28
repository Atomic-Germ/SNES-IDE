# Windows CI Plan (summary)

Goal: Implement a robust Windows CI pipeline that builds `SNES-IDE` on `windows-latest`, packages Python tools to `.exe` (PyInstaller), uploads `SNES-IDE-out` artifacts, runs the installer, and executes tests.

High-level flow:
- Build job (`build-windows`): checkout, setup Python, install PyInstaller, run `build\\build.bat`, upload `SNES-IDE-out` as artifact.
- Test job (`test`): depends on build, download artifact, run `SNES-IDE-out\\INSTALL.bat`, run `python -u tests/test.py`, upload logs.

See `.copilot-tracking/plans/20250928-windows-ci-plan.instructions.md` and `.copilot-tracking/details/20250928-windows-ci-details.md` for full checklist and details.
