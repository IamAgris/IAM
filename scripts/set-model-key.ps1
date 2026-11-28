# IAM — Set a model provider API key (NVIDIA free endpoints recommended)
# Usage: .\scripts\set-model-key.ps1 -Provider nvidia -Key "nvapi-..."
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("nvidia","dashscope")]
    [string]$Provider,
    [Parameter(Mandatory=$true)]
    [string]$Key
)

$envPath = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
if (-not (Test-Path $envPath)) { throw ".env not found" }

$keyName = if ($Provider -eq "nvidia") { "NVIDIA_API_KEY" } else { "DASHSCOPE_API_KEY" }
$content = Get-Content $envPath -Raw
if ($content -match "(?m)^$keyName=.*$") {
    $content = $content -replace "(?m)^$keyName=.*$", "$keyName=$Key"
} else {
    $content += "`n$keyName=$Key`n"
}
Set-Content -Path $envPath -Value $content -NoNewline
Write-Host "Set $keyName in .env"

# Recreate backend so the container picks up the new env
Write-Host "Recreating backend container..."
Push-Location (Split-Path $PSScriptRoot -Parent)
docker compose up -d --force-recreate backend
Pop-Location

Write-Host ""
Write-Host "Waiting for backend..."
Start-Sleep -Seconds 15
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/models/router/discover/nvidia" -Method Post -TimeoutSec 30 -ErrorAction Stop
    Write-Host "Model discovery: $($r.count) models found via $($r.provider)"
} catch {
    Write-Host "Model discovery check failed (normal if key is invalid): $($_.Exception.Message)"
}
