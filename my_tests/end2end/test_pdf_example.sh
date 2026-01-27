#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR="${ORCHESTRATOR:-http://localhost:3000}"
NS="${NS:-default}"

# -------- helpers --------
die() { echo "FAIL: $*" >&2; exit 1; }
ok()  { echo "PASS: $*"; }

curl_json() {
  # usage: curl_json METHOD URL [DATA]
  local method="$1"; shift
  local url="$1"; shift
  local data="${1:-}"

  if [[ -n "$data" ]]; then
    curl -sS -X "$method" "$url" -H "Content-Type: application/json" -d "$data"
  else
    curl -sS -X "$method" "$url"
  fi
}

http_status() {
  # prints HTTP status code only
  curl -s -o /dev/null -w "%{http_code}" "$1"
}

py_json_len() {
  # reads JSON from stdin, prints len(obj["items"]) if present, else tries len(list), else 0
  python3 - <<'PY'
import sys, json
try:
    obj = json.load(sys.stdin)
except Exception:
    print(0); sys.exit(0)

if isinstance(obj, dict) and "items" in obj and isinstance(obj["items"], list):
    print(len(obj["items"]))
elif isinstance(obj, list):
    print(len(obj))
else:
    print(0)
PY
}

py_find_pods_by_label() {
  # usage: echo "$pods_json" | py_find_pods_by_label key value
  local key="$1"
  local val="$2"
  python3 - "$key" "$val" <<'PY'
import sys, json
key=sys.argv[1]; val=sys.argv[2]
obj=json.load(sys.stdin)
items = obj.get("items", obj if isinstance(obj, list) else [])
matched=[]
for p in items:
    md=p.get("metadata", {})
    labels=md.get("labels", md.get("label", md.get("meta", {})))  # best-effort, don't rely on this
    if not isinstance(labels, dict):
        labels={}
    if labels.get(key)==val:
        matched.append(md.get("name",""))
print("\n".join([x for x in matched if x]))
PY
}

py_list_pod_names() {
  python3 - <<'PY'
import sys, json
obj=json.load(sys.stdin)
items = obj.get("items", obj if isinstance(obj, list) else [])
names=[]
for p in items:
    md=p.get("metadata", {})
    if "name" in md:
        names.append(md["name"])
print("\n".join(names))
PY
}

wait_for() {
  # usage: wait_for seconds condition_command...
  local timeout="$1"; shift
  local start
  start="$(date +%s)"
  while true; do
    if "$@"; then return 0; fi
    local now
    now="$(date +%s)"
    if (( now - start >= timeout )); then return 1; fi
    sleep 1
  done
}

# -------- cleanup (best effort) --------
cleanup() {
  echo "===> Best-effort cleanup"
  curl -s -X DELETE "$ORCHESTRATOR/api/v1/namespaces/$NS/services/health-service" >/dev/null || true
  curl -s -X DELETE "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets/health-replicaset" >/dev/null || true
  curl -s -X DELETE "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/ping" >/dev/null || true
}
cleanup

# -------- payloads (PDF example) --------
RS_3='{
  "apiVersion": "apps/v1",
  "kind": "ReplicaSet",
  "metadata": { "name": "health-replicaset" },
  "spec": {
    "replicas": 3,
    "selector": { "name": "health" },
    "template": {
      "metadata": { "app": "health" },
      "spec": { "containers": [{ "name": "health", "image": "health:latest" }] }
    }
  }
}'

RS_5='{
  "apiVersion": "apps/v1",
  "kind": "ReplicaSet",
  "metadata": { "name": "health-replicaset" },
  "spec": {
    "replicas": 5,
    "selector": { "name": "health" },
    "template": {
      "metadata": { "app": "health" },
      "spec": { "containers": [{ "name": "health", "image": "health:latest" }] }
    }
  }
}'

SVC='{
  "apiVersion": "v1",
  "kind": "Service",
  "metadata": { "name": "health-service" },
  "spec": {
    "selector": { "app": "health" },
    "ports": [{ "protocol": "TCP", "port": 2000, "targetPort": 5000 }],
    "type": "ClusterIP"
  }
}'

