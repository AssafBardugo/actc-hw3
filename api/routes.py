"""
API Routes (HTTP Layer)

Responsibility:
- Define REST API endpoints (Pods, Services, ReplicaSets).
- Validate incoming HTTP requests.
- Translate JSON payloads into internal Resource objects.
- Call ResourceStore CRUD operations.
- Return appropriate HTTP responses and status codes.

Important:
- MUST NOT start or stop workers.
- MUST NOT run reconciliation logic.
- MUST NOT contain loops or background threads.
- MUST be safe to call concurrently.
"""
from typing import Dict, Any
from fastapi import FastAPI, HTTPException

from core.types import ResourceType
from core.resources import Resource
from core.store import ResourceStore


def register_routes(app: FastAPI, store: ResourceStore) -> None:
    
    # Health check
    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}


    # pods endpoint
    @app.post("/api/v1/namespaces/{namespace}/pods", status_code=201)
    def create_pod(namespace: str, body: Dict[str, Any]):
        try:
            metadata = body.get("metadata", {})
            spec = body.get("spec", {})

            name = metadata.get("name")
            if not name:
                raise HTTPException(status_code=400, detail="Pod name missing")

            resource = Resource(
                kind=ResourceType.POD,
                name=name,
                namespace=namespace,
                metadata=metadata,
                spec=spec,
            )
            store.create(resource)
            return resource.to_dict()

        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @app.get("/api/v1/namespaces/{namespace}/pods")
    def list_pods(namespace: str):
        pods = store.list_by_namespace_and_kind(ResourceType.POD, namespace)
        return {"items": [pod.to_dict() for pod in pods.values()]}
    
    @app.get("/api/v1/namespaces/{namespace}/pods/{name}")
    def get_pod(namespace: str, name: str):
        pod = store.get(ResourceType.POD, name, namespace)
        if pod is None:
            raise HTTPException(status_code=404, detail="Pod not found")
        return pod.to_dict()

    @app.delete("/api/v1/namespaces/{namespace}/pods/{name}")
    def delete_pod(namespace: str, name: str):
        if not store.delete(ResourceType.POD, name, namespace):
            raise HTTPException(status_code=404, detail="Pod not found")
        return {"deleted": True}


    # replica-set endpoint
    @app.post("/api/v1/namespaces/{namespace}/replicasets", status_code=201)
    def create_replicaset(namespace: str, body: Dict[str, Any]):
        try:
            metadata = body.get("metadata", {})
            spec = body.get("spec", {})

            name = metadata.get("name")
            if not name:
                raise HTTPException(status_code=400, detail="ReplicaSet name missing")

            resource = Resource(
                kind=ResourceType.REPLICASET,
                name=name,
                namespace=namespace,
                metadata=metadata,
                spec=spec,
            )
            store.create(resource)
            return resource.to_dict()

        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @app.get("/api/v1/namespaces/{namespace}/replicasets")
    def list_replicasets(namespace: str):
        rss = store.list_by_namespace_and_kind(ResourceType.REPLICASET, namespace)
        return {"items": [rs.to_dict() for rs in rss.values()]}

    @app.delete("/api/v1/namespaces/{namespace}/replicasets/{name}")
    def delete_replicaset(namespace: str, name: str):
        if not store.delete(ResourceType.REPLICASET, name, namespace):
            raise HTTPException(status_code=404, detail="ReplicaSet not found")
        return {"deleted": True}
    

    # service endpoint
    @app.post("/api/v1/namespaces/{namespace}/services", status_code=201)
    def create_service(namespace: str, body: Dict[str, Any]):
        try:
            metadata = body.get("metadata", {})
            spec = body.get("spec", {})

            name = metadata.get("name")
            if not name:
                raise HTTPException(status_code=400, detail="Service name missing")

            resource = Resource(
                kind=ResourceType.SERVICE,
                name=name,
                namespace=namespace,
                metadata=metadata,
                spec=spec,
            )
            store.create(resource)
            return resource.to_dict()

        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @app.get("/api/v1/namespaces/{namespace}/services")
    def list_services(namespace: str):
        services = store.list_by_namespace_and_kind(ResourceType.SERVICE, namespace)
        return {"items": [svc.to_dict() for svc in services.values()]}

    @app.delete("/api/v1/namespaces/{namespace}/services/{name}")
    def delete_service(namespace: str, name: str):
        if not store.delete(ResourceType.SERVICE, name, namespace):
            raise HTTPException(status_code=404, detail="Service not found")
        return {"deleted": True}
