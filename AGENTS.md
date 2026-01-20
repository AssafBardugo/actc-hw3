# AGENTS.md — ACTC HW3 Orchestrator (Authoritative Spec for Tests)

## Purpose of this file
This file is the **single source of truth** for generating tests for ACTC HW3.

Your job (CODEX/agent) is to:
- Generate tests that reflect the HW requirements (from the PDF).
- Avoid out-of-scope assumptions (especially “real Kubernetes” features).
- Help the student reach a **100** by aligning tests to the assignment and expected graders/tests.

---

## ABSOLUTE SCOPE RESTRICTION — TESTS ONLY

**You MUST modify ONLY files under `./tests/`**.

Allowed:
- `tests/unit_tests/**`
- `tests/integration/**`
- `tests/e2e/**`
- `tests/Makefile` (if Makefile is placed under tests; otherwise create `Makefile` at repo root ONLY if explicitly allowed below)

Forbidden:
- Modifying any file outside `tests/`
- Modifying application code, imports, runtime logic, controllers, orchestrator, etc.
- Adding helper modules outside `tests/`
- “Fixing” implementation to make tests pass

This project is strict TDD:
> Tests describe the system. Implementation changes happen only after failing tests.

**Makefile exception (explicitly allowed):**
You MAY create/modify a root-level `Makefile` (only) to run tests by phase.

---

## READ THE PDF (MANDATORY)

You MUST read the entire assignment PDF before generating or changing tests.

PDF location (in this repo/workdir):
- `/mnt/data/ACTC_-_Homework_3.pdf`

If you cannot read the PDF, you must STOP and ask the student to provide the relevant excerpts.

---

## IMPORTANT: THIS IS NOT REAL KUBERNETES

This project is an educational orchestrator “inspired by Kubernetes”, not Kubernetes.

You MUST NOT assume the existence of:
- CoreDNS / kube-dns
- kube-proxy, iptables-based Service routing
- overlay networks, CNI plugins
- real Kubernetes API coverage beyond what the HW asks
- Deployments, rolling updates, autoscaling, etc. (unless explicitly required)

Only implement/test what the PDF and this file explicitly define.

---

## HW PDF EXCERPTS (VERBATIM, SHORT QUOTES ONLY)

These quotes are copied verbatim from the PDF (short excerpts only). They are **normative**.

### What you’re building (verbatim excerpt)
> “A tool to orchestrate podman containers.”  
> “All in a single process, runnable as uv run orchestrator.py.”  
> “All configuration is done by creating, updating and deleting resources through a REST API…”

### Reconciliation / networking / host exposure (verbatim excerpt)
> “The system continuously (every five seconds or less) reconciles actual resources with the configuration.”  
> “Pods are in the same network and can access each other by name…”  
> “Services are exposed on the host machine at their port…”

### Starting point (verbatim excerpt)
> “You are given a POC called poc.py which orchestrates Python functions in worker threads instead of Podman containers…”  
> “Whether you base your code on the POC or not, any bugs in your submission are your responsibility…”

---

## FULL PDF TEXT INSERTION (STUDENT ACTION REQUIRED)

Because the agent must not guess, the student will paste the most relevant PDF sections below.

Agent instruction:
- Treat the next sections as **authoritative**.
- Do not contradict them.
- If something isn’t specified, prefer the simplest testable behavior that matches demo expectations.

### PDF BLOCK A — “Intro” (PASTE VERBATIM HERE)
> [STUDENT: paste the full relevant paragraph(s) from the PDF here.] - DONE
"
In your final ACTC assignment you will build a simple container orchestration system
implementing the core functionality of Kubernetes.
Though in production we might choose a language like Rust (for correctness, maintainability
and the great ecosystem) or Go (for the strong cloud-specific ecosystem which means most
developers with experience in cloud technologies are fluent), for our prototype we will choose
Python (for speed of implementation vs C, and because you all learned it, which cannot be said
of Rust or Go).
Often, when we embark on a difficult technical project, we start by building a proof of concept
(POC) - just the hard thing without all the stuff around it that makes it usable in the real world -
to ensure that we know what hardships we will encounter and that our design is sound before
we commit to it. Of course, some challenges may not come up in the POC, but the more we
learn and derisk upfront, the better.
To put your time and effort to best didactic use, you won’t start from scratch, you’ll start from a
POC, and you will develop it into a fully usable MVP (minimum viable product, the first version of
a product that someone could actually get value from).
"

### PDF BLOCK B — “What you’re building” (PASTE VERBATIM HERE)
> [STUDENT: paste the full relevant paragraph(s) from the PDF here.] - DONE
"
## What you're building

