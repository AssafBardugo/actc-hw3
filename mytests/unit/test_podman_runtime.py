# import pytest

# from core.resources import Resource
# from core.types import ResourceType
# from runtime.podman import PodmanRuntime

# pytestmark = [pytest.mark.phase2, pytest.mark.unit]


# def _pod(name: str = "demo", namespace: str = "default") -> Resource:
#     return Resource(
#         kind=ResourceType.POD,
#         name=name,
#         namespace=namespace,
#         metadata={"name": name, "namespace": namespace},
#         spec={"containers": [{"name": name, "image": "alpine:latest", "env": {"KEY": "VALUE"}}]},
#     )


# def test_start_pod_creates_and_starts_container(monkeypatch):
#     runtime = PodmanRuntime()
#     created = {}
#     started = {}

#     monkeypatch.setattr(runtime, "_inspect_container", lambda name: None)
#     monkeypatch.setattr(runtime, "_podman_create", lambda name, image, env: f"cid-{name}")
#     monkeypatch.setattr(runtime, "_podman_start", lambda name: started.setdefault(name, True))

#     pod = _pod()
#     runtime.start_pod(pod)

#     expected_name = f"pod-{pod.namespace}-{pod.name}"
#     assert started.get(expected_name) is True
#     pod_id = (pod.namespace, pod.name)
#     assert pod_id in runtime._cache
#     assert runtime._cache[pod_id].name == expected_name
#     assert runtime._cache[pod_id].running is True


# def test_start_pod_is_idempotent_when_already_running(monkeypatch):
#     runtime = PodmanRuntime()
#     pod = _pod()
#     pod_id = (pod.namespace, pod.name)

#     running_info = ContainerInfo(container_id="abc", name="existing", running=True)
#     monkeypatch.setattr(runtime, "_inspect_container", lambda name: running_info)
#     monkeypatch.setattr(runtime, "_podman_create", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not create")))  # type: ignore
#     monkeypatch.setattr(runtime, "_podman_start", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not start")))  # type: ignore

#     runtime.start_pod(pod)
#     runtime.start_pod(pod)

#     assert runtime._cache[pod_id].running is True


# def test_start_pod_restarts_stopped_container(monkeypatch):
#     runtime = PodmanRuntime()
#     pod = _pod()
#     pod_id = (pod.namespace, pod.name)
#     calls = {"start": 0}

#     stopped_info = ContainerInfo(container_id="cid", name="demo", running=False)
#     monkeypatch.setattr(runtime, "_inspect_container", lambda name: stopped_info)

#     def _start(name: str) -> None:
#         calls["start"] += 1

#     monkeypatch.setattr(runtime, "_podman_start", _start)
#     monkeypatch.setattr(runtime, "_podman_create", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not create")))  # type: ignore

#     runtime.start_pod(pod)
#     assert calls["start"] == 1
#     assert runtime._cache[pod_id].running is True


# def test_stop_pod_is_idempotent(monkeypatch):
#     runtime = PodmanRuntime()
#     pod = _pod()
#     pod_id = (pod.namespace, pod.name)
#     stopped = {"stop": 0, "rm": 0}

#     running_info = ContainerInfo(container_id="cid", name="demo", running=True)
#     inspections = iter([running_info, None])
#     monkeypatch.setattr(runtime, "_inspect_container", lambda name: next(inspections, None))

#     def _stop(name: str) -> None:
#         stopped["stop"] += 1

#     def _rm(name: str) -> None:
#         stopped["rm"] += 1

#     monkeypatch.setattr(runtime, "_podman_stop", _stop)
#     monkeypatch.setattr(runtime, "_podman_rm", _rm)

#     runtime._cache[pod_id] = running_info

#     runtime.stop_pod(pod_id)
#     runtime.stop_pod(pod_id)

#     assert stopped["stop"] == 1
#     assert stopped["rm"] == 1
#     assert pod_id not in runtime._cache


# def test_is_running_reflects_podman_inspect(monkeypatch):
#     runtime = PodmanRuntime()
#     pod = _pod()
#     pod_id = (pod.namespace, pod.name)

#     running_info = ContainerInfo(container_id="cid", name="demo", running=True)
#     monkeypatch.setattr(runtime, "_inspect_container", lambda name: running_info)
#     assert runtime.is_running(pod_id) is True

#     not_running = ContainerInfo(container_id="cid", name="demo", running=False)
#     monkeypatch.setattr(runtime, "_inspect_container", lambda name: not_running)
#     assert runtime.is_running(pod_id) is False

#     monkeypatch.setattr(runtime, "_inspect_container", lambda name: None)
#     assert runtime.is_running(pod_id) is False
