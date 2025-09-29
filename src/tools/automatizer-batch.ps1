#!/usr/bin/env pwsh
<#
PowerShell port of automatizer-batch.bat
Prompts the user for inputs and executes automatizer.exe with the same arguments.
#>

# Work from the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Interactive prompts
$userDirectory = Read-Host -Prompt 'Enter desired directory (e.g. C:\\Users\\anonymous\\Desktop\\game_folder)'
$MemoryMap = Read-Host -Prompt 'Memory map (HIROM or LOROM)'
$Speed = Read-Host -Prompt 'Speed (FAST or SLOW)'

# Determine toolsDirectory as the parent of the script directory
$toolsDirectory = (Resolve-Path (Join-Path -Path $scriptDir -ChildPath '..')).ProviderPath

# Candidate paths
$automatizerPath = [System.IO.Path]::Combine($toolsDirectory, 'libs', 'pvsneslib', 'devkitsnes', 'automatizer.exe')
$binAutomatizerPath = [System.IO.Path]::Combine($toolsDirectory, 'libs', 'pvsneslib', 'devkitsnes', 'bin', 'automatizer.exe')
$pyScript = [System.IO.Path]::Combine($toolsDirectory, 'libs', 'pvsneslib', 'devkitsnes', 'automatizer.py')

function Run-PythonFallback {
    # Try python then python3 then py
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $cmd) { $cmd = Get-Command py -ErrorAction SilentlyContinue }

    if ($cmd -and (Test-Path -Path $pyScript)) {
        Set-Location -Path $userDirectory
        $proc = Start-Process -FilePath $cmd.Source -ArgumentList @($pyScript, $userDirectory, $MemoryMap, $Speed) -NoNewWindow -Wait -PassThru
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
}

# Prefer explicit automatizer.exe locations
if (Test-Path -Path $automatizerPath) {
    Set-Location -Path $userDirectory
    $proc = Start-Process -FilePath $automatizerPath -ArgumentList @($userDirectory, $MemoryMap, $Speed) -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -eq 0) { Write-Host 'Execution successful!' } else { Write-Host "automatizer exited with code $($proc.ExitCode)"; exit $proc.ExitCode }
    exit 0
}

if (Test-Path -Path $binAutomatizerPath) {
    Set-Location -Path $userDirectory
    $proc = Start-Process -FilePath $binAutomatizerPath -ArgumentList @($userDirectory, $MemoryMap, $Speed) -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -eq 0) { Write-Host 'Execution successful!' } else { Write-Host "automatizer exited with code $($proc.ExitCode)"; exit $proc.ExitCode }
    exit 0
}

# If an 'automatizer' binary is available on PATH, use it
$automatizerCmd = Get-Command automatizer -ErrorAction SilentlyContinue
if ($automatizerCmd) {
    Set-Location -Path $userDirectory
    $proc = Start-Process -FilePath $automatizerCmd.Source -ArgumentList @($userDirectory, $MemoryMap, $Speed) -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -eq 0) { Write-Host 'Execution successful!' } else { Write-Host "automatizer exited with code $($proc.ExitCode)"; exit $proc.ExitCode }
    exit 0
}

# Fall back to python script
if (Test-Path -Path $pyScript) {
    Run-PythonFallback
} else {
    Write-Host 'Error: automatizer.exe not found and no Python fallback available.'
    exit 1
}

# Pause at the end similar to 'pause' in batch
Read-Host -Prompt 'Press Enter to continue'

exit 0
