#!/usr/bin/env bash
set -euo pipefail

ORCH=http://localhost:3000

echo "[Phase 1] Starting orchestrator..."
uv run orchestrator.py --port 3000 &
PID=$!
sleep 2

cleanup() {
  echo "[Phase 1] Cleaning up"
  kill $PID || true
}
trap cleanup EXIT

echo "[Phase 1] Health check"
curl -sf $ORCH/healthz >/dev/null

echo "[Phase 1] Create pod"
curl -sf -X POST $ORCH/api/v1/namespaces/default/pods \
  -H "Content-Type: application/json" \
  -d '{
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": { "name": "test-pod" },
    "spec": {
      "containers": [{
        "name": "worker",
        "image": "health"
      }]
    }
  }' >/dev/null

sleep 2

echo "[Phase 1] Verify pod exists"
curl -sf $ORCH/api/v1/namespaces/default/pods/test-pod >/dev/null

echo "[Phase 1] Delete pod"
curl -sf -X DELETE $ORCH/api/v1/namespaces/default/pods/test-pod >/dev/null

sleep 1

echo "[Phase 1] Verify pod deleted (expect failure)"
if curl -sf $ORCH/api/v1/namespaces/default/pods/test-pod; then
  echo "ERROR: pod still exists"
  exit 1
fi

echo "[Phase 1] PASS"
