#!/usr/bin/env bash
set -euo pipefail

ORCH=http://localhost:3000
POD=test-podman-pod

echo "[Phase 2] Starting orchestrator..."
uv run orchestrator.py --port 3000 &
PID=$!
sleep 2

cleanup() {
  echo "[Phase 2] Cleanup"
  podman rm -f $POD >/dev/null 2>&1 || true
  kill $PID || true
}
trap cleanup EXIT

echo "[Phase 2] Create pod"
curl -sf -X POST $ORCH/api/v1/namespaces/default/pods \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"v1\",
    \"kind\": \"Pod\",
    \"metadata\": { \"name\": \"$POD\" },
    \"spec\": {
      \"containers\": [{
        \"name\": \"worker\",
        \"image\": \"health\"
      }]
    }
  }" >/dev/null

sleep 3

echo "[Phase 2] Verify container running"
podman ps --format "{{.Names}}" | grep -q "^$POD$"

echo "[Phase 2] Kill container manually"
podman rm -f $POD

echo "[Phase 2] Wait for reconciliation"
sleep 5

echo "[Phase 2] Verify container restarted"
podman ps --format "{{.Names}}" | grep -q "^$POD$"

echo "[Phase 2] PASS"
