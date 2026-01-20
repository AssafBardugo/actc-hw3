import os
import shutil
from typing import Callable, Dict, Optional

import pytest

from core.resources import Resource
from core.store import ResourceStore
from core.types import ResourceType


class RecordingRuntime:
    """Simple runtime stub that records start/stop calls without side effects."""

    def __init__(self):
        self.started: list[Resource] = []
        self.stopped: list[tuple[str, str]] = []
        self._running: set[tuple[str, str]] = set()

    def start_pod(self, pod: Resource) -> None:
        self.started.append(pod)
        self._running.add((pod.namespace, pod.name))

    def stop_pod(self, pod_id: tuple[str, str]) -> None:
        self.stopped.append(pod_id)
        self._running.discard(pod_id)

    def list_running_pods(self):
        return set(self._running)


@pytest.fixture
def resource_store() -> ResourceStore:
    return ResourceStore()


@pytest.fixture
def runtime_stub() -> RecordingRuntime:
    return RecordingRuntime()


@pytest.fixture
def make_pod() -> Callable[..., Resource]:
    def _make(
        name: str = "pod-1",
        namespace: str = "default",
        labels: Optional[Dict[str, str]] = None,
        image: str = "alpine:latest",
        env: Optional[Dict[str, str]] = None,
    ) -> Resource:
        metadata: Dict[str, object] = {"name": name, "namespace": namespace}
        if labels:
            metadata["labels"] = labels
        container_spec: Dict[str, object] = {"name": name, "image": image}
        if env:
            container_spec["env"] = env
        spec = {"containers": [container_spec]}
        return Resource(
            kind=ResourceType.POD,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec,
        )

    return _make


@pytest.fixture
def make_service() -> Callable[..., Resource]:
    def _make(
        name: str = "svc-1",
        namespace: str = "default",
        selector: Optional[Dict[str, str]] = None,
        ports: Optional[list[dict]] = None,
    ) -> Resource:
        metadata: Dict[str, object] = {"name": name, "namespace": namespace}
        spec = {
            "selector": selector or {},
            "ports": ports
            or [
                {
                    "protocol": "TCP",
                    "port": 80,
                    "targetPort": 8080,
                }
            ],
            "type": "ClusterIP",
        }
        return Resource(
            kind=ResourceType.SERVICE,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec,
        )

    return _make


@pytest.fixture
def make_replicaset(make_pod: Callable[..., Resource]) -> Callable[..., Resource]:
    def _make(
        name: str = "rs-1",
        namespace: str = "default",
        replicas: int = 1,
        selector: Optional[Dict[str, str]] = None,
        template_labels: Optional[Dict[str, str]] = None,
        pod_image: str = "alpine:latest",
    ) -> Resource:
        metadata: Dict[str, object] = {"name": name, "namespace": namespace}
        template = {
            "metadata": {"labels": template_labels or selector or {"app": name}},
            "spec": {
                "containers": [
                    {"name": name, "image": pod_image},
                ]
            },
        }
        spec = {
            "replicas": replicas,
            "selector": selector or {"app": name},
            "template": template,
        }
        return Resource(
            kind=ResourceType.REPLICASET,
            name=name,
            namespace=namespace,
            metadata=metadata,
            spec=spec,
        )

    return _make


@pytest.fixture
def api_client(resource_store: ResourceStore):
    """Construct a FastAPI test client bound to the current ResourceStore."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    try:
        from api.routes import register_routes
    except Exception as exc:  # pragma: no cover - defensive for early development
        pytest.skip(f"API routes not yet available ({exc!r})")

    app = FastAPI()
    register_routes(app, resource_store)
    return TestClient(app)


def require_podman() -> None:
    """Helper to skip tests when podman is unavailable in the environment."""
    if not shutil.which("podman"):
        pytest.skip("Podman binary not found; real-container tests require podman")


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    return os.environ.get("ORCHESTRATOR_URL", "http://localhost:3000")
