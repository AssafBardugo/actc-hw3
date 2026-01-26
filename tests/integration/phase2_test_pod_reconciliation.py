import pytest

from controllers.pod_controller import PodController
from actual_state.resources import Resource
from actual_state.store import ResourceStore
from actual_state.types import ResourceType
from api_runtime.podman import PodmanRuntime

pytestmark = [pytest.mark.phase2, pytest.mark.integration]


class InspectableRuntime(PodmanRuntime):
    """PodmanRuntime with a public list_running_pods helper for tests."""

    def list_running_pods(self):
        return {pid for pid, info in self._cache.items() if info.running}


def _pod(name: str = "phase2", image: str = "alpine:latest") -> Resource:
    return Resource(
        kind=ResourceType.POD,
        name=name,
        namespace="default",
        metadata={"name": name},
        spec={"containers": [{"name": name, "image": image}]},
    )


def test_creating_pod_starts_container(monkeypatch):
    store = ResourceStore()
    runtime = InspectableRuntime()
    pod = _pod("start-me")
    store.create(pod)

    created: list[str] = []
    started: list[str] = []

    monkeypatch.setattr(runtime, "_inspect_container", lambda name: None)
    monkeypatch.setattr(runtime, "_podman_create", lambda name, image, env: created.append(name) or f"cid-{name}")
    monkeypatch.setattr(runtime, "_podman_start", lambda name: started.append(name))

    controller = PodController(store, runtime)
    controller.reconcile()

    expected_name = f"pod-{pod.namespace}-{pod.name}"
    assert created == [expected_name]
    assert started == [expected_name]
    assert (pod.namespace, pod.name) in runtime.list_running_pods()


def test_deleting_pod_stops_container(monkeypatch):
    store = ResourceStore()
    runtime = InspectableRuntime()
    pod = _pod("delete-me")
    store.create(pod)

    monkeypatch.setattr(runtime, "_inspect_container", lambda name: None)
    monkeypatch.setattr(runtime, "_podman_create", lambda name, image, env: f"cid-{name}")
    monkeypatch.setattr(runtime, "_podman_start", lambda name: None)
    controller = PodController(store, runtime)
    controller.reconcile()

    stopped: list[str] = []
    removed: list[str] = []
    monkeypatch.setattr(
        runtime,
        "_inspect_container",
        lambda name: runtime._cache.get((pod.namespace, pod.name)),
    )
    monkeypatch.setattr(runtime, "_podman_stop", lambda name: stopped.append(name))
    monkeypatch.setattr(runtime, "_podman_rm", lambda name: removed.append(name))

    store.delete(ResourceType.POD, pod.name, pod.namespace)
    controller.reconcile()

    expected_name = f"pod-{pod.namespace}-{pod.name}"
    assert expected_name in stopped
    assert expected_name in removed
    assert runtime.list_running_pods() == set()
