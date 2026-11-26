<#
.SYNOPSIS
    Incrementally index IAM repository files (paths + hashes + architecture links).
.DESCRIPTION
    Stores only metadata, never file contents. Unchanged files reuse their old
    entry, so repeated runs are cheap. Deleted/renamed files are dropped.
.EXAMPLE
    ./Update-Index.ps1
.EXAMPLE
    ./Update-Index.ps1 -Force
#>
[CmdletBinding()]
param(
    [switch] $Force,
    [switch] $Quiet
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ConfigPath = Join-Path $PSScriptRoot 'config/architecture-links.json'
$IndexPath = Join-Path $PSScriptRoot 'index/file-index.json'

if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Missing config: $ConfigPath" }
$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

$indexDir = Split-Path -Parent $IndexPath
if (-not (Test-Path -LiteralPath $indexDir)) { New-Item -ItemType Directory -Path $indexDir -Force | Out-Null }

$previous = @{}
if (-not $Force -and (Test-Path -LiteralPath $IndexPath)) {
    try {
        $old = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($f in $old.files) { $previous[$f.path] = $f }
    }
    catch {
        Write-Warning "Existing index could not be read; rebuilding. $($_.Exception.Message)"
    }
}

$secretPattern = '(?i)(^|/)\.env([./]|$)|(^|/)(secrets?|private)(/|$)|\.(pfx|p12|key|pem|crt|cer|keystore|jks|asc)$|(^|/)[^/]*credentials[^/]*\.(json|yaml|yml|txt|csv)$'

function Get-Sha256 {
    param([string] $Path)
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            return ([System.BitConverter]::ToString($sha.ComputeHash($stream)) -replace '-', '').ToLowerInvariant()
        }
        finally { $sha.Dispose() }
    }
    finally { $stream.Dispose() }
}

function Get-Category {
    param([string] $Rel)
    if ($Rel -match '\.md$') {
        if ($Rel -notmatch '/' -or $Rel -like 'canonical/*') { return 'document-authoritative' }
        return 'document'
    }
    if ($Rel -like 'backend/app/api/routes/*') { return 'api-route' }
    if ($Rel -like 'backend/app/services/*') { return 'service' }
    if ($Rel -like 'backend/app/models/*') { return 'orm-model' }
    if ($Rel -like 'backend/app/db/migrations/*') { return 'migration' }
    if ($Rel -like 'backend/app/core/*') { return 'core' }
    if ($Rel -like 'backend/app/orchestration/*') { return 'orchestration' }
    if ($Rel -like 'backend/app/workers/*') { return 'worker' }
    if ($Rel -like 'backend/tests/*' -or $Rel -like 'tests/*' -or $Rel -match '/tests?/') { return 'test' }
    if ($Rel -like 'frontend/*') { return 'frontend' }
    if ($Rel -like 'sdk/*') { return 'sdk' }
    if ($Rel -like 'infra/*') { return 'infrastructure' }
    if ($Rel -like 'tools/rkie/*' -or $Rel -like 'scripts/*') { return 'tooling' }
    if ($Rel -match '(^|/)\.env' -or $Rel -like 'docker-compose*' -or $Rel -like '*.toml' -or $Rel -like '*.yaml') { return 'configuration' }
    return 'other'
}

$tracked = @{}
foreach ($t in @(& git -C $RepoRoot ls-files --cached 2>$null)) {
    if (-not [string]::IsNullOrWhiteSpace($t)) { $tracked[($t -replace '\\', '/')] = $true }
}

$entries = @(& git -C $RepoRoot ls-files --cached --others --exclude-standard 2>$null)

$files = New-Object System.Collections.Generic.List[object]
$added = 0
$changed = 0
$unchanged = 0

foreach ($entry in $entries) {
    if ([string]::IsNullOrWhiteSpace($entry)) { continue }
    $rel = $entry -replace '\\', '/'
    if ($rel -match $secretPattern) { continue }
    if ($rel -eq 'tools/rkie/index/file-index.json') { continue }

    $full = Join-Path $RepoRoot ($rel -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { continue }

    $item = Get-Item -LiteralPath $full -ErrorAction SilentlyContinue
    if ($null -eq $item) { continue }
    $hash = Get-Sha256 -Path $full

    $old = $null
    if ($previous.ContainsKey($rel)) { $old = $previous[$rel] }

    if ($null -ne $old -and $old.sha256 -eq $hash) {
        $spec = $old.spec
        $decisions = $old.decisions
        $area = $old.area
        $superseded = [bool] $old.superseded
        $unchanged++
    }
    else {
        $spec = $config.default.spec
        $decisions = @($config.default.decisions)
        $area = $config.default.area
        $superseded = $false

        foreach ($m in $config.mappings) {
            if ($rel -match $m.pattern) {
                $spec = $m.spec
                $decisions = @($m.decisions)
                $area = $m.area
                break
            }
        }
        foreach ($p in $config.superseded) {
            if ($rel -match $p) { $superseded = $true; break }
        }

        if ($null -eq $old) { $added++ } else { $changed++ }
    }

    $files.Add([pscustomobject]@{
        path       = $rel
        sha256     = $hash
        bytes      = $item.Length
        status     = if ($tracked.ContainsKey($rel)) { 'tracked' } else { 'untracked' }
        category   = Get-Category -Rel $rel
        area       = $area
        spec       = $spec
        decisions  = $decisions
        superseded = $superseded
    })
}

$removed = 0
foreach ($key in $previous.Keys) {
    $stillThere = $false
    foreach ($f in $files) { if ($f.path -eq $key) { $stillThere = $true; break } }
    if (-not $stillThere) { $removed++ }
}

$baseCommit = (& git -C $RepoRoot rev-parse HEAD 2>$null)
if ([string]::IsNullOrWhiteSpace($baseCommit)) { $baseCommit = '(none)' }

$payload = [pscustomobject]@{
    version        = 1
    generatedAt    = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    baseCommit     = $baseCommit
    configVersion  = $config.version
    stats          = [pscustomobject]@{
        files     = $files.Count
        added     = $added
        changed   = $changed
        removed   = $removed
        unchanged = $unchanged
    }
    files          = @($files | Sort-Object -Property path)
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($IndexPath, ($payload | ConvertTo-Json -Depth 8), $utf8NoBom)

if (-not $Quiet) {
    Write-Host ("Index written: {0}" -f $IndexPath)
    Write-Host ("Files: {0} | added: {1} | changed: {2} | removed: {3} | unchanged: {4} | base commit: {5}" -f `
        $files.Count, $added, $changed, $removed, $unchanged, $baseCommit.Substring(0, [Math]::Min(7, $baseCommit.Length)))
}
