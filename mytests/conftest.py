import os
from typing import Callable, Dict, Optional, Any
import pytest

from actual_state.resources import Resource
from actual_state.store import ResourceStore
from actual_state.types import ResourceType
from api_runtime.podman import PodmanRuntime


class RecordingRuntime:
    """Simple runtime stub that records start/stop calls without side effects."""

    def __init__(self):
        self.started: list[Resource] = []
        self.stopped: list[Resource] = []
        self._running: dict[tuple[str, str], Resource] = {}

    def start_pod(self, pod: Resource) -> None:
        self.started.append(pod)
        self._running[(pod.namespace, pod.name)] = pod

    def stop_pod(self, pod: Resource) -> None:
        self.stopped.append(pod)
        self._running.pop((pod.namespace, pod.name), None)

    def list_running_pods(self):
        return list(self._running.values())


@pytest.fixture
def runtime_stub() -> RecordingRuntime:
    return RecordingRuntime()


@pytest.fixture
def resource_store() -> ResourceStore:
    return ResourceStore()


@pytest.fixture
def make_pod() -> Callable[..., Resource]:
    def _make(
        name: str,
        namespace: str = "default",
        labels: Optional[Dict[str, str]] = None,
        image: str = "alpine:latest",
        env: Optional[Dict[str, str]] = None,
        spec: Optional[Dict[str, Any]] = None,
        status: Dict[str, Any] = {}
    ) -> Resource:

        metadata: Dict[str, object] = {"name": name, "namespace": namespace}
        if labels:
            metadata["labels"] = labels
        extra_spec = spec
        if isinstance(image, dict) and spec is None and env is None:
            extra_spec = image
            image = "alpine:latest"

        container_spec: Dict[str, object] = {"name": name, "image": image}
        if env:
            container_spec["env"] = env
        spec = {"containers": [container_spec]}
        if extra_spec:
            spec.update(extra_spec)
        return Resource(
            kind=ResourceType.POD,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec,
            status=status
        )
    return _make


@pytest.fixture
def make_service() -> Callable[..., Resource]:
    def _make(
        name: str,
        namespace: str = "default",
        selector: Optional[Dict[str, str]] = None,
        ports: Optional[list[dict]] = None,
        service_type: str = "default_type",
        status: Dict[str, Any] = {}
    ) -> Resource:

        metadata: Dict[str, object] = {"name": name, "namespace": namespace}
        spec = {
            "type": service_type,
            "selector": selector or {},
            "ports": ports
            or [
                {
                    "protocol": "TCP",
                    "port": 80,
                    "targetPort": 8080,
                }
            ]
        }
        return Resource(
            kind=ResourceType.SERVICE,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec,
            status=status
        )
    return _make


@pytest.fixture
def make_replicaset() -> Callable[..., Resource]:
    def _make(
        name: str,
        namespace: str = "default",
        replicas: int = 1,
        selector: Dict[str, str] = {},
        template_labels: Optional[Dict[str, str]] = None,
        pod_name: str = "pod_name",
        pod_image: str = "pod_image",
        status: Dict[str, Any] = {}
    ) -> Resource:

        metadata: Dict[str, object] = {"name": name, "namespace": namespace}
        template = {
            "metadata": {
                "labels": template_labels or selector
            },
            "spec": {
                "containers": [
                    {"name": pod_name, "image": pod_image}
                ]
            }
        }
        spec = {
            "replicas": replicas,
            "selector": selector,
            "template": template
        }
        return Resource(
            kind=ResourceType.REPLICASET,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec,
            status=status
        )
    return _make


@pytest.fixture
def api_client(resource_store: ResourceStore):
    """Construct a FastAPI test client bound to the current ResourceStore."""
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    except Exception as e:
        pytest.skip(f"FastAPI test client unavailable ({e!r})")

    podman = PodmanRuntime(resource_store)

    try:
        from api_runtime.routes import register_routes
    except Exception as e:
        pytest.skip(f"API routes not yet available ({e!r})")

    app = FastAPI()
    register_routes(app, resource_store, podman)
    return TestClient(app)


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    return os.environ.get("ORCHESTRATOR_URL", "http://localhost:3000")
