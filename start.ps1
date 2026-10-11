<#
.SYNOPSIS
    cortex.ai - Windows PowerShell Lifecycle Manager
    Starts and manages all services in the cortex.ai monorepo.
#>

param (
    [switch]$Stop,
    [switch]$SeedOnly,
    [switch]$TestOnly
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# Find Python interpreter
$PythonExe = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

if ($Stop) {
    Write-Host "[!] Stopping any running cortex.ai services..." -ForegroundColor Yellow
    $ports = @(8000, 8001, 8002, 8003, 8004, 8005, 8011, 8012, 8013, 8014, 8015, 4200)
    foreach ($port in $ports) {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($conns) {
            foreach ($conn in $conns) {
                try { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
            }
        }
    }
    Write-Host "[+] All cortex.ai processes stopped." -ForegroundColor Green
    exit 0
}

if ($SeedOnly) {
    & $PythonExe database/seed_db.py
    exit 0
}

if ($TestOnly) {
    & $PythonExe scripts/eval/eval_runner.py
    exit 0
}

& $PythonExe scripts/run_all.py
