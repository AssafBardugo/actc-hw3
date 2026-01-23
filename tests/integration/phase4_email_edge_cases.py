import pytest
from controllers.replicaset_controller import ReplicaSetController
from core.types import ResourceType

pytestmark = [pytest.mark.phase4, pytest.mark.integration, pytest.mark.email_edge_cases]


def _pod_names(store):
    pods = store.list_by_namespace_and_kind(ResourceType.POD, "default")
    return set(pods.keys())


def test_overlapping_selectors_never_delete_existing_pods(resource_store, make_replicaset):
    """
    Edge case B:
    Overlapping ReplicaSet selectors must not cause pod deletion.
    """

    rs_a = make_replicaset(
        name="overlap-a",
        replicas=1,
        selector={"tier": "api"},
    )
    rs_b = make_replicaset(
        name="overlap-b",
        replicas=1,
        selector={"tier": "api"},
    )

    resource_store.create(rs_a)
    resource_store.create(rs_b)

    controller = ReplicaSetController(resource_store)

    controller.reconcile()
    pods_after_first = _pod_names(resource_store)

    # Must have created at least one pod per RS
    assert len(pods_after_first) >= 2

    controller.reconcile()
    pods_after_second = _pod_names(resource_store)

    # No pod deletion allowed
    assert pods_after_first.issubset(pods_after_second)


def test_selector_change_does_not_delete_old_pods(resource_store, make_replicaset):
    """
    Edge case C:
    Changing selector must not delete previously created pods.
    """

    rs_v1 = make_replicaset(
        name="mutable",
        replicas=1,
        selector={"app": "v1"},
    )
    resource_store.create(rs_v1)

    controller = ReplicaSetController(resource_store)

    controller.reconcile()
    pods_before = _pod_names(resource_store)
    assert len(pods_before) >= 1

    # Change selector
    rs_v2 = make_replicaset(
        name="mutable",
        replicas=1,
        selector={"app": "v2"},
    )
    resource_store.update(rs_v2)

    controller.reconcile()
    pods_after = _pod_names(resource_store)

    # Old pods must remain
    assert pods_before.issubset(pods_after)

    # New pods may be added
    assert len(pods_after) >= len(pods_before)


def test_foreign_pods_are_never_deleted(resource_store, make_replicaset, make_pod):
    """
    Edge cases A + B:
    ReplicaSet must not delete pods it did not create,
    even if they match its selector.
    """

    foreign = make_pod(
        name="foreign",
        labels={"role": "shared"},
    )
    resource_store.create(foreign)

    rs = make_replicaset(
        name="rs",
        replicas=1,
        selector={"role": "shared"},
    )
    resource_store.create(rs)

    controller = ReplicaSetController(resource_store)

    controller.reconcile()
    pods_after = _pod_names(resource_store)

    assert "foreign" in pods_after


def test_scale_down_is_non_destructive(resource_store, make_replicaset):
    """
    Edge case A + D:
    Scaling down must not delete existing pods.
    """

    rs = make_replicaset(
        name="safe-scale",
        replicas=3,
        selector={"tier": "web"},
    )
    resource_store.create(rs)

    controller = ReplicaSetController(resource_store)

    controller.reconcile()
    pods_before = _pod_names(resource_store)
    assert len(pods_before) >= 3

    # Scale down
    rs_scaled = make_replicaset(
        name="safe-scale",
        replicas=1,
        selector={"tier": "web"},
    )
    resource_store.update(rs_scaled)

    controller.reconcile()
    pods_after = _pod_names(resource_store)

    # No deletion allowed
    assert pods_before.issubset(pods_after)
