# ACTC HW3 – Option C (Controlled Rewrite) Work Plan

Goal: Build the ACTC HW3 orchestrator as an MVP **by evolving the provided POC**:
- Keep the high-level architecture (API + resource store + controllers + reconciliation)
- Replace execution model (threads → podman containers)
- Add missing K8s-like resources (ReplicaSet, Service networking)
- End with code you **understand and own**

> **Total estimate:** ~32–44 hours (depends on Podman/networking friction)


===============================================================================

# Phase 1 – Make the POC *Your* Code (⏱ 6–10 hours)

**Definition of done for Phase 1:**  
You can explain on a whiteboard (or in a doc) the full flow:
**REST API → ResourceStore → Controllers → reconcile loop → runtime actions.**

## 1.1 Baseline run + demo mapping (⏱ 1–2h)
- [ ] Run orchestrator + demo end-to-end
  - Run:
    - `uv run orchestrator.py`
    - `./demo.sh`
  - Confirm orchestrator answers `/healthz` and demo completes.
- [ ] Map each `demo.sh` REST call to the matching FastAPI endpoint in `orchestrator.py`
  - Write down (in notes) which endpoint handles:
    - Pod create/list/get/update/delete
    - Service create/list/get/delete
    - (Any extra demo endpoints like `/send`)

**Why:** This anchors you in the expected API behavior and reduces confusion later.

## 1.2 Read + annotate architecture (⏱ 2–3h)
- [ ] Read `orchestrator.py` top-to-bottom once without editing.
- [ ] Second pass: add **your own** short comments (why it exists, not what it does) in:
  - ResourceStore / state management
  - Controller base loop / reconcile scheduling
  - PodController responsibilities
  - ServiceController responsibilities

**Why:** Your brain needs “ownership language” to feel grounded.

## 1.3 Draw the system diagram (mandatory) (⏱ 1h)
- [ ] Create a diagram (paper / draw.io) showing:
  - API layer (FastAPI)
  - ResourceStore (in-memory desired state)
  - Controllers (PodController, ServiceController)
  - Reconcile loop timing (≤5s; POC uses ~1s)
  - Runtime backend (currently threads; later Podman)

**Why:** If you can’t draw it, you’ll suffer later when you add ReplicaSets + services.

## 1.4 Refactor for clarity (no new features yet) (⏱ 2–4h)
- [ ] Rename confusing variables/functions (small, safe renames).
- [ ] Add consistent naming for:
  - “desired state” vs “actual state”
  - “pod resource” vs “running container”
- [ ] Add lightweight logging that helps you reason about reconcile decisions.

**Why:** This reduces “foreign code pain” and makes later changes safer.


===============================================================================

# Phase 2 – Replace Execution Model (Threads → Podman) (⏱ 10–16 hours)

**Definition of done for Phase 2:**  
Creating a Pod resource causes a **real Podman container** to run, and deleting the Pod
stops/removes it. Reconciliation restarts containers if they die.

> Keep the architecture. Replace ONLY the “runtime” implementation.

## 2.1 Decide runtime contract (⏱ 1h)
- [ ] Create a tiny abstraction (even just a class/module) for container runtime:
  - `start_pod(pod_spec) -> container_id/name`
  - `stop_pod(container_id/name)`
  - `is_running(container_id/name) -> bool`
  - (optional) `logs(container_id/name)`

**Why:** Prevents Podman logic from spreading into controllers.

## 2.2 Minimal Podman “run/stop/rm” implementation (⏱ 3–5h)
- [ ] Implement container start with `subprocess`:
  - `podman run -d --name <pod-name> ... <image>`
  - pass env vars from the Pod spec
- [ ] Implement stop/remove:
  - `podman stop <name>` (ignore if already stopped)
  - `podman rm <name>` (ignore if missing)
- [ ] Add robust error handling:
  - capture stdout/stderr
  - raise or log meaningful errors

**Why:** This is the MVP “container runtime”.

## 2.3 Integrate runtime into PodController reconcile (⏱ 3–5h)
- [ ] Replace “thread start” with “podman start”
- [ ] Replace “thread stop” with “podman stop/rm”
- [ ] Ensure reconcile compares:
  - desired pods from ResourceStore
  - actual running containers from Podman (or cached state + checks)

**Why:** This is the heart of Kubernetes: reconciliation against reality.

## 2.4 Self-healing behavior (⏱ 2–3h)
- [ ] If a container exits or is manually removed:
  - reconcile should re-create it (because Pod resource still exists)
- [ ] Confirm behavior manually:
  - create pod
  - `podman rm -f <pod>`
  - wait ≤5s → pod returns

**Why:** This is a key explicit requirement (“reconciles every five seconds or less”).

## 2.5 Smoke tests (manual, for now) (⏱ 1–2h)
- [ ] Manual validation checklist:
  - Create Pod → container appears in `podman ps`
  - Delete Pod → container disappears
  - Update Pod → defined behavior (either restart, or reject changes; pick and document)
  - Orchestrator restart → state resets (allowed; no persistence required)

**Why:** You need stability before adding ReplicaSets and Services.