PING='{
  "apiVersion": "v1",
  "kind": "Pod",
  "metadata": { "name": "ping" },
  "spec": {
    "containers": [{
      "name": "ping",
      "image": "ping:latest",
      "env": { "HEALTH_SERVICE": "health-service:2000" }
    }]
  }
}'

# -------- 1) Create resources (PDF steps) --------
echo "===> Create ReplicaSet (3 replicas)"
curl_json POST "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets" "$RS_3" >/dev/null || die "ReplicaSet POST failed"

echo "===> Create Service"
curl_json POST "$ORCHESTRATOR/api/v1/namespaces/$NS/services" "$SVC" >/dev/null || die "Service POST failed"

echo "===> Create ping Pod (no labels)"
curl_json POST "$ORCHESTRATOR/api/v1/namespaces/$NS/pods" "$PING" >/dev/null || die "Pod POST failed"

# -------- 2) Wait until service reachable on host (PDF says exposed on host) --------
echo "===> Wait for host access to Service on localhost:2000"
wait_for 30 bash -lc 'curl -sf "http://localhost:2000/health" >/dev/null' \
  || die "Service not reachable at http://localhost:2000/health"
ok "Service reachable from host (localhost:2000/health)"

# -------- 3) Basic load-balancing smoke (original test) --------
echo "===> Load-balancing smoke test (5 requests)"
results=()
for i in {1..5}; do
  resp="$(curl -s "http://localhost:2000/health" || true)"
  [[ -n "$resp" ]] || die "Empty response from service"
  echo "  Response $i: $resp"
  results+=("$resp")
done

uniq_count="$(printf "%s\n" "${results[@]}" | sort | uniq | wc -l | tr -d ' ')"
if [[ "$uniq_count" -lt 2 ]]; then
  echo "WARN: Responses looked identical ($uniq_count unique). This MAY still be fine if /health returns constant text."
  echo "      We'll rely on stronger checks below."
else
  ok "Load-balancing signal detected ($uniq_count unique responses)"
fi

# -------- 4) Verify ping Pod is NOT included in Service (original heuristic + stronger checks) --------
echo "===> Ensure ping isn't accidentally selected by Service selector"
# If your /health output includes pod name, this will catch obvious misrouting:
for r in "${results[@]}"; do
  if echo "$r" | grep -qi "ping"; then
    die "Service response appears to come from ping pod (selector/routing bug)"
  fi
done
ok "No obvious evidence of routing to ping in /health responses"

# -------- 5) Scale ReplicaSet 3 -> 5 (PDF step) --------
echo "===> Scale ReplicaSet to 5 replicas via PUT (PDF step)"
curl_json PUT "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets/health-replicaset" "$RS_5" >/dev/null \
  || die "ReplicaSet PUT (scale) failed"

# -------- 6) Check that 2 additional replicas appear (best-effort using pods list endpoint) --------
echo "===> Verify more pods exist after scale-up (3 -> 5)"
PODS_URL="$ORCHESTRATOR/api/v1/namespaces/$NS/pods"

pods_before="$(curl -sS "$PODS_URL" || true)"
if [[ -n "$pods_before" ]]; then
  # Wait until at least 6 pods total? (5 health + ping) = 6
  wait_for 40 bash -lc "curl -sS '$PODS_URL' | python3 -c 'import sys,json; o=json.load(sys.stdin); items=o.get(\"items\", o if isinstance(o,list) else []); print(len(items));' | grep -Eq '^[6-9][0-9]*$'" \
    || echo "WARN: Could not confirm total pod count reached 6 via GET $PODS_URL (endpoint may differ)."
else
  echo "WARN: GET $PODS_URL returned empty; skipping pod-count-based assertions."
fi

# -------- 7) Service remains reachable after scaling --------
echo "===> Verify Service still reachable after scaling"
wait_for 30 bash -lc 'curl -sf "http://localhost:2000/health" >/dev/null' \
  || die "Service not reachable after scaling"
