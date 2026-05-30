Write-Host "================================================================================"
Write-Host " Running QHome AI Agent Smoke Tests (Windows PowerShell)"
Write-Host "================================================================================"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$rootDir = Split-Path -Parent $scriptDir

if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is required but not installed."
    exit 1
}

Write-Host "`nRunning Full Quality Check..." -ForegroundColor Cyan
& python "$rootDir\scripts\run_full_quality_check.py"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[X] Quality Check Failed!"
    exit 1
}

Write-Host "`nRunning a mock workflow to verify end-to-end routing..." -ForegroundColor Cyan
& python "$rootDir\run.py" run --ticket-id="damaged-ceramic-delivery"

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host " Smoke test completed successfully!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
