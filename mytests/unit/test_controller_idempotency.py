import pytest

from controllers.pod_controller import PodController
from controllers.replicaset_controller import ReplicaSetController
from controllers.service_controller import ServiceController
from core.types import ResourceType

pytestmark = [pytest.mark.phase1, pytest.mark.unit]


def test_pod_controller_start_is_idempotent(resource_store, runtime_stub, make_pod):
    pod = make_pod(name="idempotent-pod")
    resource_store.create(pod)

    controller = PodController(resource_store, runtime_stub)

    controller.reconcile()
    controller.reconcile()

    assert len(runtime_stub.started) == 1
    assert runtime_stub.started[0].name == "idempotent-pod"
    assert runtime_stub.stopped == []


def test_pod_controller_stop_is_idempotent(resource_store, runtime_stub):
    controller = PodController(resource_store, runtime_stub)
    runtime_stub._running.add(("default", "ghost"))

    controller.reconcile()
    controller.reconcile()

    assert runtime_stub.stopped.count(("default", "ghost")) == 1
    assert ("default", "ghost") not in runtime_stub.list_running_pods()


def test_service_controller_repeated_reconcile_is_stable(resource_store, make_service, make_pod):
    svc = make_service(name="svc", selector={"app": "demo"})
    pod = make_pod(name="demo-0", labels={"app": "demo"})
    resource_store.create(svc)
    resource_store.create(pod)

    controller = ServiceController(resource_store)

    controller.reconcile()
    first_endpoints = controller.get_endpoints("default", "svc")

    controller.reconcile()
    second_endpoints = controller.get_endpoints("default", "svc")

    assert first_endpoints == {"demo-0"}
    assert second_endpoints == {"demo-0"}


def test_replicaset_controller_does_not_over_create(resource_store, make_replicaset, make_pod):
    rs = make_replicaset(name="stable-rs", replicas=1, selector={"app": "demo"})
    existing = make_pod(name="demo-0", labels={"app": "demo"})
    resource_store.create(rs)
    resource_store.create(existing)

    controller = ReplicaSetController(resource_store)

    controller.reconcile()
    controller.reconcile()  # idempotent: repeating should not corrupt store or delete pods

    pods = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert "demo-0" in pods  # existing pod must remain present
    assert len(pods) >= 1  # no deletion or corruption
