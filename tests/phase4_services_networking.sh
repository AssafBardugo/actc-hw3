#!/usr/bin/env bash
set -euo pipefail

ORCH=http://localhost:3000
RS=health-rs
SVC=health-svc

echo "[Phase 4] Starting orchestrator..."
uv run orchestrator.py --port 3000 &
PID=$!
sleep 3

cleanup() {
  echo "[Phase 4] Cleanup"
  curl -s -X DELETE $ORCH/api/apps/v1/namespaces/default/replicasets/$RS >/dev/null || true
  curl -s -X DELETE $ORCH/api/v1/namespaces/default/services/$SVC >/dev/null || true
  kill $PID || true
}
trap cleanup EXIT

echo "[Phase 4] Create ReplicaSet (health)"
curl -sf -X POST $ORCH/api/apps/v1/namespaces/default/replicasets \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"apps/v1\",
    \"kind\": \"ReplicaSet\",
    \"metadata\": { \"name\": \"$RS\" },
    \"spec\": {
      \"replicas\": 2,
      \"selector\": { \"app\": \"health\" },
      \"template\": {
        \"metadata\": { \"labels\": { \"app\": \"health\" }},
        \"spec\": {
          \"containers\": [{
            \"name\": \"health\",
            \"image\": \"health\"
          }]
        }
      }
    }
  }" >/dev/null

sleep 4

echo "[Phase 4] Create Service"
curl -sf -X POST $ORCH/api/v1/namespaces/default/services \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"v1\",
    \"kind\": \"Service\",
    \"metadata\": { \"name\": \"$SVC\" },
    \"spec\": {
      \"selector\": { \"app\": \"health\" },
      \"ports\": [{
        \"port\": 2000,
        \"targetPort\": 5000
      }]
    }
  }" >/dev/null

sleep 2

echo "[Phase 4] Curl service from host"
curl -sf http://localhost:2000/health >/dev/null

echo "[Phase 4] PASS"
