from typing import Dict, Any, Tuple, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from actual_state.types import ResourceType, PodStatus
from actual_state.resources import Resource
from actual_state.store import ResourceStore
from api_runtime.podman import PodmanRuntime

CONTAINER_PORT = 5000


def validate_pod(namespace: str, body: Dict[str, Any]) -> Resource:

    if "kind" not in body or body["kind"] != "Pod":
        raise KeyError("kind is missing or incorrect")

    if "metadata" not in body or "name" not in body["metadata"]:
        raise KeyError("Pod name missing")
    metadata = body["metadata"]
    name = metadata["name"]

    if "labels" not in metadata:
        metadata["labels"] = {}

    if "spec" not in body:
        raise KeyError("Pod.spec is missing")
    spec = body["spec"]

    if "containers" not in spec or not isinstance(spec["containers"], List) or len(spec["containers"]) != 1:
        raise KeyError("pod must have exactly one container")

    container = spec["containers"][0]
    if "image" not in container:
        raise KeyError("Pod.spec.containers[0] is missing image to run")
    
    if "name" not in container:
        spec["containers"][0]["name"] = f'{container["image"]}-name'

    status = body["status"] if "status" in body else {}

    if "phase" not in status or status["phase"] not in PodStatus:
        status["phase"] = PodStatus.PENDING
    
    status["containerPort"] = CONTAINER_PORT

    return Resource(ResourceType.POD, name, namespace, metadata, spec, status)


def validate_service(namespace: str, body: Dict[str, Any]) -> Resource:

    if "kind" not in body or body["kind"] != "Service":
        raise KeyError("kind is missing or incorrect")
    
    if "metadata" not in body or "name" not in body["metadata"]:
        raise KeyError("Service name missing")
    metadata = body["metadata"]
    name = metadata["name"]

    if "spec" not in body:
        raise KeyError("Service.spec is missing")
    spec = body["spec"]

    if "type" not in spec:
        spec["type"] = "ClusterIP"

    # if "selector" is not in spec, we accept it. but the service will be unusable.
    if "selector" not in spec:
        spec["selector"] = {}

    if "ports" not in spec or not isinstance(spec["ports"], List):
        raise KeyError("Service.spec.ports is missing or not an array")

    if "port" not in spec["ports"][0] or not isinstance(spec["ports"][0]["port"], int):
        raise KeyError("Service.spec.ports[0].port is missing")

    if "targetPort" not in spec["ports"][0]:
        spec["ports"][0]["targetPort"] = spec["ports"][0]["port"]   # Default for missing targetPort

    return Resource(ResourceType.SERVICE, name, namespace, metadata, spec)


def validate_replicaset(namespace: str, body: Dict[str, Any]) -> Resource:

    if "kind" not in body or body["kind"] != "ReplicaSet":
        raise KeyError("kind is missing or incorrect")

    if "metadata" not in body or "name" not in body["metadata"]:
        raise KeyError("Service name missing")
    metadata = body["metadata"]
    name = metadata["name"]

    if "spec" not in body:
        raise KeyError("Service.spec is missing")
    spec = body["spec"]

    if "replicas" not in spec:
        spec["replicas"] = 1

    if "selector" not in spec or spec["selector"] == {}:
        raise KeyError("selector is missing")
    
    if "template" not in spec or spec["template"] == {}:
        raise KeyError("template is missing")
    template = spec["template"]

    # spec.template.metadata.labels is default to be spec.selector
    if "metadata" not in template or "labels" not in template["metadata"]:
        spec["template"]["metadata"] = {"labels": spec["selector"]}

    if "spec" not in template:
        raise KeyError("spec.template.spec is missing")
    tmp_spec = template["spec"]

    if "containers" not in tmp_spec or not isinstance(tmp_spec["containers"], List) or len(tmp_spec["containers"]) != 1:
        raise KeyError("replicaset must have exactly one container inside the pod")
    
    container = tmp_spec["containers"][0]
    if "image" not in container:
        raise KeyError("containers[0] is missing image to run")

    if "name" not in container:
        spec["template"]["spec"]["containers"][0]["name"] = f'{container["image"]}-name'

    return Resource(ResourceType.REPLICASET, name, namespace, metadata, spec)



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
            raise HTTPException(status_code=400, detail=str(e))
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
            store.update(updated_pod)
            return updated_pod.to_dict()
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))
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
            raise HTTPException(409, str(e))
        except TimeoutError:
            raise HTTPException(408, "Request timeout")


    @app.post("/api/v1/namespaces/{namespace}/pods/{name}/call")
    def call_pod(namespace: str, name: str, message: Dict[str, Any]):
        try:
            pod = store.get(ResourceType.POD, name, namespace)

            resp = podman.send2pod(pod, message.get("data"), timeout=30.0)

            return {"status": "Success", "result": resp}
        except KeyError as e:
            raise HTTPException(409, str(e))
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
            raise HTTPException(status_code=400, detail=str(e))
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
            store.update(updated_service)
            return updated_service.to_dict()
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))
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
                raise ValueError(f"{service.key()} is unusable since it dosen't have a selector")

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
                raise ValueError(f"{service.key()} is unusable since it dosen't have a selector")

            pod = podman.load_balancer(namespace, service.spec["selector"])

            resp = podman.send2pod(pod, message.get("data"), timeout=30.0)

            return {"status": "Success", "result": resp}
        except KeyError as e:
            raise HTTPException(409, str(e))
        except TimeoutError:
            raise HTTPException(408, "Request timeout")
    

    @app.get("/api/v1/namespaces/{namespace}/services/{name}/endpoints")
    def list_endpoints(namespace: str, name: str) -> Dict[str, Any]:
        raise NotImplementedError



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
            raise HTTPException(status_code=400, detail=str(e))
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
            store.update(updated_rs)
            return updated_rs.to_dict()
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))


    @app.delete("/api/apps/v1/namespaces/{namespace}/replicasets/{name}")
    def delete_replicaset(namespace: str, name: str):
        if not store.delete(ResourceType.REPLICASET, name, namespace):
            raise HTTPException(status_code=404, detail="ReplicaSet not found")
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
            matched_service = None
            matched_namespace = None

            for ns, svc_map in services.items():
                for svc in svc_map.values():
                    ports = svc.spec.get("ports", [])
                    if ports and ports[0].get("port") == local_port:
                        matched_service = svc
                        matched_namespace = ns
                        break
                if matched_service is not None:
                    break

            if matched_service is None:
                raise HTTPException(404, "No Service bound to this port")

            body = await request.body()
            if body:
                try:
                    payload = await request.json()
                except Exception:
                    payload = body.decode("utf-8", errors="replace")
            else:
                payload = {"path": path}

            result = podman.route2service(
                matched_namespace,
                matched_service.name,
                local_port,
                payload,
                expect_response=True,
            )

            return Response(content=str(result))

        except KeyError as e:
            raise HTTPException(404, str(e))
