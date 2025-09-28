#!/usr/bin/env pwsh
<#
PowerShell port of automatizer-batch.bat
Prompts the user for inputs and executes automatizer.exe with the same arguments.
#>

# Work from the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Interactive prompts
$userDirectory = Read-Host "Enter desired directory (e.g. C:\\Users\\anonymous\\Desktop\\game_folder)"
$MemoryMap = Read-Host "HIROM or LOROM? Choose LOROM if unsure"
$Speed = Read-Host "Speed (FAST or SLOW):"

# Determine toolsDirectory as the parent of the script directory
$toolsDirectory = Join-Path -Path $scriptDir -ChildPath '..'

# Set the full path to automatizer.exe
$automatizerPath = Join-Path -Path $toolsDirectory -ChildPath 'libs\\pvsneslib\\devkitsnes\\automatizer.exe'

if (Test-Path -Path $automatizerPath) {
    # Change to the user-specified directory
    Set-Location -Path $userDirectory

    # Execute automatizer.exe with the same arguments
    & "$automatizerPath" "$userDirectory" "$MemoryMap" "$Speed"
    Write-Host "Execution successful!"
} else {
    Write-Host "Error: automatizer.exe not found."
}

# Pause at the end similar to 'pause' in batch
Write-Host "Press any key to continue . . ."
try {
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
} catch {
    Read-Host -Prompt "Press Enter to continue"
}

exit 0
