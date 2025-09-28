#!/usr/bin/env pwsh
<#
PowerShell port of initTest.bat
Attempts to run the corresponding test script (prefers a .ps1 test if available, falls back to calling the .bat if present).
#>

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$targetPs1 = Join-Path -Path $scriptDir -ChildPath "..\..\test\test.ps1"
$targetBat = Join-Path -Path $scriptDir -ChildPath "..\..\test\test.bat"

if (Test-Path -Path $targetPs1) {
    & "$targetPs1" @args
    exit $LASTEXITCODE
} elseif (Test-Path -Path $targetBat) {
    # Preserve original behavior by invoking cmd to call the batch file
    $quotedTarget = [char]34 + $targetBat + [char]34
    $argList = @('/c', 'call', $quotedTarget)
    if ($args) { $argList += $args }
    $proc = Start-Process -FilePath 'cmd.exe' -ArgumentList $argList -NoNewWindow -Wait -PassThru
    exit $proc.ExitCode
} else {
    Write-Host ('Target test script not found: {0} or {1}' -f $targetPs1, $targetBat)
    exit 1
}
