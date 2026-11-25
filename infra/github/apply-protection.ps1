# =============================================================================
# Apply BALANCED GitHub repository protection to IamAgris/IAM
# =============================================================================
# Run after the GitHub credential for github.com belongs to an account with
# admin rights on the target repository (owner or collaborator with Admin).
#
# Usage:  powershell -ExecutionPolicy Bypass -File infra\github\apply-protection.ps1
#
# The token is read from the local Git Credential Manager; it is never printed
# or written to disk.

$ErrorActionPreference = 'Stop'

$owner  = 'IamAgris'
$repo   = 'IAM'
$branch = 'main'

# --- Read GitHub token from the local credential manager ---------------------
$cred  = "protocol=https`nhost=github.com`n`n" | git credential fill 2>$null
$token = ($cred | Where-Object { $_ -like 'password=*' }) -replace '^password=',''
if (-not $token) { throw 'No GitHub credential found for github.com.' }

$headers = @{
    Authorization           = "Bearer $token"
    'User-Agent'            = 'iam-repo-protection'
    Accept                  = 'application/vnd.github+json'
    'X-GitHub-Api-Version'  = '2022-11-28'
}
$base = "https://api.github.com/repos/$owner/$repo"

# --- Confirm identity and permissions ----------------------------------------
$me   = Invoke-RestMethod -Headers $headers -Uri 'https://api.github.com/user'
$info = Invoke-RestMethod -Headers $headers -Uri $base
Write-Host "Authenticated as: $($me.login)"
Write-Host "Target: $($info.full_name) | push=$($info.permissions.push) admin=$($info.permissions.admin)"
if (-not $info.permissions.admin) {
    throw 'Authenticated account lacks admin rights; cannot apply protection.'
}

# --- 1. Balanced branch protection on main ----------------------------------
$protection = @{
    required_status_checks = @{
        strict   = $true
        contexts = @()
    }
    enforce_admins = $true
    required_pull_request_reviews = @{
        dismiss_stale_reviews           = $true
        require_code_owner_reviews      = $false
        required_approving_review_count = 1
        require_last_push_approval      = $false
    }
    restrictions                     = $null
    allow_force_pushes               = $false
    allow_deletions                  = $false
    required_conversation_resolution = $false
    lock_branch                      = $false
    allow_fork_syncing               = $false
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Put -Headers $headers -Uri "$base/branches/$branch/protection" -Body $protection | Out-Null
Write-Host "Applied branch protection to '$branch'."

# --- 2. Dependabot alerts ----------------------------------------------------
$alertHeaders = @{}
foreach ($k in $headers.Keys) { $alertHeaders[$k] = $headers[$k] }
$alertHeaders['Accept'] = 'application/vnd.github.dorian-preview+json'
try {
    Invoke-RestMethod -Method Put -Headers $alertHeaders -Uri "$base/vulnerability-alerts" | Out-Null
    Write-Host 'Enabled Dependabot alerts.'
} catch {
    Write-Warning "Dependabot alerts could not be enabled: $($_.Exception.Message)"
}

# --- 3. Dependabot security updates -----------------------------------------
$fixHeaders = @{}
foreach ($k in $headers.Keys) { $fixHeaders[$k] = $headers[$k] }
$fixHeaders['Accept'] = 'application/vnd.github.london-preview+json'
try {
    Invoke-RestMethod -Method Put -Headers $fixHeaders -Uri "$base/automated-security-fixes" | Out-Null
    Write-Host 'Enabled Dependabot security updates.'
} catch {
    Write-Warning "Security updates could not be enabled: $($_.Exception.Message)"
}

# --- 4. Secret scanning + push protection (best effort) ---------------------
$scanBody = @{
    security_and_analysis = @{
        secret_scanning                = @{ status = 'enabled' }
        secret_scanning_push_protection = @{ status = 'enabled' }
    }
} | ConvertTo-Json -Depth 5
try {
    Invoke-RestMethod -Method Patch -Headers $headers -Uri $base -Body $scanBody | Out-Null
    Write-Host 'Enabled secret scanning and push protection.'
} catch {
    Write-Warning "Secret scanning settings could not be applied: $($_.Exception.Message)"
}

# --- 5. Verify ---------------------------------------------------------------
$v = Invoke-RestMethod -Headers $headers -Uri "$base/branches/$branch/protection"
Write-Host '--- Verification ---'
Write-Host "Required reviewers : $($v.required_pull_request_reviews.required_approving_review_count)"
Write-Host "Dismiss stale      : $($v.required_pull_request_reviews.dismiss_stale_reviews)"
Write-Host "Enforce on admins  : $($v.enforce_admins.enabled)"
Write-Host "Force pushes       : $($v.allow_force_pushes.enabled)"
Write-Host "Branch deletions   : $($v.allow_deletions.enabled)"
Write-Host 'Done.'
