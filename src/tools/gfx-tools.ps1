#!/usr/bin/env pwsh
<#
PowerShell launcher for gfx-tools.py — forwards args to Python and preserves exit code.
#>

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptDir

$py = Join-Path $scriptDir 'gfx-tools.py'
if (-not (Test-Path -Path $py)) {
    Write-Error "Missing script: $py"
    exit 1
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error 'Python not found on PATH. Install Python or add it to PATH.'
    exit 1
}

& python -u $py @args
exit $LASTEXITCODE
