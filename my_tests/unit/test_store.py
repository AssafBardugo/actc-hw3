import pytest

from actual_state.types import ResourceType, PodStatus
from actual_state.resources import Resource
from actual_state.store import ResourceStore

pytestmark = [pytest.mark.unit]


def test_pod_create(resource_store: ResourceStore, make_pod):
    pod = make_pod(name="pod")
    resource_store.create(pod)

    ret_pod = resource_store.get(ResourceType.POD, "pod")

    assert ret_pod
    assert pod == ret_pod
    assert pod.status["phase"] == PodStatus.PENDING


def test_service_create(resource_store: ResourceStore, make_service):
    service = make_service(name="service")
    resource_store.create(service)

    ret_service = resource_store.get(ResourceType.SERVICE, "service")

    assert ret_service
    assert service == ret_service


def test_replicaset_create(resource_store: ResourceStore, make_replicaset):
    replicaset = make_replicaset(name="replicaset")
    resource_store.create(replicaset)

    ret_replicaset = resource_store.get(ResourceType.REPLICASET, "replicaset")

    assert ret_replicaset
    assert replicaset == ret_replicaset


def test_list_by(resource_store: ResourceStore, make_pod, make_service, make_replicaset):
    pod_ns1 = make_pod(name="pod_ns1", namespace="ns1")
    srv_ns1 = make_service(name="srv_ns1", namespace="ns1")
    rs_ns1 = make_replicaset(name="rs_ns1", namespace="ns1")

    pod_ns2 = make_pod(name="pod_ns2", namespace="ns2")
    srv_ns2 = make_service(name="srv_ns2", namespace="ns2")
    rs_ns2 = make_replicaset(name="rs_ns2", namespace="ns2")

    resource_store.create(pod_ns1)
    resource_store.create(srv_ns1)
    resource_store.create(rs_ns1)
    resource_store.create(pod_ns2)
    resource_store.create(srv_ns2)
    resource_store.create(rs_ns2)

    assert resource_store.list_by_kind(ResourceType.POD)        == {"ns1": {"pod_ns1": pod_ns1},    "ns2": {"pod_ns2": pod_ns2}}
    assert resource_store.list_by_kind(ResourceType.SERVICE)    == {"ns1": {"srv_ns1": srv_ns1},    "ns2": {"srv_ns2": srv_ns2}}
    assert resource_store.list_by_kind(ResourceType.REPLICASET) == {"ns1": {"rs_ns1": rs_ns1},      "ns2": {"rs_ns2": rs_ns2}}

    assert resource_store.list_by_namespace_and_kind(ResourceType.POD, "ns1")["pod_ns1"] == pod_ns1
    assert resource_store.list_by_namespace_and_kind(ResourceType.SERVICE, "ns1")["srv_ns1"] == srv_ns1
    assert resource_store.list_by_namespace_and_kind(ResourceType.REPLICASET, "ns1")["rs_ns1"] == rs_ns1
    assert resource_store.list_by_namespace_and_kind(ResourceType.POD, "ns2")["pod_ns2"] == pod_ns2
    assert resource_store.list_by_namespace_and_kind(ResourceType.SERVICE, "ns2")["srv_ns2"] == srv_ns2
    assert resource_store.list_by_namespace_and_kind(ResourceType.REPLICASET, "ns2")["rs_ns2"] == rs_ns2


def test_delete(resource_store: ResourceStore, make_pod, make_service, make_replicaset):
    pod_ns1 = make_pod(name="pod_ns1", namespace="ns1")
    srv_ns1 = make_service(name="srv_ns1", namespace="ns1")
    rs_ns1 = make_replicaset(name="rs_ns1", namespace="ns1")

    resource_store.create(pod_ns1)
    resource_store.create(srv_ns1)
    resource_store.create(rs_ns1)

    # not exists pods
    assert resource_store.delete(ResourceType.POD, "pod_ns3", "ns1") == False
    assert resource_store.delete(ResourceType.POD, "pod_ns1", "ns3") == False
    assert resource_store.delete(ResourceType.POD, "pod_ns1", "ns2") == False
    assert resource_store.delete(ResourceType.SERVICE, "pod_ns1", "ns1") == False

    # delete twice
    assert resource_store.delete(ResourceType.POD, "pod_ns1", "ns1") == True
    assert resource_store.delete(ResourceType.POD, "pod_ns1", "ns1") == False

    assert resource_store.delete(ResourceType.SERVICE, "srv_ns1", "ns1") == True

    assert len(resource_store.list_by_kind(ResourceType.SERVICE)["ns1"]) == 0
    assert len(resource_store.list_by_kind(ResourceType.REPLICASET)["ns1"]) == 1

    assert resource_store.get(ResourceType.SERVICE, "srv_ns1", "ns1") == None
    assert resource_store.get(ResourceType.REPLICASET, "rs_ns1", "ns1") == rs_ns1
