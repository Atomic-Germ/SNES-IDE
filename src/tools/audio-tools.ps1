#!/usr/bin/env pwsh
<#
Lightweight PowerShell launcher for audio-tools.py — forwards arguments to Python and returns the same exit code.
#>

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptDir

$py = Join-Path $scriptDir 'audio-tools.py'
if (-not (Test-Path -Path $py)) {
    Write-Error "Missing script: $py"
    exit 1
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error 'Python not found on PATH. Install Python or add it to PATH.'
    exit 1
}

# Run Python with unbuffered output to match CI expectations
& python -u $py @args
exit $LASTEXITCODE
