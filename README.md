# ACTC Homework 3

how to run?
./run_my_test.sh


supported api requests:

# ================================================================================
# 0) NON-K8S / infra
# ================================================================================

GET  /healthz 

# ================================================================================
# 1) POD REQUESTS 
# ================================================================================

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

# ======= EXEC / RPC-like calls =======
# Call a function/command inside the pod/container (sync request/response)
POST    /api/v1/namespaces/{namespace}/pods/{podName}/call 

# Send an async message to the pod/container (fire-and-forget over HTTP)
POST    /api/v1/namespaces/{namespace}/pods/{podName}/send 

# ======= Logs / status =======
# GET     /api/v1/namespaces/{namespace}/pods/{podName}/logs
GET     /api/v1/namespaces/{namespace}/pods/{podName}/status 


# ================================================================================
# 2) SERVICE REQUESTS
# ================================================================================

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

# ======= EXEC / RPC-like calls =======
# Call a function/command inside the service (sync request/response)
POST    /api/v1/namespaces/{namespace}/services/{serviceName}/call 

# Send an async message to the service (fire-and-forget over HTTP)
POST    /api/v1/namespaces/{namespace}/services/{serviceName}/send 

# ======= Endpoints / status =======
# Service endpoints
GET     /api/v1/namespaces/{namespace}/services/{serviceName}/endpoints 

# Host proxy (Catch-all): http://localhost:{service.port}/{path}
GET     /{path:path} 
POST    /{path:path} 


# ================================================================================
# 3) REPLICASET REQUESTS
# ================================================================================

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

