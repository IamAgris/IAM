# Local equivalent of .github/workflows/ci.yml.
# Requires the Docker Compose Postgres + Redis services to be running.
# Reads credentials from .env but never prints them.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$values = @{}
$envFile = Join-Path $root '.env'
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*([A-Z0-9_]+)=(.*)$') { $values[$Matches[1]] = $Matches[2] }
    }
}
$pgPass = $env:POSTGRES_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { $values['POSTGRES_PASSWORD'] }
$pgPort = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { $values['POSTGRES_PORT'] }
$redisPort = if ($env:REDIS_PORT) { $env:REDIS_PORT } else { $values['REDIS_PORT'] }
if (-not $pgPass) { $pgPass = 'change-me-securely' }
if (-not $pgPort) { $pgPort = '5434' }
if (-not $redisPort) { $redisPort = '6381' }

$env:POSTGRES_HOST = '127.0.0.1'
$env:POSTGRES_PORT = $pgPort
$env:POSTGRES_PASSWORD = $pgPass
$env:DATABASE_URL = "postgresql+asyncpg://aura:$pgPass@127.0.0.1:$pgPort/aura_integration_test"
$env:REDIS_URL = "redis://127.0.0.1:$redisPort/0"
$env:PYTHONPATH = Join-Path $root 'backend'

Write-Host '== backend compile =='
python -m compileall -q backend/app
if ($LASTEXITCODE -ne 0) { throw 'compile failed' }

Write-Host '== backend unit tests =='
python -m unittest discover -s backend/tests -p 'test_*.py' -q
if ($LASTEXITCODE -ne 0) { throw 'unit tests failed' }

Write-Host '== postgres + redis integration =='
python backend/tests/integration_db_check.py
if ($LASTEXITCODE -ne 0) { throw 'integration failed' }

Write-Host '== frontend build =='
Push-Location (Join-Path $root 'frontend')
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'frontend build failed' }
} finally { Pop-Location }

Write-Host 'LOCAL CI PASSED'
