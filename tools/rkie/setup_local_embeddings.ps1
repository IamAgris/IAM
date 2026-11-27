<#
.SYNOPSIS
    Bootstrap local-only neural embeddings (Ollama + nomic-embed-text).
.DESCRIPTION
    Checks or installs Ollama, ensures the service is reachable, pulls the
    embedding model, verifies it and enables tools/rkie/config/embeddings.json.
    Never contacts an external embedding provider with repository content.
.EXAMPLE
    ./tools/rkie/setup_local_embeddings.ps1
.EXAMPLE
    ./tools/rkie/setup_local_embeddings.ps1 -CheckOnly
#>
[CmdletBinding()]
param(
    [switch] $CheckOnly,
    [string] $Model = 'nomic-embed-text',
    [string] $BaseUrl = 'http://localhost:11434'
)

$ErrorActionPreference = 'Continue'
$configPath = Join-Path $PSScriptRoot 'config/embeddings.json'

function Test-OllamaService {
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/tags" -TimeoutSec 5 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch { return $false }
}

$cli = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $cli) {
    Write-Host 'Ollama CLI not found.'
    if ($CheckOnly) { Write-Host 'CHECK: local embeddings unavailable (no Ollama).'; exit 1 }
    Write-Host 'Installing via winget: winget install --id Ollama.Ollama'
    winget install --id Ollama.Ollama --accept-package-agreements --accept-source-agreements --silent
    Write-Host 'Ollama installed. Open a new shell so PATH is refreshed, then rerun this script.'
    exit 2
}

$running = Test-OllamaService
if (-not $running) {
    if ($CheckOnly) { Write-Host 'CHECK: Ollama service not reachable.'; exit 1 }
    Write-Host 'Starting Ollama service...'
    Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        if (Test-OllamaService) { $running = $true; break }
    }
    if (-not $running) { Write-Error 'Ollama service did not become reachable.'; exit 1 }
}

$tags = (Invoke-RestMethod -Uri "$BaseUrl/api/tags" -TimeoutSec 10).models
if (-not ($tags | Where-Object { $_.name -like "$Model*" })) {
    if ($CheckOnly) { Write-Host "CHECK: model '$Model' not installed."; exit 1 }
    Write-Host "Pulling local model '$Model'..."
    $body = @{ name = $Model; stream = $false } | ConvertTo-Json -Compress
    $result = Invoke-RestMethod -Uri "$BaseUrl/api/pull" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 600
    if ($result.status -ne 'success') { Write-Error "Model pull failed: $($result.status)"; exit 1 }
}

if ($CheckOnly) {
    $dim = 0
    try {
        $body = @{ model = $Model; input = 'embedding check' } | ConvertTo-Json -Compress
        $embed = Invoke-RestMethod -Uri "$BaseUrl/api/embed" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 60
        $dim = $embed.embeddings[0].Count
    } catch { Write-Error "Embedding check failed: $($_.Exception.Message)"; exit 1 }
    Write-Host "CHECK OK: '$Model' is available locally ($dim dimensions)."
    exit 0
}

$settings = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$settings.enabled = $true
$settings.provider = 'ollama'
$settings.model = $Model
$settings.base_url = $BaseUrl
$settings.dimension = 768
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($configPath, ($settings | ConvertTo-Json -Depth 5), $utf8)
Write-Host "Enabled local neural embeddings: model=$Model base_url=$BaseUrl"
Write-Host 'Verify with: python tools/rkie/neural.py status --json'
