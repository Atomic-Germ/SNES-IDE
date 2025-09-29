@echo off
set /p userDirectory=Enter the desired directory (e.g., C:\Users\anonymous\Desktop\game_folder):
set /p MemoryMap=HIROM or LOROM (if you don't know, choose LOROM)?:
set /p Speed=Speed: use all SNES speed (FAST) or use the recommended one (SLOW)? Write FAST or SLOW:

:: Set the path to the directory above "tools"
set "toolsDirectory=%~dp0.."

:: Candidate paths for automatizer executable/script
set "automatizerPath=%toolsDirectory%\libs\pvsneslib\devkitsnes\automatizer.exe"
set "binAutomatizerPath=%toolsDirectory%\libs\pvsneslib\devkitsnes\bin\automatizer.exe"
set "pyScript=%toolsDirectory%\libs\pvsneslib\devkitsnes\automatizer.py"

:: Helper to run the python fallback with the available python launcher
:run_python_fallback
where python >nul 2>nul
if %errorlevel%==0 (
    if exist "%pyScript%" (
        cd /d "%userDirectory%"
        python "%pyScript%" "%userDirectory%" "%MemoryMap%" "%Speed%"
        echo Execution successful!
        goto :eof
    )
)
where py >nul 2>nul
if %errorlevel%==0 (
    if exist "%pyScript%" (
        cd /d "%userDirectory%"
        py "%pyScript%" "%userDirectory%" "%MemoryMap%" "%Speed%"
        echo Execution successful!
        goto :eof
    )
)
:: No python fallback found
echo Error: automatizer.exe not found and no Python fallback available.
pause
goto :eof

:: Try explicit automatizer.exe locations first
if exist "%automatizerPath%" (
    cd /d "%userDirectory%"
    "%automatizerPath%" "%userDirectory%" "%MemoryMap%" "%Speed%"
    echo Execution successful!
    goto :eof
)

if exist "%binAutomatizerPath%" (
    cd /d "%userDirectory%"
    "%binAutomatizerPath%" "%userDirectory%" "%MemoryMap%" "%Speed%"
    echo Execution successful!
    goto :eof
)

:: If an 'automatizer' binary/executable is on PATH, try to execute it
where automatizer >nul 2>nul
if %errorlevel%==0 (
    cd /d "%userDirectory%"
    automatizer "%userDirectory%" "%MemoryMap%" "%Speed%"
    echo Execution successful!
    goto :eof
)

:: Fall back to Python-based script if available
if exist "%pyScript%" (
    call :run_python_fallback
) else (
    echo Error: automatizer not found in expected locations.
    pause
)

:: Pause at the end of the script
pause