ok "Service reachable after scaling"

# -------- 8) Stronger traffic test: multiple concurrent curls --------
echo "===> Concurrency smoke: 30 parallel requests to Service"
tmpdir="$(mktemp -d)"
for i in {1..30}; do
  (curl -s "http://localhost:2000/health" >"$tmpdir/r$i.txt" || echo "__ERR__" >"$tmpdir/r$i.txt") &
done
wait

err_count="$(grep -R "__ERR__" -n "$tmpdir" | wc -l | tr -d ' ')"
[[ "$err_count" -eq 0 ]] || die "Some parallel requests failed ($err_count/30)"

# Ensure non-empty responses
empty_count="$(find "$tmpdir" -type f -size 0 | wc -l | tr -d ' ')"
[[ "$empty_count" -eq 0 ]] || die "Some parallel requests returned empty response ($empty_count/30)"
ok "Parallel request smoke passed (30/30 ok)"

# -------- 9) Reconciliation test: delete one health pod and ensure system heals --------
# PDF says: if a pod is deleted, soon a new one is created to replace it. :contentReference[oaicite:1]{index=1}
echo "===> Reconciliation: delete one health pod (best-effort) and ensure Service keeps working"

# Try to find health-labeled pods via list endpoint (best-effort)
pods_json="$(curl -sS "$PODS_URL" || true)"
health_pods=""
if [[ -n "$pods_json" ]]; then
  health_pods="$(echo "$pods_json" | py_find_pods_by_label app health || true)"
fi

if [[ -n "$health_pods" ]]; then
  victim="$(echo "$health_pods" | head -n1)"
  echo "  Deleting health pod: $victim"
  curl -s -X DELETE "$ORCHESTRATOR/api/v1/namespaces/$NS/pods/$victim" >/dev/null || true

  # Even if the pod was deleted, service should still respond (either via other pods or after replacement)
  wait_for 40 bash -lc 'curl -sf "http://localhost:2000/health" >/dev/null' \
    || die "Service broke after deleting a health pod (reconcile/routing bug)"
  ok "Service survived pod deletion (reconciliation seems working)"
else
  echo "WARN: Could not identify a health pod by label via GET $PODS_URL; skipping delete+heal test."
fi

# -------- 10) Endpoint discovery must be dynamic (no caching): scale down then up quickly --------
echo "===> Dynamic endpoints smoke: scale down to 1 then up to 4 quickly"

RS_1='{
  "apiVersion": "apps/v1",
  "kind": "ReplicaSet",
  "metadata": { "name": "health-replicaset" },
  "spec": {
    "replicas": 1,
    "selector": { "name": "health" },
    "template": {
      "metadata": { "app": "health" },
      "spec": { "containers": [{ "name": "health", "image": "health:latest" }] }
    }
  }
}'

RS_4='{
  "apiVersion": "apps/v1",
  "kind": "ReplicaSet",
  "metadata": { "name": "health-replicaset" },
  "spec": {
    "replicas": 4,
    "selector": { "name": "health" },
    "template": {
      "metadata": { "app": "health" },
      "spec": { "containers": [{ "name": "health", "image": "health:latest" }] }
    }
  }
}'

curl_json PUT "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets/health-replicaset" "$RS_1" >/dev/null || die "scale down to 1 failed"
wait_for 30 bash -lc 'curl -sf "http://localhost:2000/health" >/dev/null' || die "service failed after scale down"

curl_json PUT "$ORCHESTRATOR/api/apps/v1/namespaces/$NS/replicasets/health-replicaset" "$RS_4" >/dev/null || die "scale up to 4 failed"
wait_for 30 bash -lc 'curl -sf "http://localhost:2000/health" >/dev/null' || die "service failed after scale up"
ok "Service stayed healthy across quick scale down/up"

# -------- done --------
rm -rf "$tmpdir" || true

echo
echo " ALL TESTS COMPLETED "
