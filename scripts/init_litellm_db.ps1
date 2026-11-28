# OD-52: create LiteLLM's dedicated database in the existing postgres service.
# Idempotent. Credentials are read from .env and never printed.

$ErrorActionPreference = 'Stop'
$envFile = Join-Path (Join-Path $PSScriptRoot '..') '.env'
$user = 'aura'
$password = 'change-me-securely'

foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*([A-Za-z0-9_]+)=(.*)$') {
        switch ($Matches[1]) {
            'POSTGRES_USER' { $user = $Matches[2] }
            'POSTGRES_PASSWORD' { $password = $Matches[2] }
        }
    }
}

$exists = (docker exec -e "PGPASSWORD=$password" aura-postgres psql -U $user -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'litellm_db'" | Out-String).Trim()
if ($exists -ne '1') {
    docker exec -e "PGPASSWORD=$password" aura-postgres psql -U $user -d postgres -c 'CREATE DATABASE litellm_db;'
}

Write-Output 'litellm_db ready'
