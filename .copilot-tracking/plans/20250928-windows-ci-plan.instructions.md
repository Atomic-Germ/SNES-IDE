---
applyTo: '.copilot-tracking/changes/20250928-windows-ci-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: Windows CI for SNES-IDE

## Overview
Add a comprehensive Windows CI build & test pipeline that produces `SNES-IDE-out`, packages Python scripts into Windows executables, runs the installer, and executes the test suite on `windows-latest` GitHub Actions runners.

## Objectives
- Produce an automated build job that outputs `SNES-IDE-out` as an artifact
- Add a test job that runs `SNES-IDE-out/INSTALL.bat` and executes `tests/test.py`
- Cache Python dependencies and speed up repeated runs

## Research Summary
### Project Files
- `build/build.bat` - Windows build wrapper (see details file lines 1-20)
- `build/build.py` - build orchestration producing `SNES-IDE-out` (see details file lines 1-40)

### External References
- #file:../research/20250928-windows-ci-research.md - Full research (see research file for PyInstaller and GitHub Actions docs summary)

## Implementation Checklist

### [ ] Phase 1: Preparation
- [ ] Task 1.1: Confirm build entrypoint and artifacts
  - Details: .copilot-tracking/details/20250928-windows-ci-details.md (Lines 1-26)
- [ ] Task 1.2: Document runner & dependency requirements
  - Details: .copilot-tracking/details/20250928-windows-ci-details.md (Lines 27-45)

### [ ] Phase 2: CI Implementation
- [ ] Task 2.1: Implement `build-windows` job
  - Details: .copilot-tracking/details/20250928-windows-ci-details.md (Lines 46-92)
- [ ] Task 2.2: Implement `test` job that depends on build
  - Details: .copilot-tracking/details/20250928-windows-ci-details.md (Lines 93-156)

### [ ] Phase 3: Optimization & Hardening
- [ ] Task 3.1: Add caching (pip cache)
  - Details: .copilot-tracking/details/20250928-windows-ci-details.md (Lines 157-194)
- [ ] Task 3.2: Add failure diagnostics and artifact retention policies
  - Details: .copilot-tracking/details/20250928-windows-ci-details.md (Lines 195-240)

## Dependencies
- `actions/checkout@v4`
- `actions/setup-python@v4`
- `actions/cache@v4`
- `actions/upload-artifact@v4` and `actions/download-artifact@v5`
- PyInstaller (installed via pip during build)

## Success Criteria
- Build job produces `SNES-IDE-out` artifact
- Test job executes `INSTALL.bat` and `tests/test.py` exiting with code 0
- Cache hits on `actions/cache` for pip between runs
- Build and test logs uploaded for troubleshooting
