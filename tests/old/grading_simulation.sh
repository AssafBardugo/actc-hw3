#!/usr/bin/env bash
set -euo pipefail

ORCH=http://localhost:3000
NS=default

RS=health-replicaset
SVC=health-service
PING=ping

echo "=============================================="
echo " ACTC HW3 - GRADING SIMULATION TEST"
echo "=============================================="

echo "[1] Starting orchestrator"
uv run orchestrator.py --port 3000 &
PID=$!
sleep 3

cleanup() {
  echo
  echo "[CLEANUP]"
  curl -s -X DELETE $ORCH/api/apps/v1/namespaces/$NS/replicasets/$RS >/dev/null || true
  curl -s -X DELETE $ORCH/api/v1/namespaces/$NS/services/$SVC >/dev/null || true
  curl -s -X DELETE $ORCH/api/v1/namespaces/$NS/pods/$PING >/dev/null || true
  kill $PID >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[2] Health check"
curl -sf $ORCH/healthz >/dev/null

# ------------------------------------------------
# Step 1: Create ReplicaSet (3 replicas)
# ------------------------------------------------
echo "[3] Create ReplicaSet (3 replicas)"

curl -sf -X POST \
  $ORCH/api/apps/v1/namespaces/$NS/replicasets \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"apps/v1\",
    \"kind\": \"ReplicaSet\",
    \"metadata\": {
      \"name\": \"$RS\"
    },
    \"spec\": {
      \"replicas\": 3,
      \"selector\": { \"app\": \"health\" },
      \"template\": {
        \"metadata\": { \"labels\": { \"app\": \"health\" } },
        \"spec\": {
          \"containers\": [{
            \"name\": \"health\",
            \"image\": \"health:latest\"
          }]
        }
      }
    }
  }" >/dev/null

echo "    waiting for reconciliation..."
sleep 5

COUNT=$(curl -s $ORCH/api/v1/namespaces/$NS/pods | jq '.items | length')
test "$COUNT" -eq 3

echo "    OK: 3 pods running"

# ------------------------------------------------
# Step 2: Create Service
# ------------------------------------------------
echo "[4] Create Service (ClusterIP → host port)"

curl -sf -X POST \
  $ORCH/api/v1/namespaces/$NS/services \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"v1\",
    \"kind\": \"Service\",
    \"metadata\": {
      \"name\": \"$SVC\"
    },
    \"spec\": {
      \"selector\": { \"app\": \"health\" },
      \"ports\": [{
        \"protocol\": \"TCP\",
        \"port\": 2000,
        \"targetPort\": 5000
      }],
      \"type\": \"ClusterIP\"
    }
  }" >/dev/null

sleep 2

echo "[5] Test service from host"
curl -sf http://localhost:2000/health >/dev/null
echo "    OK: service reachable from host"

# ------------------------------------------------
# Step 3: Create Ping Pod
# ------------------------------------------------
echo "[6] Create ping pod"

curl -sf -X POST \
  $ORCH/api/v1/namespaces/$NS/pods \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"v1\",
    \"kind\": \"Pod\",
    \"metadata\": {
      \"name\": \"$PING\"
    },
    \"spec\": {
      \"containers\": [{
        \"name\": \"ping\",
        \"image\": \"ping:latest\",
        \"env\": {
          \"HEALTH_SERVICE\": \"$SVC:2000\"
        }
      }]
    }
  }" >/dev/null

sleep 4

echo "    (ping pod should be calling health service now)"

# ------------------------------------------------
# Step 4: Scale ReplicaSet to 5
# ------------------------------------------------
echo "[7] Scale ReplicaSet to 5 replicas"

curl -sf -X PUT \
  $ORCH/api/apps/v1/namespaces/$NS/replicasets/$RS \
  -H "Content-Type: application/json" \
  -d "{
    \"apiVersion\": \"apps/v1\",
    \"kind\": \"ReplicaSet\",
    \"metadata\": {
      \"name\": \"$RS\"
    },
    \"spec\": {
      \"replicas\": 5
    }
  }" >/dev/null

sleep 5

COUNT=$(curl -s $ORCH/api/v1/namespaces/$NS/pods | jq '.items | length')
test "$COUNT" -eq 6   # 5 health + 1 ping

echo "    OK: scaled correctly"

# ------------------------------------------------
# Step 5: Pod self-healing
# ------------------------------------------------
echo "[8] Delete one health pod manually"

POD_TO_KILL=$(curl -s $ORCH/api/v1/namespaces/$NS/pods | \
  jq -r '.items[] | select(.metadata.labels.app=="health") | .metadata.name' | head -n1)

curl -sf -X DELETE \
  $ORCH/api/v1/namespaces/$NS/pods/$POD_TO_KILL >/dev/null

sleep 5

COUNT=$(curl -s $ORCH/api/v1/namespaces/$NS/pods | jq '.items | length')
test "$COUNT" -eq 6

echo "    OK: ReplicaSet recreated missing pod"

# ------------------------------------------------
# Step 6: Final service check
# ------------------------------------------------
echo "[9] Final service check"
curl -sf http://localhost:2000/health >/dev/null

echo
echo "=============================================="
echo " 🎉 GRADING SIMULATION PASSED"
echo "=============================================="