```
● A tool to orchestrate podman containers.
● Using Python with the uv package manager, with fastapi for the REST API,
subprocess for running podman commands, and pytest for tests (you may need to
read up on these libraries, they have great documentation).
● All in a single process, runnable as uv run orchestrator.py.
● The design is based on Kubernetes, with familiar resources like Pods, Containers,
ReplicaSets, Services (with some simplifications, see “What you’re not building”).
● All configuration is done by creating, updating and deleting resources through a REST
API that is a subset of the Kubernetes REST API.
● For example, these calls create a health-replicaset ReplicaSet that runs 3 replicas
of a container based on the health image, a health Service that listens on port 2000
and load balances between those replicas, and a ping Container based on the ping
image that has a HEALTH_SERVICE environment variable pointing at the health
service:
```

Shell

export ORCHESTRATOR=http://localhost: 3000

curl -X POST
https://$ORCHESTRATOR/api/apps/v1/namespaces/default/replicasets
\
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
},
}
}
}'

curl -X POST https://$ORCHESTRATOR/api/v1/namespaces/default/pods
\
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

curl -X POST https://$ORCHESTRATOR/api/v1/namespaces/default/pods
\
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


Shell

● If we then then ran this, it would cause 2 additional replicas to be created:

curl -X PUT
https://$ORCHESTRATOR/api/apps/v1/namespaces/default/replicasets/
health-replicaset \
-H "Content-Type: application/json" \
-d '{
"apiVersion": "apps/v1",
"kind": "ReplicaSet",
"metadata": {
"name": "health-replicaset"
},
"spec": {
"replicas": 5,
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
},
}
}
}'

● The system continuously (every five seconds or less) reconciles actual resources with
the configuration. If we were to manually delete one of the pods created by the
ReplicaSet (or it were to naturally stop), soon a new one would be created to replace
it.
● Pods are in the same network and can access each other by name, e.g. in our example,
running curl [http://ping:5000](http://ping:5000) from a health container will connect to port 5000
on the ping pod, running curl [http://health:2000](http://health:2000) on the ping ping will connect


```
to port 5000 on a health pod chosen by the load balancer.
● Services are exposed on the host machine at their port (so in our example, running
curl http://localhost:2000/health on the machine running the orchestrator
and containers should connect us to a health pod's port 5000).
● Thread safety - making many API requests in parallel should never corrupt the program
state.
● Tests - the project should contain automated tests that convince you the code does what
you meant it to do.
```
"

### PDF BLOCK C — “What you’re not building” (PASTE VERBATIM HERE)
> [STUDENT: paste the bullet list.] - DONE
"
## What you're not building

```
● Support for more than one Cluster
● Support for more than one Container in a Pod
● Application-layer (e.g. HTTP) load balancing
● Rolling updates and other deployment patterns (the Deployment object)
● ConfigMaps, Secrets, Persistent Volumes
● Resource Limits and Scheduling
● Health checks and readiness probes
● Autoscaling
● Nodes (support for running Containers on a different machine than the one running the
control plane)
● Distributed Control Plane (running control plane components in different processes /
nodes, running multiple copies of control plane components)
● Persistent Control Plane state (saving of state to disk or a DB so that it will survive
restarting the control plane)
```
"

### PDF BLOCK D — “What you’re starting from” (PASTE VERBATIM HERE)
> [STUDENT: paste the submission + run commands.] - DONE
"
The POC is in poc.py, but we also supply demo.sh that shows how to use it.
"

---

## PROJECT STATUS
The student’s codebase is currently **mid Phase 2**.

You MUST:
- Generate tests based on this spec + PDF (not current code).
- Expect many tests to fail initially.
- Avoid coding around implementation bugs by changing tests.
- Prefer tests that reflect what the graders/official scripts are likely to verify.

---

# Phases (Authoritative for Test Planning)

## Phase 1 — Control plane skeleton + basic API + store correctness

### Goal
Have a working orchestrator skeleton with:
- ResourceStore (desired state)
- Controllers (reconcile loops)
- Minimal HTTP API surface to create/list/get/delete resources
- Thread safety
- Smoke tests

### New concepts
- Desired state vs actual state
- Reconciliation
- Idempotent controllers
- Thread-safe store

### Responsibilities
- `ResourceStore`: thread-safe CRUD, query helpers
- Controllers: idempotent reconcile functions
- `orchestrator.py`: wiring only (start controllers + API server)

### Invariants
- No corruption under concurrent API usage
- Controllers are idempotent
- Store is the single source of truth

### Tests required
- Unit: store CRUD + thread safety
- Unit: controller idempotency (no side effects for repeated reconcile)
- Integration: API create/list/get/delete endpoints return correct shapes
- E2E: `/healthz` returns OK and server boots

---

## Phase 2 — Pod execution via Podman runtime (core requirement)

### Goal
Pods result in real running “workloads” via **Podman containers** (not threads).

### New concepts
- Runtime layer backed by `podman` subprocess
- Container lifecycle reconciliation

### Responsibilities
- Runtime:
  - start container for a pod
  - stop container for a pod
  - detect running state
  - idempotent operations
- PodController:
  - reconcile desired pods vs runtime
  - start/stop via runtime, not directly calling podman
- API:
  - pod CRUD stable and thread-safe

### Invariants
- At most one container per Pod
- Idempotent start/stop
- Reconcile loop converges
- No “real Kubernetes” dependencies (no kube-proxy, no CoreDNS)

### Tests required
- Unit: runtime command construction (mock subprocess)
- Integration: creating a Pod triggers runtime start (mock or real depending on tier)
- E2E: at least one Pod runs as a real container (if the HW provides test images/workers)

---

## Phase 3 — Services + cluster networking behavior

### Goal
Enable pod-to-pod and pod-to-service communication consistent with the PDF and demo.

### New concepts
- Service selectors
- Endpoint sets
- Host exposure (Service port on localhost)

### Responsibilities
- ServiceController:
  - compute endpoints based on selectors
  - update routing metadata used by runtime
- Runtime:
  - ensure pods share a podman network
  - ensure name-based reachability (“access each other by name”)
  - ensure Service host exposure behavior (as required by PDF)

### Invariants
- Service endpoints update when pods change
- Selector matching is correct
- Host exposure for Services works (where required)

### Tests required
- Unit: selector matching
- Integration: service endpoints update correctly
- E2E: “curl localhost:<svc_port>/...” hits backing pod (only if PDF/demo requires this)

---

## Phase 4 — ReplicaSets + scaling + self-healing

### Goal
ReplicaSets reconcile to desired replica counts, with updates and selector changes.

### New concepts
- ReplicaSet `spec.replicas`
- ReplicaSet selector/template
- Continuous reconciliation + self-healing

### Responsibilities
- ReplicaSetController:
  - reconcile counts
  - create/delete Pods via ResourceStore
  - handle updates to `replicas` and selector changes
- Runtime + PodController handle actual container convergence

### Invariants
- System converges within reconciliation interval
- Scale up creates additional pods
- Scale down deletes pods created for the RS (see edge-case policy below)

### Tests required
- Unit: RS computes desired delta correctly
- Integration: scaling triggers pod create/delete
- E2E: scaling changes affect running containers

---

## Phase 5 — Robustness polish (grade boosters)

### Goal
Maximize “code review” score and reduce dark corners.

### Examples (optional, do not assume unless PDF implies)
- clearer status reporting
- better error handling
- deterministic naming
- stronger idempotency / cleanup correctness

### Tests required
- Minimal; 1 E2E smoke test is enough

---

# Edge-case policy (from student’s lecturer discussion)
The student explicitly chooses to handle the following edge cases (they matter for grading; tests must not contradict them):

A) **ReplicaSet will NOT “own” Pods** in a strict Kubernetes sense.  
B) **Overlapping selectors** between ReplicaSets must be handled so pods are not incorrectly removed.  
C) ReplicaSet **selector can change over time**; behavior must remain consistent and not delete unrelated pods.

