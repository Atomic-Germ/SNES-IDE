#!/usr/bin/env pwsh
<#
PowerShell port of build.bat
Checks for Python and runs build.py with forwarded arguments.
#>

# Ensure we operate from the location of this script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptDir

# Check if python is available
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "Python is not installed."
    exit 1
}

# If build.py exists, run it with passed through args
if (Test-Path -Path "build.py") {
    & python "./build.py" @args
} else {
    Write-Host "build.py not found."
    exit 1
}
