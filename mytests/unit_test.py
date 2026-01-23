import pytest

from core.types import ResourceType, ResourceStatus
from core.store import ResourceStore
from controllers.pod_controller import PodController
from controllers.replicaset_controller import ReplicaSetController
from controllers.service_controller import ServiceController

pytestmark = [pytest.mark.unit]


def test_pod_create(resource_store: ResourceStore, make_pod):
    pod = make_pod(name="pod")
    resource_store.create(pod)

    ret_pod = resource_store.get(ResourceType.POD, "pod")

    assert ret_pod
    assert pod.key() == ret_pod.key()
    assert pod.status["phase"] == ResourceStatus.PENDING


def test_service_create(resource_store: ResourceStore, make_service):
    service = make_service(name="service")
    resource_store.create(service)

    ret_service = resource_store.get(ResourceType.SERVICE, "service")

    assert ret_service
    assert service.key() == ret_service.key()


def test_replicaset_create(resource_store: ResourceStore, make_replicaset):
    replicaset = make_replicaset(name="replicaset")
    resource_store.create(replicaset)

    ret_replicaset = resource_store.get(ResourceType.REPLICASET, "replicaset")

    assert ret_replicaset
    assert replicaset.key() == ret_replicaset.key()
