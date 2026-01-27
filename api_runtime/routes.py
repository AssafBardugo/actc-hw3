import random
import socket
from typing import Dict, Any, List, Set
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from actual_state.types import ResourceType
from actual_state.resources import Resource
from actual_state.store import ResourceStore
from api_runtime.podman import PodmanRuntime
from api_runtime.validate_resource import validate_pod, validate_service, validate_replicaset



def register_routes(app: FastAPI, store: ResourceStore, podman: PodmanRuntime) -> None:
    
    # Health check
    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}



    # ================================================================================
    # POD REQUESTS
    # ================================================================================
    @app.post("/api/v1/namespaces/{namespace}/pods", status_code=201)
    def create_pod(namespace: str, body: Dict[str, Any]):
        try:
            resource = validate_pod(namespace, body)
            store.create(resource)
            return resource.to_dict()
        except KeyError as e:
            print(f"pod was not created since 'body' is not compatible with API_POLICY.md. KeyError: {str(e)}")
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


    @app.put("/api/v1/namespaces/{namespace}/pods/{name}")
    def update_pod(namespace: str, name: str, body: Dict[str, Any]):
        try:
            updated_pod = validate_pod(namespace, body)

            store.delete(ResourceType.POD, name, namespace)      # Can fail silently

            store.create(updated_pod)
            return updated_pod.to_dict()
        except KeyError as e:
            print(f"pod was not updated since 'body' is not compatible with API_POLICY.md. KeyError: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))


    @app.delete("/api/v1/namespaces/{namespace}/pods/{name}")
    def delete_pod(namespace: str, name: str):
        return {"deleted": store.delete(ResourceType.POD, name, namespace)}


    @app.post("/api/v1/namespaces/{namespace}/pods/{name}/send")
    def send_to_pod(namespace: str, name: str, message: Dict[str, Any]):
        try:
            pod = store.get(ResourceType.POD, name, namespace)

            podman.send2pod(pod, message.get("data"), timeout=5.0)

            return {"status": "Success", "message": "Message sent"}
        except KeyError as e:
            return {"status": "Fail", "message": f"KeyError: {str(e)}"}
        except TimeoutError:
            raise HTTPException(408, "Request timeout")


    @app.post("/api/v1/namespaces/{namespace}/pods/{name}/call")
    def call_pod(namespace: str, name: str, message: Dict[str, Any]):
        try:
            pod = store.get(ResourceType.POD, name, namespace)

            resp = podman.send2pod(pod, message.get("data"), timeout=30.0)

            return {"status": "Success", "result": resp}
        except KeyError as e:
            return {"status": "Fail", "message": f"KeyError: {str(e)}"}
        except TimeoutError:
            raise HTTPException(408, "Request timeout")


    @app.get("/api/v1/namespaces/{namespace}/pods/{name}/status")
    def pod_status(namespace: str, name: str) -> Dict[str, Any]:
        pod = store.get(ResourceType.POD, name, namespace)
        if pod is None:
            raise HTTPException(status_code=404, detail="Pod not found")
        return pod.to_dict()



    # ================================================================================
    # SERVICE REQUESTS
    # ================================================================================
    @app.post("/api/v1/namespaces/{namespace}/services", status_code=201)
    def create_service(namespace: str, body: Dict[str, Any]):        
        try:
            resource = validate_service(namespace, body)
            store.create(resource)
            return resource.to_dict()
        except KeyError as e:
            print(f"service was not created since 'body' is not compatible with API_POLICY.md. KeyError: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))


    @app.get("/api/v1/namespaces/{namespace}/services/{name}")
    def get_service(namespace: str, name: str):
        service = store.get(ResourceType.SERVICE, name, namespace)
        if service is None:
            raise HTTPException(status_code=404, detail="Service not found")
        return service.to_dict()


    @app.get("/api/v1/namespaces/{namespace}/services")
    def list_services(namespace: str):
        services = store.list_by_namespace_and_kind(ResourceType.SERVICE, namespace)
        return {"items": [svc.to_dict() for svc in services.values()]}


    @app.put("/api/v1/namespaces/{namespace}/services/{name}")
    def update_service(namespace: str, name: str, body: Dict[str, Any]):
        try:
            updated_service = validate_service(namespace, body)

            store.delete(ResourceType.SERVICE, name, namespace)     # Can fail silently

            store.create(updated_service)
            return updated_service.to_dict()
        except KeyError as e:
            print(f"service was not updated since 'body' is not compatible with API_POLICY.md. KeyError: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))


    @app.delete("/api/v1/namespaces/{namespace}/services/{name}")
    def delete_service(namespace: str, name: str):
        return {"deleted": store.delete(ResourceType.SERVICE, name, namespace)}


    @app.post("/api/v1/namespaces/{namespace}/services/{name}/send")
    def send_to_service(namespace: str, name: str, message: Dict[str, Any]):
        try:
            service = store.get(ResourceType.SERVICE, name, namespace)

            if not service:
                raise KeyError("param is not a service")
            
            if service.spec["selector"] == {}:
                return {"status": "Fail", "message": f"{service.key()} is unusable since it dosen't have a selector"}

            pod = podman.load_balancer(namespace, service.spec["selector"])

            podman.send2pod(pod, message.get("data"), timeout=5.0)

            return {"status": "Success", "message": "Message sent"}
        except KeyError as e:
            raise HTTPException(409, str(e))
        except TimeoutError:
            raise HTTPException(408, "Request timeout")


    @app.post("/api/v1/namespaces/{namespace}/services/{name}/call")
    def call_to_service(namespace: str, name: str, message: Dict[str, Any]):
        try:
            service = store.get(ResourceType.SERVICE, name, namespace)

            if not service:
                raise KeyError("param is not a service")
            
            if service.spec["selector"] == {}:
                return {"status": "Fail", "message": f"{service.key()} is unusable since it dosen't have a selector"}

            pod = podman.load_balancer(namespace, service.spec["selector"])

            resp = podman.send2pod(pod, message.get("data"), timeout=30.0)

            return {"status": "Success", "result": resp}
        except KeyError as e:
            raise HTTPException(409, str(e))
        except TimeoutError:
            raise HTTPException(408, "Request timeout")
    

    @app.get("/api/v1/namespaces/{namespace}/services/{name}/endpoints")
    def list_endpoints(namespace: str, name: str) -> Set[str]:
        return podman.get_services_endpoints(namespace, name)



    # ================================================================================
    # REPLICASET REQUESTS
    # ================================================================================
    @app.post("/api/apps/v1/namespaces/{namespace}/replicasets", status_code=201)
    def create_replicaset(namespace: str, body: Dict[str, Any]):
        try:
            resource = validate_replicaset(namespace, body)
            store.create(resource)
            return resource.to_dict()
        except KeyError as e:
            print(f"replicaset was not created since 'body' is not compatible with API_POLICY.md. KeyError: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))


    @app.get("/api/apps/v1/namespaces/{namespace}/replicasets")
    def list_replicasets(namespace: str):
        rss = store.list_by_namespace_and_kind(ResourceType.REPLICASET, namespace)
        return {"items": [rs.to_dict() for rs in rss.values()]}


    @app.get("/api/apps/v1/namespaces/{namespace}/replicasets/{name}")
    def get_replicaset(namespace: str, name: str):
        rs = store.get(ResourceType.REPLICASET, name, namespace)
        if rs is None:
            raise HTTPException(status_code=404, detail="ReplicaSet not found")
        return rs.to_dict()


    @app.put("/api/apps/v1/namespaces/{namespace}/replicasets/{name}")
    def update_replicaset(namespace: str, name: str, body: Dict[str, Any]):
        try:
            updated_rs = validate_replicaset(namespace, body)

            old_rs = store.get(ResourceType.REPLICASET, name, namespace)

            if old_rs:     # Can fail silently
                for i in range(old_rs.spec["replicas"]):
                    store.delete(ResourceType.POD, f"own_by_{name}_{i}", namespace)
                store.delete(ResourceType.REPLICASET, name, namespace)

            store.create(updated_rs)
            return updated_rs.to_dict()
        except KeyError as e:
            print(f"replicaset was not updated since 'body' is not compatible with API_POLICY.md. KeyError: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))


    @app.delete("/api/apps/v1/namespaces/{namespace}/replicasets/{name}")
    def delete_replicaset(namespace: str, name: str):
        to_delete = store.get(ResourceType.REPLICASET, name, namespace)
        if to_delete is None:
            return {"deleted": False}

        for i in range(to_delete.spec["replicas"]):
            store.delete(ResourceType.POD, f"own_by_{name}_{i}", namespace)
        store.delete(ResourceType.REPLICASET, name, namespace)
        return {"deleted": True}



    # ================================================================================
    # HOST -> SERVICE PROXY
    # ================================================================================
    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def host_proxy(path: str, request: Request):
        try:
            local_port = request.url.port
            if local_port is None:
                raise HTTPException(400, "Missing destination port")

            # Find service with matching port
            services = store.list_by_kind(ResourceType.SERVICE)
            matched_services: List[Resource] = []

            for svc_map in services.values():
                for svc in svc_map.values():
                    if svc.spec["ports"][0]["port"] == local_port:
                        matched_services.append(svc)

            if not matched_services:
                raise HTTPException(404, "No Service bound to this port")

            chosen_service = random.choice(matched_services)

            body = await request.body()
            if body:
                try:
                    value = await request.json()
                except Exception:
                    value = body.decode("utf-8", errors="replace")
            else:
                value = None

            pod = podman.load_balancer(
                chosen_service.namespace,
                chosen_service.spec["selector"]
            )

            if request.method == "GET":
                import requests
                result = requests.get(
                    f"http://localhost:{pod.status['hostPort']}/",
                    timeout=30
                ).text
            else:
                result = podman.send2pod(pod, value, 30)

            return Response(content=result)

        except KeyError as e:
            raise HTTPException(404, str(e))
