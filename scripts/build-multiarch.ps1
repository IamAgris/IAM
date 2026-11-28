# Build IAM images for AMD64 and ARM64 without assuming a registry is available.
# Requires Docker Desktop / buildx with QEMU emulation for cross-architecture builds.
# Each platform is exported as a loadable Docker archive under artifacts/.

param(
    [string[]] $Services = @("backend", "frontend"),
    [string[]] $Platforms = @("linux/amd64", "linux/arm64"),
    [string] $OutputDir = "artifacts/multiarch"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$builder = "iam-multiarch"
$existing = docker buildx ls | Select-String -Pattern "^$builder\s"
if (-not $existing) {
    docker buildx create --name $builder --driver docker-container --use --bootstrap
} else {
    docker buildx use $builder
}
docker buildx inspect --bootstrap | Out-Null

foreach ($service in $Services) {
    $contextPath = if ($service -eq "backend") { "backend" } else { "frontend" }
    foreach ($platform in $Platforms) {
        $arch = $platform.Split("/")[1]
        $tag = "project-aura-${service}:${arch}"
        $dest = Join-Path $OutputDir "${service}-${arch}.tar"
        Write-Host "Building $service for $platform -> $dest"
        docker buildx build --platform $platform -t $tag --output "type=docker,dest=$dest" $contextPath
        if ($LASTEXITCODE -ne 0) { throw "build failed for $service / $platform" }
        Write-Host "Wrote $dest"
    }
}

Write-Host @'
Loading on a target machine:
  docker load -i artifacts/multiarch/backend-arm64.tar
  docker image inspect project-aura-backend:arm64 --format '{{.Architecture}}'

To publish to a registry instead, replace --output with --push and use a tag your
registry accepts, e.g. registry.example.com/iam/backend:arm64.
'@
