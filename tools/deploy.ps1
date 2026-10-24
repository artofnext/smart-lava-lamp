# Upload firmware/*.py to the board over USB. Never touches config.json.
# Usage: ./tools/deploy.ps1 [-Port COM5]
# Runs mpremote through uv (uvx), so nothing needs to be installed.
param([string]$Port = "auto")
$ErrorActionPreference = "Stop"
$fw = Join-Path $PSScriptRoot "..\firmware"
$conn = if ($Port -eq "auto") { @() } else { @("connect", $Port) }

function mpr { uvx mpremote @conn @args; if ($LASTEXITCODE) { throw "mpremote failed" } }

Get-ChildItem $fw -Filter *.py | ForEach-Object {
    mpr fs cp $_.FullName ":$($_.Name)"
}
if (Test-Path "$fw\web") {
    mpr fs mkdir :web 2>$null
    Get-ChildItem "$fw\web" -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring((Resolve-Path "$fw\web").Path.Length + 1)
        mpr fs cp $_.FullName ":web/$($rel -replace '\\','/')"
    }
}
mpr reset
