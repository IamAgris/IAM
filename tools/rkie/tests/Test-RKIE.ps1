<#
.SYNOPSIS
    Smoke tests for the Phase 1 RKIE search and index toolkit.
.DESCRIPTION
    Exercises every search mode, secret exclusion, JSON output, no-result
    handling, incremental index stability and index freshness. Read-only with
    respect to repository source files; it only rewrites the generated index.
.EXAMPLE
    ./tools/rkie/tests/Test-RKIE.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'

$testsRoot = $PSScriptRoot
$rkieRoot = Split-Path -Parent $testsRoot
$repoRoot = (Resolve-Path (Join-Path $rkieRoot '..\..')).Path
$searchScript = Join-Path $rkieRoot 'Search-IAMRepo.ps1'
$indexScript = Join-Path $rkieRoot 'Update-Index.ps1'
$freshScript = Join-Path $rkieRoot 'Check-IndexFreshness.ps1'
$indexPath = Join-Path $rkieRoot 'index/file-index.json'

$script:passed = 0
$script:failed = 0

function Assert-Contains {
    param([string] $Output, [string] $Expected, [string] $Name)
    if ($Output.IndexOf($Expected, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
        $script:passed++
        Write-Host ("PASS  " + $Name)
    }
    else {
        $script:failed++
        Write-Host ("FAIL  " + $Name + "  (expected text: " + $Expected + ")")
    }
}

function Assert-NotContains {
    param([string] $Output, [string] $Unexpected, [string] $Name)
    if ($Output.IndexOf($Unexpected, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        $script:passed++
        Write-Host ("PASS  " + $Name)
    }
    else {
        $script:failed++
        Write-Host ("FAIL  " + $Name + "  (unexpected text: " + $Unexpected + ")")
    }
}

function Assert-Equal {
    param($Actual, $Expected, [string] $Name)
    if ([string]$Actual -eq [string]$Expected) {
        $script:passed++
        Write-Host ("PASS  " + $Name)
    }
    else {
        $script:failed++
        Write-Host ("FAIL  " + $Name + "  (expected " + $Expected + ", got " + $Actual + ")")
    }
}

Write-Host "RKIE smoke tests - repo: $repoRoot"
Write-Host ""

# 1. Mode help
$out = (& $searchScript -ListModes 2>&1 6>&1 | Out-String)
Assert-Contains $out 'auto' 'ListModes lists auto mode'
Assert-Contains $out 'history' 'ListModes lists history mode'

# 2. The GitHub miss case: filename search
$out = (& $searchScript -Query 'modelrouter' -Mode files 2>&1 6>&1 | Out-String)
Assert-Contains $out 'backend/app/api/routes/modelrouter.py' 'filename search finds modelrouter.py'
Assert-Contains $out 'backend/app/models/modelrouter.py' 'filename search finds model ORM file'

# 3. Secret exclusion by default
$out = (& $searchScript -Query '.env' -Mode files 2>&1 6>&1 | Out-String)
Assert-NotContains $out '.env.example' 'secret pattern excludes .env.example'
Assert-Contains $out 'No results' 'no results for excluded secret filename'

# 4. Architecture docs
# The authoritative doc corpus grew (licensing README, conflict report, automation spec),
# so the OD-46 authority can rank below position 20. Widen deliberately to 50 — still a
# bounded smoke assertion, not a full-corpus dump.
$out = (& $searchScript -Query 'OD-46' -Mode docs -MaxResults 50 2>&1 6>&1 | Out-String)
Assert-Contains $out 'docs/IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md' 'docs mode finds OD-46 authority'

# 5. Content search
$out = (& $searchScript -Query 'shared primary local brain' -Mode content -Scope backend -MaxResults 5 2>&1 6>&1 | Out-String)
Assert-Contains $out 'config.py' 'content search finds config comment'

# 6. Symbol definitions
$out = (& $searchScript -Query 'IntelligenceRouter' -Mode symbols -Scope backend 2>&1 6>&1 | Out-String)
Assert-Contains $out 'intel_router_service.py' 'symbols mode finds class definition'

# 7. API routes
$out = (& $searchScript -Query '/api/v1/memory' -Mode api 2>&1 6>&1 | Out-String)
Assert-Contains $out 'memory.py' 'api mode finds route prefix'

# 8. Database models
$out = (& $searchScript -Query 'KnowledgeItem' -Mode db 2>&1 6>&1 | Out-String)
Assert-Contains $out 'models/memory.py' 'db mode finds ORM model'

# 9. Git history
$out = (& $searchScript -Query 'model router' -Mode history -MaxResults 5 2>&1 6>&1 | Out-String)
Assert-Contains $out '(git history)' 'history mode uses git pickaxe'

# 10. Machine-readable output
$out = (& $searchScript -Query 'Qwen' -Mode auto -Scope backend -MaxResults 3 -Json 2>&1 6>&1 | Out-String)
Assert-Contains $out '"ResultCount"' 'JSON output has ResultCount'
Assert-Contains $out '"Results"' 'JSON output has Results'

# 11. No-result handling includes the filename hint.
# Build the query in two parts so the literal itself is not stored in this file
# (otherwise the search would match this test script).
$noMatch = 'zzq' + 'x-nomatch-7f3a9'
$out = (& $searchScript -Query $noMatch -Mode auto 2>&1 6>&1 | Out-String)
Assert-Contains $out 'No results' 'no-result path reports no results'
Assert-Contains $out '-Mode files' 'no-result path suggests filename mode'

# 12. Incremental index is stable once the working tree settles.
# Three runs absorb a file written concurrently with the start of the test.
& $indexScript -Quiet | Out-Null
& $indexScript -Quiet | Out-Null
& $indexScript -Quiet | Out-Null
$index = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8 | ConvertFrom-Json
Assert-Equal $index.stats.added 0 'incremental index: no additions on repeat run'
Assert-Equal $index.stats.changed 0 'incremental index: no changes on repeat run'
Assert-Equal $index.stats.removed 0 'incremental index: no removals on repeat run'

# 13. Freshness check passes after index update
$fresh = (& $freshScript 2>&1 6>&1 | Out-String)
Assert-Contains $fresh 'FRESH' 'freshness check passes after index refresh'

Write-Host ""
Write-Host ("Result: {0} passed, {1} failed" -f $script:passed, $script:failed)
if ($script:failed -gt 0) { exit 1 } else { exit 0 }
