# Orchestrator REST API endpoint examples (K8s-style subset)

# > This list is a practical "full set" of endpoints that a single-process FastAPI + Podman
# > orchestrator typically exposes for the supported resources: Pods, Services, ReplicaSets.
# > It is aligned with the constraints you listed (NO Deployments, NO ConfigMaps, etc.).
# >
# > Conventions:
# > - Base URL example: https://localhost:3000
# > - All endpoints below are shown as PATHS only (no scheme/host).
# > - Namespaces: the system should accept any namespace string; commonly "default".
# > - Methods shown are the ones you typically implement for this kind of project.
# > - If your implementation does not support WATCH or PATCH, ignore those.

### CRUD -> API -- ###
# POST      -> create
# GET       -> list/get
# PUT       -> replace/update full object
# DELETE    -> remove

================================================================================
0) NON-K8S / infra
================================================================================

GET  /healthz

# (optional) metrics/debug
GET  /metrics
GET  /debug/state

================================================================================
1) POD REQUESTS
================================================================================

# List pods in namespace
GET     /api/v1/namespaces/{namespace}/pods
# Create pod in namespace
POST    /api/v1/namespaces/{namespace}/pods

# Get one pod
GET     /api/v1/namespaces/{namespace}/pods/{podName}
# Replace/update pod (e.g., change env/image/ports -> reconcile)
PUT     /api/v1/namespaces/{namespace}/pods/{podName}
# Delete pod
DELETE  /api/v1/namespaces/{namespace}/pods/{podName}

# ======= EXEC / RPC-like calls (NOT real K8s, but common in this homework) =======
# Call a function/command inside the pod/container (sync request/response)
POST    /api/v1/namespaces/{namespace}/pods/{podName}/call

# Send an async message to the pod/container (fire-and-forget / enqueue)
POST    /api/v1/namespaces/{namespace}/pods/{podName}/send

# Read received messages (polling)
GET     /api/v1/namespaces/{namespace}/pods/{podName}/queue
# Clear queue (optional)
DELETE  /api/v1/namespaces/{namespace}/pods/{podName}/queue

# ======= Logs / status =======
GET     /api/v1/namespaces/{namespace}/pods/{podName}/logs
GET     /api/v1/namespaces/{namespace}/pods/{podName}/status


================================================================================
2) SERVICE REQUESTS
================================================================================

# List services in namespace
GET     /api/v1/namespaces/{namespace}/services
# Create service in namespace
POST    /api/v1/namespaces/{namespace}/services

# Get one service
GET     /api/v1/namespaces/{namespace}/services/{serviceName}
# Replace/update service (e.g., selector/ports)
PUT     /api/v1/namespaces/{namespace}/services/{serviceName}
# Delete service
DELETE  /api/v1/namespaces/{namespace}/services/{serviceName}

# Service status / endpoints (which pods are selected)
GET     /api/v1/namespaces/{namespace}/services/{serviceName}/status
GET     /api/v1/namespaces/{namespace}/services/{serviceName}/endpoints

# (optional) "proxy" request through service LB (NOT real K8s; useful for tests)
POST    /api/v1/namespaces/{namespace}/services/{serviceName}/proxy
GET     /api/v1/namespaces/{namespace}/services/{serviceName}/proxy


================================================================================
3) REPLICASET REQUESTS
================================================================================

# List replicasets in namespace
GET     /api/apps/v1/namespaces/{namespace}/replicasets
# Create replicaset in namespace
POST    /api/apps/v1/namespaces/{namespace}/replicasets

# Get one replicaset
GET     /api/apps/v1/namespaces/{namespace}/replicasets/{rsName}
# Replace/update replicaset (mainly: spec.replicas)
PUT     /api/apps/v1/namespaces/{namespace}/replicasets/{rsName}
# Delete replicaset
DELETE  /api/apps/v1/namespaces/{namespace}/replicasets/{rsName}

# Replicaset status / controlled pods
GET     /api/apps/v1/namespaces/{namespace}/replicasets/{rsName}/status
GET     /api/apps/v1/namespaces/{namespace}/replicasets/{rsName}/pods


================================================================================
4) POSSIBLE MORE REQUESTS (OUTSIDE POD/SVC/RS)
================================================================================

# Namespaces (optional in simplified orchestrator; often supported as "string only")
GET     /api/v1/namespaces
POST    /api/v1/namespaces
GET     /api/v1/namespaces/{namespace}
DELETE  /api/v1/namespaces/{namespace}

# Events (optional; helps tests/debug)
GET     /api/v1/namespaces/{namespace}/events

# System-level reconciliation control (optional)
POST    /api/v1/reconcile
GET     /api/v1/reconcile/status

# Version (optional)
GET     /version
