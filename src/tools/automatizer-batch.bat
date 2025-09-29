@echo off
set /p userDirectory=Enter the desired directory (e.g., C:\Users\anonymous\Desktop\game_folder):
set /p MemoryMap=HIROM or LOROM (if you don't know, choose LOROM)?:
set /p Speed=Speed: use all SNES speed (FAST) or use the recommended one (SLOW)? Write FAST or SLOW:

:: Set the path to the directory above "tools"
set "toolsDirectory=%~dp0.."

:: Set the full path to automatizer.exe
set "automatizerPath=%toolsDirectory%\libs\pvsneslib\devkitsnes\automatizer.exe"

:: Set the path to Python automatizer script
set "pyScript=%toolsDirectory%\libs\pvsneslib\devkitsnes\automatizer.py"

:: Check if automatizer.exe exists
if exist "%automatizerPath%" (
    :: Change to the user-specified directory
    cd /d "%userDirectory%"

    :: Execute automatizer.exe with the userDirectory as an argument
    "%automatizerPath%" "%userDirectory%" "%MemoryMap%" "%Speed%"
    echo Execution successful!

) else (
    :: Attempt Python fallback if automatizer.exe not found
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

    echo Error: automatizer.exe not found and no Python fallback available.
)

:: Pause at the end of the script
pause
