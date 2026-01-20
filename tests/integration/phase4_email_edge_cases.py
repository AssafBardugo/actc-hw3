import pytest

from controllers.replicaset_controller import ReplicaSetController
from core.types import ResourceType

pytestmark = [pytest.mark.phase4, pytest.mark.integration]


def test_overlapping_selectors_do_not_trigger_deletion(resource_store, make_replicaset):
    rs_a = make_replicaset(name="overlap-a", replicas=1, selector={"tier": "api"})
    rs_b = make_replicaset(name="overlap-b", replicas=1, selector={"tier": "api"})
    resource_store.create(rs_a)
    resource_store.create(rs_b)

    controller = ReplicaSetController(resource_store)
    controller.reconcile()

    pods = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert len(pods) >= 2  # at least one pod per ReplicaSet

    controller.reconcile()
    pods_after = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert len(pods_after) >= len(pods)  # no accidental deletions on repeat reconcile


def test_selector_change_creates_new_pods_without_killing_old_ones(resource_store, make_replicaset):
    rs = make_replicaset(name="mutable", replicas=1, selector={"app": "v1"})
    resource_store.create(rs)
    controller = ReplicaSetController(resource_store)
    controller.reconcile()

    pods_before = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    created_before = list(pods_before.keys())

    updated_rs = make_replicaset(name="mutable", replicas=1, selector={"app": "v2"})
    resource_store.update(updated_rs)
    controller.reconcile()

    pods_after = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert set(created_before).issubset(set(pods_after.keys()))  # previous pods remain
    assert len(pods_after) >= len(created_before)  # new selector may add pods, but not remove old


def test_multiple_replicasets_matching_same_pods_preserve_them(resource_store, make_replicaset, make_pod):
    shared_pod = make_pod(name="shared", labels={"role": "shared"})
    resource_store.create(shared_pod)

    rs_a = make_replicaset(name="match-a", replicas=1, selector={"role": "shared"})
    rs_b = make_replicaset(name="match-b", replicas=1, selector={"role": "shared"})
    resource_store.create(rs_a)
    resource_store.create(rs_b)

    controller = ReplicaSetController(resource_store)
    controller.reconcile()

    pods = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert "shared" in pods
    assert pods["shared"] is shared_pod


def test_scale_down_does_not_delete_unrelated_overlapping_pods(resource_store, make_replicaset, make_pod):
    rs = make_replicaset(name="safe-scale", replicas=2, selector={"tier": "web"})
    resource_store.create(rs)
    controller = ReplicaSetController(resource_store)
    controller.reconcile()

    foreign = make_pod(name="foreign", labels={"tier": "web"})
    resource_store.create(foreign)

    scaled = make_replicaset(name="safe-scale", replicas=1, selector={"tier": "web"})
    resource_store.update(scaled)
    controller.reconcile()

    pods = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert "foreign" in pods
    assert len(pods) >= 2  # at least one RS pod and the foreign pod remain
