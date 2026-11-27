<#
.SYNOPSIS
    Run Ollama in Docker for local embeddings when it cannot be installed natively.
.DESCRIPTION
    Starts an Ollama container, pulls nomic-embed-text through its local API and
    enables tools/rkie/config/embeddings.json. No repository content is sent
    anywhere except this local container.
#>
[CmdletBinding()]
param(
    [string] $Model = 'nomic-embed-text',
    [string] $BaseUrl = 'http://localhost:11434',
    [string] $Container = 'iam-ollama'
)

$existing = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $Container }
if (-not $existing) {
    Write-Host 'Starting Ollama container...'
    docker run -d --name $Container -p 11434:11434 -v iam_ollama_data:/root/.ollama ollama/ollama
}
else {
    $running = docker ps --format '{{.Names}}' | Where-Object { $_ -eq $Container }
    if (-not $running) { docker start $Container | Out-Null }
}

for ($i = 0; $i -lt 30; $i++) {
    try {
        (Invoke-WebRequest -Uri "$BaseUrl/api/tags" -TimeoutSec 3 -UseBasicParsing) | Out-Null
        break
    }
    catch { Start-Sleep -Seconds 1 }
}

$body = @{ name = $Model; stream = $false } | ConvertTo-Json -Compress
$result = Invoke-RestMethod -Uri "$BaseUrl/api/pull" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 600
if ($result.status -ne 'success') { Write-Error "Pull failed: $($result.status)"; exit 1 }

$configPath = Join-Path $PSScriptRoot 'config/embeddings.json'
$settings = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$settings.enabled = $true
$settings.provider = 'ollama'
$settings.model = $Model
$settings.base_url = $BaseUrl
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($configPath, ($settings | ConvertTo-Json -Depth 5), $utf8)
Write-Host "Enabled local neural embeddings via Docker container '$Container'."
