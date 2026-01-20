import pytest

from controllers.service_controller import ServiceController
from core.types import ResourceType

pytestmark = [pytest.mark.phase3, pytest.mark.unit]


def test_service_controller_selects_pods_by_label(resource_store, make_service, make_pod):
    svc = make_service(name="svc", selector={"app": "demo"})
    pod_match = make_pod(name="demo-1", labels={"app": "demo"})
    pod_other = make_pod(name="other", labels={"app": "other"})
    resource_store.create(svc)
    resource_store.create(pod_match)
    resource_store.create(pod_other)

    controller = ServiceController(resource_store)
    controller.reconcile()

    endpoints = controller.get_endpoints("default", "svc")
    assert endpoints == {"demo-1"}


def test_service_controller_handles_missing_selector(resource_store, make_service):
    svc = make_service(name="selector-less", selector={})
    resource_store.create(svc)

    controller = ServiceController(resource_store)
    controller.reconcile()

    assert controller.get_endpoints("default", "selector-less") == set()


def test_service_controller_reacts_to_label_changes(resource_store, make_service, make_pod):
    svc = make_service(name="svc", selector={"app": "demo"})
    pod = make_pod(name="demo-1", labels={"app": "demo"})
    resource_store.create(svc)
    resource_store.create(pod)
    controller = ServiceController(resource_store)

    controller.reconcile()
    assert controller.get_endpoints("default", "svc") == {"demo-1"}

    updated_pod = make_pod(name="demo-1", labels={"app": "different"})
    resource_store.update(updated_pod)
    controller.reconcile()

    assert controller.get_endpoints("default", "svc") == set()
