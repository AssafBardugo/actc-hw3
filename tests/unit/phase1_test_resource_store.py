import threading

import pytest

from core.resources import Resource
from core.store import ResourceStore
from core.types import ResourceType

pytestmark = [pytest.mark.phase1, pytest.mark.unit]


def test_resource_store_rejects_duplicate_creation(resource_store: ResourceStore):
    pod = Resource(ResourceType.POD, "same-name", "default", {}, {})
    resource_store.create(pod)

    with pytest.raises(ValueError):
        resource_store.create(pod)

    fetched = resource_store.get(ResourceType.POD, "same-name", "default")
    assert fetched is pod


def test_resource_store_update_requires_existing_resource(resource_store: ResourceStore):
    missing = Resource(ResourceType.SERVICE, "nope", "default", {}, {})
    with pytest.raises(KeyError):
        resource_store.update(missing)


def test_resource_store_thread_safety_under_concurrent_writes():
    """
    ResourceStore must be the single thread-safe source of truth.
    Concurrent CRUD operations should not corrupt internal state.
    """
    store = ResourceStore()
    total = 50

    def create_and_update(idx: int) -> None:
        pod = Resource(ResourceType.POD, f"pod-{idx}", "default", {}, {"rev": 0})
        store.create(pod)
        updated = Resource(ResourceType.POD, f"pod-{idx}", "default", {}, {"rev": idx})
        store.update(updated)
        assert store.get(ResourceType.POD, pod.name, pod.namespace).spec["rev"] == idx

    threads = [threading.Thread(target=create_and_update, args=(i,)) for i in range(total)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    pods = store.list_by_kind(ResourceType.POD).get("default", {})
    assert len(pods) == total
    assert all(isinstance(pod, Resource) for pod in pods.values())


def test_resource_store_delete_reflects_presence(resource_store: ResourceStore):
    pod = Resource(ResourceType.POD, "ephemeral", "default", {}, {})
    resource_store.create(pod)

    assert resource_store.delete(ResourceType.POD, "ephemeral", "default") is True
    assert resource_store.delete(ResourceType.POD, "ephemeral", "default") is False
    assert resource_store.get(ResourceType.POD, "ephemeral", "default") is None
