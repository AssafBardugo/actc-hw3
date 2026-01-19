
def test_pod_controller_idempotent(resource_store, runtime_worker):
    from controllers.pod_controller import PodController
    from core.resources import Resource
    from core.types import ResourceType

    controller = PodController(resource_store, runtime_worker)

    pod = Resource(ResourceType.POD, "p1", "default", {}, {})
    resource_store.create(pod)

    controller.reconcile()
    controller.reconcile()  # must not crash


def test_replicaset_controller_empty(resource_store):
    from controllers.replicaset_controller import ReplicaSetController

    controller = ReplicaSetController(resource_store)
    controller.reconcile()  # no RS → no crash


def test_service_controller_empty(resource_store):
    from controllers.service_controller import ServiceController

    controller = ServiceController(resource_store)
    controller.reconcile()  # no services → no crash