===============================================================================

# Phase 3 – ReplicaSet Controller (⏱ 7–11 hours)

**Definition of done for Phase 3:**  
ReplicaSet CRUD exists and scaling works: changing `.spec.replicas` creates/deletes Pods,
and losing a pod triggers replacement.

## 3.1 Define ReplicaSet resource schema + storage (⏱ 1–2h)
- [ ] Add a ReplicaSet resource type in your in-memory store:
  - `metadata.name`
  - `spec.replicas` (int)
  - `spec.selector` (labels)
  - `spec.template` (pod template with metadata+spec)
- [ ] Decide label strategy:
  - pods created by RS must get labels that match RS selector

**Why:** Without correct labels, Service selection won’t work later.

## 3.2 Add ReplicaSet REST endpoints (⏱ 2–3h)
- [ ] Implement endpoints (matching assignment example paths):
  - POST `/api/apps/v1/namespaces/{ns}/replicasets`
  - GET list + GET by name
  - PUT update by name (scaling)
  - DELETE by name
- [ ] Validate input fields minimally (reject missing name/replicas/template)

**Why:** The graders will hit these endpoints.

## 3.3 Implement ReplicaSetController reconcile logic (⏱ 3–5h)
- [ ] Every reconcile tick:
  - for each ReplicaSet:
    - list Pods in store that match selector AND are owned by this ReplicaSet
    - if count < replicas: create missing Pods from template
    - if count > replicas: delete extra Pods
- [ ] Pod naming strategy for replicas:
  - deterministic names: `<rs-name>-<index or random suffix>`
  - must avoid collisions

**Why:** This is classic “desired replicas” reconciliation.

## 3.4 Ownership + cleanup (⏱ 1h)
- [ ] Add owner marker to pods created by RS (e.g. `metadata.owner: <rs-name>` or labels)
- [ ] On RS deletion:
  - delete its owned pods (recommended)

**Why:** Avoid leaking pods and confusing the grader/tests.


===============================================================================

# Phase 4 – Networking & Services (⏱ 9–13 hours)

**Definition of done for Phase 4:**  
- Pods can reach each other by name on a shared network.
- Service exposes host port and forwards/load-balances to matching pods.

## 4.1 Create shared Podman network for all pods (⏱ 1–2h)
- [ ] On orchestrator startup:
  - ensure a network exists (e.g. `actc-net`)
- [ ] When starting a pod container:
  - attach to that network
  - set container name to pod name (DNS by name)

**Why:** Requirement: pods in same network and can access each other by name.

## 4.2 Verify pod-to-pod DNS + connectivity (⏱ 1–2h)
- [ ] Create two simple pods (or use provided images if they exist)
- [ ] Exec into one and curl the other by name:
  - `curl http://<other-pod>:<port>`
- [ ] Document what works (DNS, port reachability)

**Why:** If this fails, Services will be impossible.

## 4.3 Service backend discovery (selector → pods) (⏱ 1–2h)
- [ ] Implement a function:
  - `get_service_backends(service) -> list[pod]`
  - based on selector labels
- [ ] Ensure it updates dynamically as pods come/go (ReplicaSet scaling)

**Why:** Services are selectors over pods.

## 4.4 Expose Service on host + forward to backends (⏱ 4–6h)
Pick a simple approach (don’t overbuild):
- Option A (recommended): **Python TCP proxy** per Service:
  - orchestrator listens on `service.spec.ports[0].port` on localhost
  - each incoming connection is forwarded to one backend pod IP:targetPort
  - use round-robin or random backend selection
- [ ] Implement start/stop of listener threads per Service in ServiceController reconcile.
- [ ] Make sure:
  - Service delete stops the listener and frees host port
  - If backends change, new connections use updated backend list

**Why:** Requirement: `curl http://localhost:<svc-port>/...` works.

## 4.5 End-to-end scenario test (⏱ 1–2h)
Reproduce the assignment story:
- [ ] Create ReplicaSet of `health` with N replicas
- [ ] Create Service selecting `app=health`
- [ ] Create `ping` pod that calls `health-service:<port>`
- [ ] Validate:
  - service works from host (`curl localhost:<port>`)
  - service works from inside cluster by name (`curl health-service:<port>` if you implement service DNS, or ensure ping talks to service host/alias as required by your design)

**Why:** This is the assignment’s “happy path”.


===============================================================================

# Suggested timeline (practical)

- **Day 1–2:** Phase 1 (understand + refactor)
- **Day 3–5:** Phase 2 (Podman runtime)
- **Day 6–7:** Phase 3 (ReplicaSet)
- **Day 8–10:** Phase 4 (Networking + Services)

> If you’re short on time, Phase 4 is the most uncertain (network + forwarding),
> so start it earlier than you think.


===============================================================================

# Notes for your mindset (important)

- If you feel lost: **stop and redraw the architecture**.
- Keep changes incremental:
  - after every TODO: run a minimal smoke test
- Don’t chase “perfect Kubernetes”.
  - You’re building a small MVP with explicit constraints.

Good luck — this is the correct strategy for someone thorough who wants ownership.
