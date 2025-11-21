@echo off
REM SNES-IDE Build System for Windows
REM This batch file provides a convenient interface to the Python build system
REM Usage: build.bat [command]

setlocal enabledelayedexpansion

if "%1"=="" (
    python build_system.py build
) else (
    python build_system.py %*
)

if errorlevel 1 (
    echo.
    echo Error: Build command failed
    exit /b 1
)

exit /b 0
