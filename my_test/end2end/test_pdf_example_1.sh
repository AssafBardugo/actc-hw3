#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR="http://localhost:3000"
NS="default"

echo "===> Creating health ReplicaSet (3 replicas)"

curl -s -X POST "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets" \
  -H "Content-Type: application/json" \
  -d '{
    "apiVersion": "apps/v1",
    "kind": "ReplicaSet",
    "metadata": {
      "name": "health-replicaset"
    },
    "spec": {
      "replicas": 3,
      "selector": {
        "name": "health"
      },
      "template": {
        "metadata": {
          "app": "health"
        },
        "spec": {
          "containers": [{
            "name": "health",
            "image": "health:latest"
          }]
        }
      }
    }
  }'

sleep 3

echo "===> Creating health Service"

curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/services" \
  -H "Content-Type: application/json" \
  -d '{
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
      "name": "health-service"
    },
    "spec": {
      "selector": {
        "app": "health"
      },
      "ports": [{
        "protocol": "TCP",
        "port": 2000,
        "targetPort": 5000
      }],
      "type": "ClusterIP"
    }
  }'

echo "===> Creating ping Pod (NO LABELS)"

curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" \
  -H "Content-Type: application/json" \
  -d '{
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
      "name": "ping"
    },
    "spec": {
      "containers": [{
        "name": "ping",
        "image": "ping:latest",
        "env": {
          "HEALTH_SERVICE": "health-service:2000"
        }
      }]
    }
  }'

sleep 3

echo "===> Verifying Service is reachable from host"

curl -sf "http://localhost:2000/health" > /dev/null
echo "PASS: Service reachable from host"

echo "===> Verifying load-balancing across replicas"

RESULTS=()
for i in {1..5}; do
  RESP=$(curl -s "http://localhost:2000/health")
  echo "Response $i: $RESP"
  RESULTS+=("$RESP")
done

UNIQUE=$(printf "%s\n" "${RESULTS[@]}" | sort | uniq | wc -l)

if [ "$UNIQUE" -lt 2 ]; then
  echo "FAIL: Service does not appear to load-balance"
  exit 1
fi

echo "PASS: Load balancing detected"

echo "===> Verifying ping pod is NOT part of service"

# This assumes health pods identify themselves differently than ping
for r in "${RESULTS[@]}"; do
  if echo "$r" | grep -qi "ping"; then
    echo "FAIL: ping pod received service traffic"
    exit 1
  fi
done

echo "PASS: ping pod not part of service"

echo
echo "ALL PDF EXAMPLE TESTS PASSED"
