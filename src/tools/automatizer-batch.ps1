#!/usr/bin/env pwsh
<#
PowerShell port of automatizer-batch.bat
Prompts the user for inputs and executes automatizer.exe with the same arguments.
#>

# Work from the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Interactive prompts (simplified)
$userDirectory = Read-Host 'Enter desired directory'
$MemoryMap = Read-Host 'Memory map: HIROM or LOROM'
$Speed = Read-Host 'Speed: FAST or SLOW'

# Determine toolsDirectory as the parent of the script directory
$toolsDirectory = (Join-Path -Path $scriptDir -ChildPath '..' | Resolve-Path).ProviderPath

# Set the full path to automatizer.exe
$automatizerPath = Join-Path -Path $toolsDirectory -ChildPath 'libs\\pvsneslib\\devkitsnes\\automatizer.exe'

if (Test-Path -Path $automatizerPath) {
    # Change to the user-specified directory
    Set-Location -Path $userDirectory

    # Execute automatizer.exe with the same arguments using Start-Process
    $proc = Start-Process -FilePath $automatizerPath -ArgumentList @($userDirectory, $MemoryMap, $Speed) -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -eq 0) {
        Write-Host 'Execution successful!'
    } else {
        Write-Host "automatizer exited with code $($proc.ExitCode)"
        exit $proc.ExitCode
    }
} else {
    Write-Host 'Error: automatizer.exe not found.'
}

# Pause at the end similar to 'pause' in batch
Read-Host -Prompt 'Press Enter to continue'

exit 0
