#!/usr/bin/env bash
set -euo pipefail

ORCH=http://localhost:3000
RS=rs-test

echo "[Phase 3] Starting orchestrator..."
uv run orchestrator.py --port 3000 &
PID=$!
sleep 2

cleanup() {
  echo "[Phase 3] Cleanup"
  curl -s -X DELETE $ORCH/api/apps/v1/namespaces/default/replicasets/$RS >/dev/null || true
  kill $PID || true
}
trap cleanup EXIT

echo "[Phase 3] Create ReplicaSet (replicas=2)"
curl -sf -X POST $ORCH/api/apps/v1/namespaces/default/replicasets \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"apps/v1\",
    \"kind\": \"ReplicaSet\",
    \"metadata\": { \"name\": \"$RS\" },
    \"spec\": {
      \"replicas\": 2,
      \"selector\": { \"app\": \"rs\" },
      \"template\": {
        \"metadata\": { \"labels\": { \"app\": \"rs\" }},
        \"spec\": {
          \"containers\": [{
            \"name\": \"worker\",
            \"image\": \"health\"
          }]
        }
      }
    }
  }" >/dev/null

sleep 4

echo "[Phase 3] Verify 2 pods exist"
COUNT=$(curl -s $ORCH/api/v1/namespaces/default/pods | jq '.items | length')
test "$COUNT" -eq 2

echo "[Phase 3] Scale to 3 replicas"
curl -sf -X PUT $ORCH/api/apps/v1/namespaces/default/replicasets/$RS \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"apps/v1\",
    \"kind\": \"ReplicaSet\",
    \"metadata\": { \"name\": \"$RS\" },
    \"spec\": { \"replicas\": 3 }
  }" >/dev/null

sleep 4

COUNT=$(curl -s $ORCH/api/v1/namespaces/default/pods | jq '.items | length')
test "$COUNT" -eq 3

echo "[Phase 3] PASS"
