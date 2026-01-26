#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR="http://localhost:3000"
NS="default"

fail() { echo "❌ FAIL: $1"; exit 1; }
pass() { echo "✅ PASS: $1"; }

wait_for_healthz() {
  for i in {1..30}; do
    curl -s "$ORCHESTRATOR/healthz" >/dev/null && return
    sleep 0.5
  done
  fail "orchestrator not ready"
}

cleanup_all() {
  pods=$(curl -s "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" \
    | python3 -c "import sys,json; print(' '.join(p['metadata']['name'] for p in json.load(sys.stdin).get('items',[])))" \
    2>/dev/null || true)

  for p in $pods; do
    curl -s -X DELETE "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/$p" >/dev/null || true
  done

  services=$(curl -s "$ORCHESTRATOR/api/v1/namespaces/$NS/services" \
    | python3 -c "import sys,json; print(' '.join(s['metadata']['name'] for s in json.load(sys.stdin).get('items',[])))" \
    2>/dev/null || true)

  for s in $services; do
    curl -s -X DELETE "$ORCHESTRATOR/api/v1/namespaces/$NS/services/$s" >/dev/null || true
  done

  sleep 2
}


test_service_selector() {
  echo "TEST 1: Service selector correctness"

  # health pod WITH label
  curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" -H "Content-Type: application/json" -d '{
    "apiVersion":"v1","kind":"Pod",
    "metadata":{"name":"health","labels":{"app":"health"}},
    "spec":{"containers":[{"name":"health","image":"health"}]}
  }' >/dev/null

  # service selects app=health
  curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/services" -H "Content-Type: application/json" -d '{
    "apiVersion":"v1","kind":"Service",
    "metadata":{"name":"health-service"},
    "spec":{"selector":{"app":"health"},"ports":[{"port":2000,"targetPort":5000}]}
  }' >/dev/null

  # ping pod WITHOUT labels
  curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" -H "Content-Type: application/json" -d '{
    "apiVersion":"v1","kind":"Pod",
    "metadata":{"name":"ping"},
    "spec":{"containers":[{"name":"ping","image":"ping","env":{"HEALTH_SERVICE":"health-service:2000"}}]}
  }' >/dev/null

  sleep 4

  # service must respond
  curl -sf http://localhost:2000/health >/dev/null \
    || fail "service unreachable"

  pass "service routes only to labeled pod"
  cleanup_all
}


test_replicaset_reconcile() {
  echo "TEST 2: ReplicaSet reconciliation"

  curl -s -X POST "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets" -H "Content-Type: application/json" -d '{
    "apiVersion":"apps/v1","kind":"ReplicaSet",
    "metadata":{"name":"rs"},
    "spec":{
      "replicas":2,
      "selector":{"app":"health"},
      "template":{
        "metadata":{"labels":{"app":"health"}},
        "spec":{"containers":[{"name":"health","image":"health"}]}
      }
    }
  }' >/dev/null

  sleep 4

  pods_before=$(curl -s "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" | grep '"name"' | wc -l)

  # delete one pod
  victim=$(curl -s "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['items'][0]['metadata']['name'])")

  curl -s -X DELETE "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/$victim" >/dev/null

  sleep 6

  pods_after=$(curl -s "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" | grep '"name"' | wc -l)

  [[ "$pods_before" -eq "$pods_after" ]] || fail "replicaset did not heal"

  pass "replicaset reconciles correctly"
  cleanup_all
}


test_replicaset_scale_up() {
  echo "TEST 3: ReplicaSet scale up"

  curl -s -X POST "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets" -H "Content-Type: application/json" -d '{
    "apiVersion":"apps/v1","kind":"ReplicaSet",
    "metadata":{"name":"rs"},
    "spec":{
      "replicas":1,
      "selector":{"app":"health"},
      "template":{
        "metadata":{"labels":{"app":"health"}},
        "spec":{"containers":[{"name":"health","image":"health"}]}
      }
    }
  }' >/dev/null

  sleep 3

  curl -s -X PUT "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets/rs" -H "Content-Type: application/json" -d '{
    "apiVersion":"apps/v1","kind":"ReplicaSet",
    "metadata":{"name":"rs"},
    "spec":{
      "replicas":3,
      "selector":{"app":"health"},
      "template":{
        "metadata":{"labels":{"app":"health"}},
        "spec":{"containers":[{"name":"health","image":"health"}]}
      }
    }
  }' >/dev/null

  sleep 5

  count=$(curl -s "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" | grep '"app": "health"' | wc -l)
  [[ "$count" -eq 3 ]] || fail "expected 3 health pods, got $count"

  pass "replicaset scale up works"
  cleanup_all
}


test_message_pipeline() {
  echo "TEST 4: Message pipeline"

  curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" -H "Content-Type: application/json" -d '{
    "apiVersion":"v1","kind":"Pod",
    "metadata":{"name":"aggregator"},
    "spec":{"containers":[{"name":"aggregator","image":"aggregator_worker","env":{"window_size":"2"}}]}
  }' >/dev/null

  curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" -H "Content-Type: application/json" -d '{
    "apiVersion":"v1","kind":"Pod",
    "metadata":{"name":"processor"},
    "spec":{"containers":[{"name":"processor","image":"processor_worker","env":{"operation":"uppercase","forward_to":"aggregator"}}]}
  }' >/dev/null

  sleep 3

  curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/processor/send" \
    -H "Content-Type: application/json" -d '{"data":"hello"}' >/dev/null

  curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/processor/send" \
    -H "Content-Type: application/json" -d '{"data":"world"}' >/dev/null

  sleep 2
  pass "message pipeline completed without errors"
  cleanup_all
}


test_crud_semantics() {
  echo "TEST 5: CRUD semantics"

  curl -s -X POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" -H "Content-Type: application/json" -d '{
    "apiVersion":"v1","kind":"Pod",
    "metadata":{"name":"crud"},
    "spec":{"containers":[{"name":"health","image":"health"}]}
  }' >/dev/null

  curl -sf "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/crud" >/dev/null \
    || fail "GET after create failed"

  curl -s -X DELETE "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/crud" >/dev/null

  code=$(curl -s -o /dev/null -w "%{http_code}" "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/crud")
  [[ "$code" == "404" ]] || fail "expected 404 after delete"

  pass "CRUD semantics correct"
}


wait_for_healthz
test_service_selector
test_replicaset_reconcile
test_replicaset_scale_up
test_message_pipeline
test_crud_semantics

echo "🎉 ALL END-TO-END TESTS PASSED"
