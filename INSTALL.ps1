#!/usr/bin/env pwsh
<#
PowerShell version of INSTALL.bat
creates simple .bat launcher files on the user's desktop and copies the snes-ide executable.
#>

# Ensure we operate from the script directory, like `cd /d "%~dp0` in batch
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptDir

# Check for 'linux' argument (case-insensitive)
$is_linux = $false
if ($args.Count -ge 1 -and $args[0].ToLower() -eq 'linux') { $is_linux = $true }

# Set the path of the executable files (preserve original layout)
$text_editor_exe = Join-Path $scriptDir "libs\notepad++\notepad++.exe"

if ($is_linux) {
    $audio_exe   = Join-Path $scriptDir "tools\audio-tools.bat"
    $gfx_exe     = Join-Path $scriptDir "tools\gfx-tools.bat"
    $other_exe   = Join-Path $scriptDir "tools\externTools.bat"
    $project_exe = Join-Path $scriptDir "tools\create-new-project.bat"
    $compiler_exe= Join-Path $scriptDir "tools\automatizer-batch.bat"
    $snes_ide    = Join-Path $scriptDir "snes-ide.bat"
} else {
    $audio_exe   = Join-Path $scriptDir "tools\audio-tools.exe"
    $gfx_exe     = Join-Path $scriptDir "tools\gfx-tools.exe"
    $other_exe   = Join-Path $scriptDir "tools\externTools.exe"
    $project_exe = Join-Path $scriptDir "tools\create-new-project.exe"
    $compiler_exe= Join-Path $scriptDir "tools\automatizer-batch.bat"
    $snes_ide    = Join-Path $scriptDir "snes-ide.exe"
}

$emulator_exe = Join-Path $scriptDir "libs\bsnes\bsnes.exe"

# Determine desktop shortcut directory, prefer USERPROFILE on Windows, fallback to HOME
$profileRoot = if ($env:USERPROFILE) { $env:USERPROFILE } else { $env:HOME }
$shortcut_dir = Join-Path $profileRoot "Desktop\snes-ide"

if (-not (Test-Path -Path $shortcut_dir)) {
    New-Item -ItemType Directory -Path $shortcut_dir -Force | Out-Null
    Write-Host "installing... $shortcut_dir"
} else {
    Write-Host "installing... $shortcut_dir"
}

# Inline shortcut creation to avoid defining a custom cmdlet with a potentially unapproved verb
$shortcuts = @{
    'text-editor' = $text_editor_exe
    'audio-tools'  = $audio_exe
    'graphic-tools' = $gfx_exe
    'other-tools'   = $other_exe
    'create-new-project' = $project_exe
    'compiler' = $compiler_exe
    'emulator' = $emulator_exe
}

foreach ($name in $shortcuts.Keys) {
    $targetPath = $shortcuts[$name]
    $shortcut_path = Join-Path $shortcut_dir "$name.bat"
    $content = "@echo off`r`n`"$targetPath`""
    Set-Content -Path $shortcut_path -Value $content -Encoding ASCII
}

if ($is_linux) {
    Copy-Item -Path $snes_ide -Destination (Join-Path $shortcut_dir "snes-ide.bat") -Force
} else {
    Copy-Item -Path $snes_ide -Destination (Join-Path $shortcut_dir "snes-ide.exe") -Force
}

Write-Host "SNES-IDE installed successfully! Check the snes-ide folder on your desktop."

# Pause behavior similar to "pause" in batch
Write-Host "Press any key to continue . . ."
# Read a single key (no echo)
try {
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
} catch {
    # Fallback for consoles that don't implement ReadKey
    Read-Host -Prompt 'Press Enter to continue'
}

exit 0
