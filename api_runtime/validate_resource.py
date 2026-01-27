import random
import socket
from typing import Dict, Any, List, Set
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from actual_state.types import ResourceType, PodStatus
from actual_state.resources import Resource
from actual_state.store import ResourceStore
from api_runtime.podman import PodmanRuntime

DEFAULT_CONTAINER_PORT = 5000


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

    if "hostPort" not in status:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            status["hostPort"] =  int(sock.getsockname()[1])

    if "containerPort" not in status:
        status["containerPort"] = DEFAULT_CONTAINER_PORT

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

    if "replicas" in spec:
        if spec["replicas"] < 1:
            raise KeyError("Service.spec.replicas has to be positive")
    else:
        spec["replicas"] = 1

    if "selector" not in spec or spec["selector"] == {}:
        raise KeyError("selector is missing")
    
    if "template" not in spec or spec["template"] == {}:
        raise KeyError("template is missing")
    template = spec["template"]

    # spec.template.metadata.labels is default to be spec.selector
    if "metadata" not in template or template["metadata"] == {}:
        spec["template"]["metadata"] = {"labels": spec["selector"].copy()}
    
    elif "labels" not in template["metadata"]:
        # replace
        # "template": {
		# 	"metadata": {
		# 		"app": "web"
		# 	}
		# }
        # to be 
        # "template": {
		# 	"metadata": {
		# 		"labels": {
		# 			"app": "web"
		# 		}
		# 	}
		# }
        labels = template["metadata"].copy()
        spec["template"]["metadata"] = {"labels": labels}

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
