#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="self-healing-k8s-service:latest"

echo "==> Building application container image..."
docker build -t "${IMAGE_NAME}" -f Dockerfile .

echo "==> Verifying non-root user execution..."
USER_ID=$(docker run --rm "${IMAGE_NAME}" id -u)
if [ "${USER_ID}" -eq "10001" ]; then
    echo "  [PASS] Container runs as non-root user (UID ${USER_ID})"
else
    echo "  [FAIL] Container running as UID ${USER_ID}, expected 10001"
    exit 1
fi

echo "==> Building Go CLI container image..."
docker build -t "k8s-health-pinger:latest" -f docker/Dockerfile.cli .

echo "==> Images built and verified successfully."