**Important guidance:**
- The lecturer said official tests won’t fail on extreme edge cases, but “better product will be graded better”.
- Therefore: include a dedicated edge-case test file, but keep it isolated.

---

## Dedicated test file: email_edge_cases (MANDATORY)

Create a separate test module:
- `tests/<appropriate-level>/email_edge_cases.py`

This file must only contain tests for:
- overlapping selectors
- selector change over time
- ensuring no incorrect deletions occur

Recommended phase association:
- Run this file only under `make phase4` (or later).

---

# Test suite structure (MANDATORY)

You must create/organize tests into exactly:

1) Unit tests:
- components in isolation
- no HTTP server
- no real podman
- heavy mocking allowed

2) Integration tests:
- FastAPI app + store/controllers wired
- runtime may be mocked
- validate API surfaces + reconciliation interactions

3) End-to-end tests:
- run `uv run orchestrator.py` (real process)
- real HTTP calls (curl/httpx)
- real podman containers where required by the PDF
- 1 e2e test per phase is sufficient

---

# Running tests by phase (MANDATORY)

Create a root `Makefile` with these targets:

- `make phase1`
- `make phase2`
- `make phase3`
- `make phase4`
- `make phase5`
- `make all`

Constraints:
- Each phase target runs only the tests relevant to that phase.
- `make all` runs everything.
- Keep output clear and short.
- Use pytest markers or directory-based selection.

---

# Anti-hallucination rules (strict)

Tests MUST NOT:
- assume DNS features beyond podman name-based container resolution
- assume Kubernetes service VIPs, iptables routing, CoreDNS
- use random sleeps for correctness (only for bounded waiting in e2e)
- require external internet
- require features listed in “What you’re not building”

If you (agent) are unsure:
- Prefer simpler tests tied to the PDF text and demo behavior.
- Ask the student to paste the missing PDF blocks above.

---

# Final instruction to agent
Your job is to generate **grading-aligned tests**.
If a test fails because it assumes non-required behavior, that test is wrong.
Prefer literal PDF alignment over “real Kubernetes correctness”.
