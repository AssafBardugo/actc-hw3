import pytest

from controllers.service_controller import ServiceController
from core.types import ResourceType

pytestmark = [pytest.mark.phase3, pytest.mark.integration]


def test_service_endpoints_track_pod_lifecycle(resource_store, make_service, make_pod):
    svc = make_service(name="svc", selector={"app": "demo"})
    resource_store.create(svc)

    controller = ServiceController(resource_store)
    controller.reconcile()
    assert controller.get_endpoints("default", "svc") == set()

    pod1 = make_pod(name="demo-1", labels={"app": "demo"})
    resource_store.create(pod1)
    controller.reconcile()
    assert controller.get_endpoints("default", "svc") == {"demo-1"}

    pod2 = make_pod(name="demo-2", labels={"app": "demo"})
    resource_store.create(pod2)
    controller.reconcile()
    assert controller.get_endpoints("default", "svc") == {"demo-1", "demo-2"}

    resource_store.delete(ResourceType.POD, "demo-1", "default")
    controller.reconcile()
    assert controller.get_endpoints("default", "svc") == {"demo-2"}
