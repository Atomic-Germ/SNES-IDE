#!/usr/bin/env pwsh
<#
PowerShell port of automatizer-batch.bat
Prompts the user for inputs and executes automatizer.exe with the same arguments.
#>

# Work from the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Interactive prompts (explicit -Prompt usage)
$userDirectory = Read-Host -Prompt 'Enter desired directory (e.g. C:\\Users\\anonymous\\Desktop\\game_folder)'
$MemoryMap = Read-Host -Prompt 'Memory map (HIROM or LOROM)'
$Speed = Read-Host -Prompt 'Speed (FAST or SLOW)'

# Determine toolsDirectory as the parent of the script directory
$toolsDirectory = (Resolve-Path (Join-Path -Path $scriptDir -ChildPath '..')).ProviderPath

# Build the path to automatizer.exe using Path.Combine to avoid escaping issues
$automatizerPath = [System.IO.Path]::Combine($toolsDirectory, 'libs', 'pvsneslib', 'devkitsnes', 'automatizer.exe')
$pyScript = [System.IO.Path]::Combine($toolsDirectory, 'libs', 'pvsneslib', 'devkitsnes', 'automatizer.py')


if (Test-Path -Path $automatizerPath) {
    # Change to the user-specified directory
    Set-Location -Path $userDirectory

    # Execute automatizer.exe with the same arguments; use Start-Process for deterministic exit codes
    $proc = Start-Process -FilePath $automatizerPath -ArgumentList @($userDirectory, $MemoryMap, $Speed) -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -eq 0) {
        Write-Host 'Execution successful!'
    } else {
        Write-Host "automatizer exited with code $($proc.ExitCode)"
        exit $proc.ExitCode
    }
} elseif (Test-Path -Path $pyScript) {
    # Try to find python or python3
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if ($pythonCmd) {
        Set-Location -Path $userDirectory
        $proc = Start-Process -FilePath $pythonCmd.Source -ArgumentList @($pyScript, $userDirectory, $MemoryMap, $Speed) -NoNewWindow -Wait -PassThru
        if ($proc.ExitCode -eq 0) {
            Write-Host 'Execution successful!'
        } else {
            Write-Host "automatizer (python) exited with code $($proc.ExitCode)"
            exit $proc.ExitCode
        }
    } else {
        Write-Host 'Error: Python not found to run automatizer.py'
        exit 1
    }
} else {
    Write-Host 'Error: automatizer.exe not found and no Python fallback available.'
}

# Pause at the end similar to 'pause' in batch
Read-Host -Prompt 'Press Enter to continue'

exit 0
