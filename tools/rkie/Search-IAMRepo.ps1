<#
.SYNOPSIS
    Local-first repository search for IAM. Searches tracked AND uncommitted files.
.DESCRIPTION
    Deterministic search toolkit. No LLM, no network, no external index required.
    Uses ripgrep when available, otherwise Select-String over the same file set.
    Secret files are excluded by default.
.EXAMPLE
    ./Search-IAMRepo.ps1 -Query modelrouter -Mode files
.EXAMPLE
    ./Search-IAMRepo.ps1 -Query "IntelligenceRouter" -Mode symbols -Scope backend
.EXAMPLE
    ./Search-IAMRepo.ps1 -Query "OD-46" -Mode docs -Json
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string] $Query,

    [ValidateSet('auto', 'content', 'files', 'docs', 'symbols', 'history', 'api', 'db', 'tests')]
    [string] $Mode = 'auto',

    [string] $Scope = '',
    [switch] $CaseSensitive,
    [switch] $Regex,
    [int] $MaxResults = 50,
    [int] $Context = 0,
    [switch] $IncludeSensitive,
    [switch] $Json,
    [switch] $ListModes
)

$ErrorActionPreference = 'Continue'

function Get-RepoRoot {
    $candidate = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    return $candidate
}

function Write-ModeHelp {
    @"
Mode        What it searches
---------   ---------------------------------------------------------------
auto        Filename + content + architecture docs (default)
content     Text inside source files
files       Filenames and paths (the fix for the 'modelrouter' GitHub miss)
docs        Authoritative architecture documents only (docs/, canonical/, notes)
symbols     Function / class / method definitions in Python and TypeScript
history     Git pickaxe: commits where the string was added or removed
api         backend/app/api/routes/
db          backend/app/models/ and backend/app/db/
tests       tests/, backend/tests/, sdk/*/tests/

Common switches: -Scope backend | frontend | sdk | iam | tools
                 -CaseSensitive  -Regex  -Context N  -MaxResults N
                 -IncludeSensitive  -Json
"@
}

$RepoRoot = Get-RepoRoot

if ($ListModes) {
    Write-ModeHelp
    return
}

if ([string]::IsNullOrWhiteSpace($Query)) {
    Write-Error "Provide -Query, or use -ListModes."
    return
}

$ignoreCase = -not $CaseSensitive

$secretPattern = '(?i)(^|/)\.env([./]|$)|(^|/)(secrets?|private)(/|$)|\.(pfx|p12|key|pem|crt|cer|keystore|jks|asc)$|(^|/)[^/]*credentials[^/]*\.(json|yaml|yml|txt|csv)$'
$textExtensions = @('.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.md', '.sql', '.yaml', '.yml', '.toml', '.ps1', '.sh', '.ini', '.cfg', '.txt', '.html', '.css', '.ipynb', '.conf', '.proto', '.example')

function Get-CandidateFiles {
    param(
        [string] $ScopePath = '',
        [switch] $DocsOnly,
        [switch] $TextOnly,
        [switch] $AllowSensitive
    )

    $raw = @(& git -C $RepoRoot ls-files --cached --others --exclude-standard 2>$null)
    $result = New-Object System.Collections.Generic.List[object]

    $scopeRegex = ''
    if (-not [string]::IsNullOrWhiteSpace($ScopePath)) {
        $scopeRegex = '^' + [regex]::Escape(($ScopePath -replace '\\', '/' -replace '^/+|/+$', '')) + '(/|$)'
    }

    foreach ($entry in $raw) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }
        $rel = $entry -replace '\\', '/'

        if (-not $AllowSensitive -and $rel -match $secretPattern) { continue }
        if ($scopeRegex -and $rel -notmatch $scopeRegex) { continue }

        $ext = [System.IO.Path]::GetExtension($rel).ToLowerInvariant()
        if ($TextOnly -and $textExtensions -notcontains $ext) { continue }

        $isDoc = $rel -match '\.md$' -and ($rel -notmatch '/' -or $rel -like 'docs/*' -or $rel -like 'canonical/*' -or $rel -like 'tools/rkie/*')
        if ($DocsOnly -and -not $isDoc) { continue }

        $full = Join-Path $RepoRoot ($rel -replace '/', [System.IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { continue }

        $item = Get-Item -LiteralPath $full -ErrorAction SilentlyContinue
        if ($null -eq $item) { continue }
        if ($TextOnly -and $item.Length -gt 2MB) { continue }

        $result.Add([pscustomobject]@{
            Rel  = $rel
            Full = $full
            Name = [System.IO.Path]::GetFileName($rel)
            IsDoc = [bool] $isDoc
        })
    }

    return $result.ToArray()
}

function New-Result {
    param([string] $Path, [int] $Line, [string] $Text, [int] $Score)
    return [pscustomobject]@{
        Path  = $Path
        Line  = $Line
        Score = $Score
        Text  = $Text
    }
}

# A search function that finds nothing returns $null through the pipeline.
# Append-Hits makes empty results harmless.
function Append-Hits {
    param([object[]] $Items)
    if ($null -eq $Items) { return }
    foreach ($item in $Items) {
        if ($null -ne $item) { $script:allHits.Add($item) }
    }
}

function Search-Filenames {
    param([object[]] $Files)
    $hits = New-Object System.Collections.Generic.List[object]
    foreach ($f in $Files) {
        $nameMatch = $false
        $pathMatch = $false
        if ($Regex) {
            $nameMatch = $f.Name -match $Query
            $pathMatch = $f.Rel -match $Query
        }
        else {
            $comparison = if ($ignoreCase) { [System.StringComparison]::OrdinalIgnoreCase } else { [System.StringComparison]::Ordinal }
            $nameMatch = $f.Name.IndexOf($Query, $comparison) -ge 0
            $pathMatch = $f.Rel.IndexOf($Query, $comparison) -ge 0
        }
        if ($nameMatch -or $pathMatch) {
            $score = if ($nameMatch) { 5 } else { 3 }
            $hits.Add((New-Result -Path $f.Rel -Line 0 -Text ('[filename] ' + $f.Rel) -Score $score))
        }
    }
    return $hits.ToArray()
}

function Invoke-Ripgrep {
    param([object[]] $Files, [string] $Pattern)
    $hits = New-Object System.Collections.Generic.List[object]
    $rgArgs = New-Object System.Collections.Generic.List[string]
    $rgArgs.Add('-n')
    $rgArgs.Add('--color')
    $rgArgs.Add('never')
    $rgArgs.Add('--no-heading')
    if ($ignoreCase) { $rgArgs.Add('-i') }
    if ($Regex) { } else { $rgArgs.Add('-F') }
    if ($Context -gt 0) { $rgArgs.Add('-C'); $rgArgs.Add([string] $Context) }
    $rgArgs.Add('-e')
    $rgArgs.Add($Pattern)
    $rgArgs.Add('--')

    Push-Location $RepoRoot
    try {
        for ($i = 0; $i -lt $Files.Count; $i += 200) {
            $chunk = @($Files[$i..([Math]::Min($i + 199, $Files.Count - 1))])
            if ($chunk.Count -eq 0) { continue }
            $callArgs = @($rgArgs) + @($chunk | ForEach-Object { $_.Rel })
            $lines = @(& rg @callArgs 2>$null)
            foreach ($line in $lines) {
                if ($line -eq '--') { continue }
                $m = [regex]::Match([string] $line, '^(.+?)([:-])(\d+)\2(.*)$')
                if (-not $m.Success) { continue }
                $path = $m.Groups[1].Value -replace '\\', '/'
                $lineNo = [int] $m.Groups[3].Value
                $text = $m.Groups[4].Value.Trim()
                if ($text.Length -gt 300) { $text = $text.Substring(0, 300) + '...' }
                $score = 2
                if ($text -match [regex]::Escape($Query)) { $score = 3 }
                $hits.Add((New-Result -Path $path -Line $lineNo -Text $text -Score $score))
            }
        }
    }
    finally {
        Pop-Location
    }
    return $hits.ToArray()
}

function Invoke-SelectStringSearch {
    param([object[]] $Files, [string] $Pattern)
    $hits = New-Object System.Collections.Generic.List[object]
    foreach ($f in $Files) {
        $params = @{ Path = $f.Full; Pattern = $Pattern; Encoding = 'UTF8'; ErrorAction = 'SilentlyContinue' }
        if (-not $ignoreCase) { $params['CaseSensitive'] = $true }
        if (-not $Regex) { $params['SimpleMatch'] = $true }
        if ($Context -gt 0) { $params['Context'] = $Context, $Context }

        $matches = @(Select-String @params)
        foreach ($m in $matches) {
            $text = $m.Line.Trim()
            if ($text.Length -gt 300) { $text = $text.Substring(0, 300) + '...' }
            $score = 2
            if ($text -match [regex]::Escape($Query)) { $score = 3 }
            if ($f.Name.IndexOf($Query, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) { $score += 2 }
            $hits.Add((New-Result -Path $f.Rel -Line $m.LineNumber -Text $text -Score $score))
        }
    }
    return $hits.ToArray()
}

function Search-Text {
    param([object[]] $Files, [string] $Pattern)
    if ($null -eq $Files -or $Files.Count -eq 0) { return @() }
    $rg = Get-Command rg -ErrorAction SilentlyContinue
    if ($null -ne $rg -and $Context -eq 0) {
        return Invoke-Ripgrep -Files $Files -Pattern $Pattern
    }
    return Invoke-SelectStringSearch -Files $Files -Pattern $Pattern
}

function Search-Symbols {
    param([object[]] $Files)
    $escaped = [regex]::Escape($Query)
    $pattern = '^\s*(?:(?:async\s+)?def\s+' + $escaped + '\b|class\s+' + $escaped + '\b|(?:export\s+)?(?:const|function|interface|type|enum)\s+' + $escaped + '\b)'
    $hits = New-Object System.Collections.Generic.List[object]
    foreach ($f in $Files) {
        # $Query is escaped above, so this is always a regex search.
        $params = @{ Path = $f.Full; Pattern = $pattern; Encoding = 'UTF8'; ErrorAction = 'SilentlyContinue' }
        $matches = @(Select-String @params)
        foreach ($m in $matches) {
            $hits.Add((New-Result -Path $f.Rel -Line $m.LineNumber -Text $m.Line.Trim() -Score 6))
        }
    }
    return $hits.ToArray()
}

function Search-History {
    $scopeArg = @()
    if (-not [string]::IsNullOrWhiteSpace($Scope)) {
        $scopeArg = @('--', ($Scope -replace '\\', '/' -replace '^/+|/+$', ''))
    }
    $pick = if ($Regex) { '-G' } else { '-S' }
    $args = @('-C', $RepoRoot, 'log', '--oneline', '--all', '-n', [string] $MaxResults, $pick, $Query) + $scopeArg
    $lines = @(& git @args 2>$null)
    $hits = New-Object System.Collections.Generic.List[object]
    foreach ($line in $lines) {
        $hits.Add((New-Result -Path '(git history)' -Line 0 -Text ([string] $line) -Score 1))
    }
    return $hits.ToArray()
}

# ---- Execute the requested mode -------------------------------------------

$allHits = New-Object System.Collections.Generic.List[object]
$engine = 'select-string'

switch ($Mode) {
    'files' {
        $files = Get-CandidateFiles -ScopePath $Scope -AllowSensitive:$IncludeSensitive
        Append-Hits -Items (Search-Filenames -Files $files)
        $engine = 'git ls-files'
    }
    'content' {
        $files = Get-CandidateFiles -ScopePath $Scope -TextOnly -AllowSensitive:$IncludeSensitive
        Append-Hits -Items (Search-Text -Files $files -Pattern $Query)
        if ($null -ne (Get-Command rg -ErrorAction SilentlyContinue)) { $engine = 'ripgrep' }
    }
    'docs' {
        $files = Get-CandidateFiles -ScopePath $Scope -DocsOnly -TextOnly -AllowSensitive:$IncludeSensitive
        Append-Hits -Items (Search-Text -Files $files -Pattern $Query)
        $engine = 'docs-only'
    }
    'symbols' {
        $files = Get-CandidateFiles -ScopePath $Scope -TextOnly -AllowSensitive:$IncludeSensitive | Where-Object { $_.Rel -match '\.(py|ts|tsx|js|jsx)$' }
        Append-Hits -Items (Search-Symbols -Files $files)
        $engine = 'regex-definitions'
    }
    'history' {
        Append-Hits -Items (Search-History)
        $engine = 'git log -S'
    }
    'api' {
        $files = Get-CandidateFiles -ScopePath 'backend/app/api/routes' -TextOnly -AllowSensitive:$IncludeSensitive
        Append-Hits -Items (Search-Text -Files $files -Pattern $Query)
    }
    'db' {
        $files = @()
        $files += Get-CandidateFiles -ScopePath 'backend/app/models' -TextOnly -AllowSensitive:$IncludeSensitive
        $files += Get-CandidateFiles -ScopePath 'backend/app/db' -TextOnly -AllowSensitive:$IncludeSensitive
        Append-Hits -Items (Search-Text -Files $files -Pattern $Query)
    }
    'tests' {
        $files = @()
        $files += Get-CandidateFiles -ScopePath 'tests' -TextOnly -AllowSensitive:$IncludeSensitive
        $files += Get-CandidateFiles -ScopePath 'backend/tests' -TextOnly -AllowSensitive:$IncludeSensitive
        $files += Get-CandidateFiles -ScopePath 'sdk' -TextOnly -AllowSensitive:$IncludeSensitive | Where-Object { $_.Rel -match '/tests?/' }
        Append-Hits -Items (Search-Text -Files $files -Pattern $Query)
    }
    default { # auto
        $allFiles = Get-CandidateFiles -ScopePath $Scope -TextOnly -AllowSensitive:$IncludeSensitive
        Append-Hits -Items (Search-Filenames -Files $allFiles)
        Append-Hits -Items (Search-Text -Files $allFiles -Pattern $Query)
        $docs = Get-CandidateFiles -ScopePath $Scope -DocsOnly -TextOnly -AllowSensitive:$IncludeSensitive
        $docHits = @(Search-Text -Files $docs -Pattern $Query)
        foreach ($h in $docHits) { $h.Score = [Math]::Max(1, $h.Score - 1) }
        Append-Hits -Items $docHits
    }
}

# ---- Deduplicate, rank and output -----------------------------------------

$seen = @{}
$unique = New-Object System.Collections.Generic.List[object]
foreach ($hit in $allHits) {
    $key = $hit.Path + '|' + $hit.Line + '|' + $hit.Text
    if (-not $seen.ContainsKey($key)) {
        $seen[$key] = $true
        $unique.Add($hit)
    }
}

$final = @($unique | Sort-Object -Property @{ Expression = 'Score'; Descending = $true }, Path, Line | Select-Object -First $MaxResults)

if ($Json) {
    [pscustomobject]@{
        Query       = $Query
        Mode        = $Mode
        Engine      = $engine
        Scope       = $Scope
        ResultCount = $final.Count
        Results     = $final
    } | ConvertTo-Json -Depth 6
    return
}

if ($final.Count -eq 0) {
    Write-Host ("No results for '{0}' in mode '{1}'." -f $Query, $Mode)
    if ($Mode -eq 'content' -or $Mode -eq 'auto') {
        Write-Host 'Hint: if you are looking for a FILE NAME, use -Mode files.'
    }
    return
}

Write-Host ("{0} result(s) - mode={1} engine={2} scope={3}" -f $final.Count, $Mode, $engine, $(if ($Scope) { $Scope } else { '(repo)' }))
$final | Format-Table Path, Line, Score, Text -AutoSize -Wrap
