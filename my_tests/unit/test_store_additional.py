import pytest

from actual_state.types import ResourceType, PodStatus
from actual_state.store import ResourceStore

pytestmark = [pytest.mark.unit]


def test_create_duplicate_raises(resource_store: ResourceStore, make_service):
    service = make_service(name="svc")
    resource_store.create(service)

    with pytest.raises(ValueError) as exc:
        resource_store.create(service.copy())

    assert "already exists" in str(exc.value)


def test_create_same_name_different_namespace_allowed(resource_store: ResourceStore, make_pod):
    pod_default = make_pod(name="pod")
    pod_other = make_pod(name="pod", namespace="ns1")

    resource_store.create(pod_default)
    resource_store.create(pod_other)

    assert resource_store.get(ResourceType.POD, "pod") == pod_default
    assert resource_store.get(ResourceType.POD, "pod", "ns1") == pod_other


def test_update_status_updates_stored_resource(resource_store: ResourceStore, make_pod):
    pod = make_pod(name="pod")
    resource_store.create(pod)

    new_status = resource_store.update_status(pod, PodStatus.RUNNING)

    assert new_status == PodStatus.RUNNING
    assert pod.status["phase"] == PodStatus.RUNNING


def test_update_status_missing_resource_raises(resource_store: ResourceStore, make_pod):
    pod = make_pod(name="missing")

    with pytest.raises(KeyError) as exc:
        resource_store.update_status(pod, PodStatus.FAILED)

    assert "does not exist" in str(exc.value)


def test_list_by_kind_returns_copy(resource_store: ResourceStore, make_pod):
    pod = make_pod(name="pod", namespace="ns1")
    resource_store.create(pod)

    listing = resource_store.list_by_kind(ResourceType.POD)
    listing["ns1"].pop("pod")

    assert resource_store.get(ResourceType.POD, "pod", "ns1") == pod


def test_list_by_namespace_returns_copy(resource_store: ResourceStore, make_service):
    service = make_service(name="svc", namespace="ns1")
    resource_store.create(service)

    listing = resource_store.list_by_namespace_and_kind(ResourceType.SERVICE, "ns1")
    listing.clear()

    assert resource_store.get(ResourceType.SERVICE, "svc", "ns1") == service
