<#
PowerShell-based interactive installer for SNES-IDE (Windows)
- Requests elevation if needed
- Lets user choose install directory
- Detects editors (VS Code, Vim, Notepad++) and configures shortcuts
- Copies distribution from SNES-IDE-out
- Creates Start Menu and Desktop shortcuts
- Optionally adds the install bin to the user's PATH
#>

param()

function Ensure-Elevation {
    $isElevated = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isElevated) {
        Write-Host "Requesting elevation..."
        Start-Process -FilePath pwsh -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        exit 0
    }
}

# Only request elevation if we need to create Start Menu entries in Program Files or write to HKLM
# We'll perform regular user-level install by default

$defaultInstall = "$env:LocalAppData\snes-ide"
$installDir = Read-Host "Install directory (default: $defaultInstall)"
if ([string]::IsNullOrWhiteSpace($installDir)) { $installDir = $defaultInstall }

Write-Host "Installing to: $installDir"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDir = Join-Path $root 'SNES-IDE-out'
if (-not (Test-Path $outDir)) {
    Write-Error "Distribution folder 'SNES-IDE-out' not found. Run the build step first."
    exit 1
}

New-Item -Path $installDir -ItemType Directory -Force | Out-Null

# Copy files
Write-Host "Copying files..."
Copy-Item -Path (Join-Path $outDir '*') -Destination $installDir -Recurse -Force

# Detect editors
$editorChoice = 'none'
if (Get-Command code -ErrorAction SilentlyContinue) { $hasCode = $true } else { $hasCode = $false }
if (Test-Path "$env:ProgramFiles\Notepad++\notepad++.exe") { $hasNotepadPP = $true } else { $hasNotepadPP = $false }

Write-Host "Choose editor integration:"
Write-Host "  1) Visual Studio Code" -ForegroundColor Cyan
Write-Host "  2) Vim (if installed)" -ForegroundColor Cyan
Write-Host "  3) Notepad++ (Windows only)" -ForegroundColor Cyan
Write-Host "  4) None / configure later" -ForegroundColor Cyan
$choice = Read-Host "Enter 1,2,3 or 4 (default 1)"
if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '1' }

switch ($choice) {
    '1' { $editorChoice = 'vscode' }
    '2' { $editorChoice = 'vim' }
    '3' { $editorChoice = 'notepadpp' }
    default { $editorChoice = 'none' }
}

# Create bin helpers
$binDir = Join-Path $installDir 'bin'
New-Item -Path $binDir -ItemType Directory -Force | Out-Null

if ($editorChoice -eq 'vscode') {
    $script = @"
@echo off
if exist "%ProgramFiles%\Microsoft VS Code\Code.exe" (
    start "" "%ProgramFiles%\Microsoft VS Code\Code.exe" "%~1"
) else if exist "%LocalAppData%\Programs\Microsoft VS Code\Code.exe" (
    start "" "%LocalAppData%\Programs\Microsoft VS Code\Code.exe" "%~1"
) else (
    echo VS Code not found in expected locations. Please ensure 'code' is in PATH.
)
"@
    $scriptPath = Join-Path $binDir 'snes-ide-open-editor.bat'
    $script | Out-File -FilePath $scriptPath -Encoding ASCII -Force
}

if ($editorChoice -eq 'notepadpp') {
    $script = '@echo off`n"%ProgramFiles%\Notepad++\notepad++.exe" "%~1"'
    $script | Out-File -FilePath (Join-Path $binDir 'snes-ide-open-editor.bat') -Encoding ASCII -Force
}

# Create Start Menu and Desktop shortcuts
$WshShell = New-Object -ComObject WScript.Shell
$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\SNES-IDE'
New-Item -Path $startMenu -ItemType Directory -Force | Out-Null

$exeTarget = Join-Path $installDir 'snes-ide.bat'
if (-not (Test-Path $exeTarget)) { $exeTarget = Join-Path $installDir 'snes-ide.exe' }
if (-not (Test-Path $exeTarget)) { $exeTarget = Join-Path $installDir 'snes-ide.bat' }

$lnk = $WshShell.CreateShortcut((Join-Path $startMenu 'SNES-IDE.lnk'))
$lnk.TargetPath = $exeTarget
$lnk.WorkingDirectory = $installDir
$lnk.Save()

# Desktop shortcut
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk2 = $WshShell.CreateShortcut((Join-Path $desktop 'SNES-IDE.lnk'))
$lnk2.TargetPath = $exeTarget
$lnk2.WorkingDirectory = $installDir
$lnk2.Save()

# Optionally add to PATH
$addPath = Read-Host "Add $binDir to your user PATH? (y/N)"
if ($addPath -match '^[Yy]') {
    $current = [Environment]::GetEnvironmentVariable('PATH', 'User')
    if (-not ($current -like "*${binDir}*")) {
        [Environment]::SetEnvironmentVariable('PATH', "$current;$binDir", 'User')
        Write-Host "Added $binDir to your user PATH"
    }
}

Write-Host "Installation complete. You can launch SNES-IDE from Start Menu or Desktop."
