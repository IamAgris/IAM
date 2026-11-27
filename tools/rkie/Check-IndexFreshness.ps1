<#
.SYNOPSIS
    Verify that tools/rkie/index/file-index.json matches the current working tree.
.DESCRIPTION
    Recomputes SHA-256 hashes for the same candidate file set used by
    Update-Index.ps1. Read-only: never modifies the index. Exits 1 when stale.
.EXAMPLE
    ./Check-IndexFreshness.ps1
.EXAMPLE
    ./Check-IndexFreshness.ps1 -Json
#>
[CmdletBinding()]
param(
    [switch] $Json,
    [int] $MaxExamples = 20
)

$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$IndexPath = Join-Path $PSScriptRoot 'index/file-index.json'

if (-not (Test-Path -LiteralPath $IndexPath)) {
    Write-Error "Index not found: $IndexPath. Run Update-Index.ps1 first."
    exit 2
}

$index = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
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

$current = @{}
$entries = @(& git -C $RepoRoot ls-files --cached --others --exclude-standard 2>$null)
foreach ($entry in $entries) {
    if ([string]::IsNullOrWhiteSpace($entry)) { continue }
    $rel = $entry -replace '\\', '/'
    if ($rel -match $secretPattern) { continue }
    if ($rel -eq 'tools/rkie/index/file-index.json') { continue }
    $full = Join-Path $RepoRoot ($rel -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { continue }
    $current[$rel] = Get-Sha256 -Path $full
}

$indexed = @{}
foreach ($f in $index.files) { $indexed[$f.path] = $f.sha256 }

$changed = @()
$removed = @()
$newFiles = @()

foreach ($path in $indexed.Keys) {
    if (-not $current.ContainsKey($path)) {
        $removed += $path
    }
    elseif ($current[$path] -ne $indexed[$path]) {
        $changed += $path
    }
}
foreach ($path in $current.Keys) {
    if (-not $indexed.ContainsKey($path)) { $newFiles += $path }
}

$head = (& git -C $RepoRoot rev-parse HEAD 2>$null)
if ([string]::IsNullOrWhiteSpace($head)) { $head = '(none)' }
$headMismatch = ($head -ne $index.baseCommit)

$changed = @($changed | Sort-Object)
$removed = @($removed | Sort-Object)
$newFiles = @($newFiles | Sort-Object)
$isStale = ($changed.Count -gt 0 -or $removed.Count -gt 0 -or $newFiles.Count -gt 0 -or $headMismatch)
$statusText = 'FRESH'
if ($isStale) { $statusText = 'STALE' }

$result = [pscustomobject]@{
    Status           = $statusText
    GeneratedAt      = $index.generatedAt
    BaseCommit       = $index.baseCommit
    HeadCommit       = $head
    HeadMismatch     = $headMismatch
    ChangedCount     = $changed.Count
    RemovedCount     = $removed.Count
    NewCount         = $newFiles.Count
    ChangedExamples  = @($changed | Select-Object -First $MaxExamples)
    RemovedExamples  = @($removed | Select-Object -First $MaxExamples)
    NewExamples      = @($newFiles | Select-Object -First $MaxExamples)
}

if ($Json) {
    $result | ConvertTo-Json -Depth 5
}
else {
    Write-Host ("Index: {0} | generated {1} | base {2} | HEAD {3}" -f $result.Status, $result.GeneratedAt, $result.BaseCommit, $result.HeadCommit)
    Write-Host ("changed: {0} | removed: {1} | new: {2} | HEAD mismatch: {3}" -f $result.ChangedCount, $result.RemovedCount, $result.NewCount, $result.HeadMismatch)
    if ($result.ChangedCount -gt 0) { Write-Host ("Changed files: " + ($result.ChangedExamples -join ', ')) }
    if ($result.RemovedCount -gt 0) { Write-Host ("Missing files: " + ($result.RemovedExamples -join ', ')) }
    if ($result.NewCount -gt 0) { Write-Host ("New files: " + ($result.NewExamples -join ', ')) }
    if ($isStale) { Write-Host 'Run ./tools/rkie/Update-Index.ps1 to refresh.' }
}

if ($isStale) { exit 1 } else { exit 0 }
