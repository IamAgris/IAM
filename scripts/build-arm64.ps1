# Optional ARM64 image verification — requires Docker Buildx + QEMU/binfmt.
# Run from the repository root:
#   docker run --privileged --rm tonistiigi/binfmt --install arm64
#   docker buildx create --use --name iam-multiarch
#   ./scripts/build-arm64.ps1

$ErrorActionPreference = "Stop"

docker buildx build --platform linux/arm64 -t project-aura-backend:arm64 --load ./backend
docker buildx build --platform linux/arm64 -t project-aura-frontend:arm64 --load ./frontend

Write-Host "ARM64 images built. Verify with: docker image inspect project-aura-backend:arm64 --format '{{.Architecture}}'"
