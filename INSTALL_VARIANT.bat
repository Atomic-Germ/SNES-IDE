@echo off
<<<<<<< HEAD

=======
>>>>>>> 8f85e6b (Add PyInstaller spec, improve build utils, and update CI to use spec for Windows packaging)
REM Interactive installer variant for Windows (legacy batch)
REM Prefer PowerShell installer if available for a friendlier UI.
SETLOCAL ENABLEDELAYEDEXPANSION

:: If PowerShell exists, delegate to INSTALL_VARIANT.ps1 for a richer experience.
where powershell.exe >nul 2>&1
if %ERRORLEVEL%==0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL_VARIANT.ps1"
    exit /b %ERRORLEVEL%
)

:: Default install directory on Windows
set "DEFAULT_TARGET=%USERPROFILE%\AppData\Local\snes-ide"
set /p TARGET_DIR=Install directory (default: %DEFAULT_TARGET%): 
if "%TARGET_DIR%"=="" set "TARGET_DIR=%DEFAULT_TARGET%"

necho Copying distribution to %TARGET_DIR%
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
xcopy /E /I /Y "%~dp0SNES-IDE-out\*" "%TARGET_DIR%\" >nul

necho.
echo Choose an editor to configure for SNES-IDE integration:
echo   1) Visual Studio Code (code)
echo   2) Vim (terminal)
echo   3) Notepad++ (Windows only)
echo   4) None / I'll configure manually
set /p editor_choice=Enter 1,2,3 or 4 (default 1): 
if "%editor_choice%"=="" set "editor_choice=1"

nif "%editor_choice%"=="1" set "EDITOR_CHOICE=code"
if "%editor_choice%"=="2" set "EDITOR_CHOICE=vim"
if "%editor_choice%"=="3" set "EDITOR_CHOICE=notepadpp"
if "%editor_choice%"=="4" set "EDITOR_CHOICE=none"

necho Selected editor: %EDITOR_CHOICE%

n:: Optionally copy emulator binaries and cores from repo if present
set /p copy_emu=Copy emulator binaries and libretro cores from repo if present? (y/n, default y): 
if "%copy_emu%"=="" set "copy_emu=y"
if /I "%copy_emu%"=="y" (
    if exist "%~dp0libs\bsnes" (
        xcopy /E /I /Y "%~dp0libs\bsnes\*" "%TARGET_DIR%\libs\bsnes\" >nul
    )
    if exist "%~dp0libs\libretro" (
        xcopy /E /I /Y "%~dp0libs\libretro\*" "%TARGET_DIR%\libs\libretro\" >nul
    )
)

n:: Create simple desktop shortcuts (batch files) to launch snes-ide and editor helper
necho Creating desktop shortcuts...
set "DESKTOP_DIR=%USERPROFILE%\Desktop\snes-ide"
if not exist "%DESKTOP_DIR%" mkdir "%DESKTOP_DIR%"

n:: snes-ide launcher shortcut (batch)
copy "%~dp0snes-ide.bat" "%DESKTOP_DIR%\snes-ide.bat" >nul 2>&1 || (
    echo @echo off > "%DESKTOP_DIR%\snes-ide.bat"
    echo python "%TARGET_DIR%\src\snes-ide.py" %%* >> "%DESKTOP_DIR%\snes-ide.bat"
)

n:: Editor helper shortcut for Windows users
nif "%EDITOR_CHOICE%"=="code" (
    echo @echo off > "%DESKTOP_DIR%\open-editor.bat"
    echo code "%TARGET_DIR%" %%* >> "%DESKTOP_DIR%\open-editor.bat"
) else if "%EDITOR_CHOICE%"=="notepadpp" (
    echo @echo off > "%DESKTOP_DIR%\open-editor.bat"
    echo "%ProgramFiles%\Notepad++\notepad++.exe" "%TARGET_DIR%" %%* >> "%DESKTOP_DIR%\open-editor.bat"
) else (
    echo @echo off > "%DESKTOP_DIR%\open-editor.bat"
    echo start "" "%TARGET_DIR%" >> "%DESKTOP_DIR%\open-editor.bat"
)

necho Installation complete.
echo - Install directory: %TARGET_DIR%
echo - Editor: %EDITOR_CHOICE%
echo - Shortcuts installed at %DESKTOP_DIR%
pause
exit /b 0
