from core.store import ResourceStore
from core.resources import Resource
from core.types import ResourceType


def test_store_create_and_get():
    store = ResourceStore()
    pod = Resource(
        kind=ResourceType.POD,
        name="p1",
        namespace="default",
        metadata={},
        spec={}
    )

    store.create(pod)
    fetched = store.get(ResourceType.POD, "p1", "default")
    assert fetched is pod


def test_store_delete():
    store = ResourceStore()
    pod = Resource(ResourceType.POD, "p1", "default", {}, {})
    store.create(pod)

    assert store.delete(ResourceType.POD, "p1", "default") is True
    assert store.get(ResourceType.POD, "p1", "default") is None

