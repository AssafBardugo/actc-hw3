import pytest

from controllers.replicaset_controller import ReplicaSetController
from actual_state.types import ResourceType

pytestmark = [pytest.mark.phase4, pytest.mark.integration]


def test_overlapping_replicasets_do_not_delete_each_others_pods(resource_store, make_replicaset):
    rs_a = make_replicaset(name="rs-a", replicas=1, selector={"app": "shared"})
    rs_b = make_replicaset(name="rs-b", replicas=2, selector={"app": "shared"})
    resource_store.create(rs_a)
    resource_store.create(rs_b)

    controller = ReplicaSetController(resource_store)
    controller.reconcile()

    pods = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert len(pods) >= 3  # each ReplicaSet should reach its replica count without conflicts

    scaled_b = make_replicaset(name="rs-b", replicas=1, selector={"app": "shared"})
    resource_store.update(scaled_b)
    controller.reconcile()

    pods_after = resource_store.list_by_namespace_and_kind(ResourceType.POD, "default")
    assert len(pods_after) >= 2  # scaling one RS down must not remove pods needed by the other
