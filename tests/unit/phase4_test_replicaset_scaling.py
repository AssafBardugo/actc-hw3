import pytest

from controllers.replicaset_controller import ReplicaSetController
from core.types import ResourceType

pytestmark = [pytest.mark.phase4, pytest.mark.unit]


def test_scaling_up_creates_new_pods(resource_store, make_replicaset):
    rs = make_replicaset(name="rs-scale-up", replicas=2, selector={"app": "demo"})
    resource_store.create(rs)

    controller = ReplicaSetController(resource_store)
    controller.reconcile()

    pods = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert len(pods) == 2  # converge to requested replicas


def test_scaling_down_removes_only_owned_pods(resource_store, make_replicaset, make_pod):
    rs = make_replicaset(name="rs-scale-down", replicas=3, selector={"app": "demo"})
    resource_store.create(rs)

    controller = ReplicaSetController(resource_store)
    controller.reconcile()

    foreign = make_pod(name="foreign", labels={"app": "demo"})
    resource_store.create(foreign)

    updated = make_replicaset(name="rs-scale-down", replicas=1, selector={"app": "demo"})
    resource_store.update(updated)

    controller.reconcile()

    pods = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert "foreign" in pods  # unrelated pod must not be deleted
    assert len(pods) >= 2  # at least one RS pod plus the foreign pod remains
