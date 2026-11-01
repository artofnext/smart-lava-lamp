# Upload firmware/*.py to the board over USB.
# Usage: ./tools/deploy.ps1 [-Port COM5] [-Config]
param([string]$Port = "auto", [switch]$Config)
$ErrorActionPreference = "Stop"
$fw = Join-Path $PSScriptRoot "..\firmware"
$conn = if ($Port -eq "auto") { @() } else { @("connect", $Port) }

function mpr { uvx mpremote @conn @args; if ($LASTEXITCODE) { throw "mpremote failed" } }

# 1. Upload config.json if requested
if ($Config -and (Test-Path "$fw\config.json")) {
    Write-Host "Uploading config.json..."
    mpr cp "$fw\config.json" :config.json
}

# 2. Upload all python firmware files
Get-ChildItem $fw -Filter *.py | ForEach-Object {
    mpr cp $_.FullName ":$($_.Name)"
}

# 3. Upload web UI
if (Test-Path "$fw\web\index.html") {
    $ls = uvx mpremote @conn ls 2>&1 | Out-String
    if ($ls -notmatch "web") {
        mpr mkdir :web
    }
    mpr cp "$fw\web\index.html" :web/index.html
}

# 4. Restart board
Write-Host "Restarting board to run updated code..."
mpr reset
Write-Host "Deploy finished successfully!"
