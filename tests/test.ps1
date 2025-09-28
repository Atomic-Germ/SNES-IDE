#!/usr/bin/env pwsh
<#
PowerShell wrapper to run the Python test harness at tests/test.py.
This provides a ps1 equivalent to (the sometimes-missing) test.bat so callers
can prefer PowerShell without changing test behavior.
#>

# Ensure we operate from the tests directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptDir

$testPy = Join-Path $scriptDir 'test.py'

if (-not (Test-Path -Path $testPy)) {
    Write-Error "Test script not found: $testPy"
    exit 1
}

# Prefer the `python` command; fail with a clear message if not found
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error 'Python is not available in PATH. Please install Python or ensure it is on PATH.'
    exit 1
}

# Run the Python test harness with unbuffered output (matches CI)
& python -u $testPy
exit $LASTEXITCODE
