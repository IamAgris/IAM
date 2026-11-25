# IAM Multi-Architecture Build Script
# Builds backend and frontend images for linux/amd64 + linux/arm64.
# Usage: .\scripts\build-multiarch.ps1 [-Push] [-Tag "v1.0"]

param(
    [switch]$Push,
    [string]$Tag = "latest",
    [string]$Registry = "local"
)

$ErrorActionPreference = "Stop"
$platforms = "linux/amd64,linux/arm64"
$images = @{
    backend = "iam-backend"
    frontend = "iam-frontend"
}

Write-Host "=== IAM Multi-Architecture Build ==="
Write-Host "Platforms: $platforms"
Write-Host "Tag: $Tag"
Write-Host ""

# Ensure a multi-platform builder exists
$builder = docker buildx ls | Select-String "iam-multiarch"
if (-not $builder) {
    Write-Host "Creating buildx builder 'iam-multiarch'..."
    docker buildx create --name iam-multiarch --driver docker-container --use
} else {
    docker buildx use iam-multiarch
}
docker buildx inspect --bootstrap | Out-Null

foreach ($name in $images.Keys) {
    $imageName = $images[$name]
    $fullTag = "$Registry/$imageName`:$Tag"
    Write-Host "--- Building $fullTag ($name) ---"
    $context = Join-Path (Get-Location) $name

    if ($Push -and $Registry -ne "local") {
        docker buildx build --platform $platforms -t $fullTag --push $context
    } else {
        docker buildx build --platform $platforms -t $fullTag --load $context 2>&1 |
            Where-Object { $_ -notmatch "^#\d+\s" }
        Write-Host "Loaded locally: $fullTag (current platform only with --load)"
    }
}

Write-Host ""
Write-Host "=== Build complete ==="
Write-Host "Manifest inspection:"
foreach ($name in $images.Keys) {
    $imageName = $images[$name]
    docker buildx imagetools inspect "$Registry/$imageName`:$Tag" 2>$null | Select-String "Platform|Architecture" | Select-Object -First 4
}
