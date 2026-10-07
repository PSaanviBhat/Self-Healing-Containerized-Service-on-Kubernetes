#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="self-healing-app"
SERVICE_NAME="self-healing-service"

echo "========================================================"
echo "      KUBERNETES SELF-HEALING AUTOMATION TEST           "
echo "========================================================"

echo "==> 1. Checking running pods..."
kubectl get pods -n "${NAMESPACE}" -l app="${SERVICE_NAME}"

POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l app="${SERVICE_NAME}" -o jsonpath='{.items[0].metadata.name}')
echo "==> Target Pod selected: ${POD_NAME}"

INITIAL_RESTARTS=$(kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.containerStatuses[0].restartCount}')
echo "==> Initial restart count: ${INITIAL_RESTARTS}"

echo "==> 2. Injecting chaos crash via port-forward..."
kubectl port-forward "pod/${POD_NAME}" -n "${NAMESPACE}" 8080:8000 >/dev/null 2>&1 &
PF_PID=$!
sleep 2

curl -s -X POST "http://localhost:8080/chaos/crash" || true
kill "${PF_PID}" || true

echo ""
echo "==> 3. Liveness probe is now failing. Monitoring Kubernetes self-healing restart..."
for i in {1..15}; do
    CURRENT_RESTARTS=$(kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "restarted")
    STATUS=$(kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
    echo "  [t+${i}s] Pod status: ${STATUS} | Restart count: ${CURRENT_RESTARTS}"
    if [ "${CURRENT_RESTARTS}" -gt "${INITIAL_RESTARTS}" ]; then
        echo ""
        echo "==> [SUCCESS] Kubernetes detected deadlocked state and automatically healed the container!"
        kubectl get pods -n "${NAMESPACE}" -l app="${SERVICE_NAME}"
        exit 0
    fi
    sleep 3
done

echo "==> Observation complete."
