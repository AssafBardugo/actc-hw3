from controllers.base import Controller
from core.types import ResourceType
from core.store import ResourceStore


class ServiceController(Controller):

    def __init__(self, store: ResourceStore) -> None:
        self.store = store
        # (namespace, service_name) -> set of pod names
        self.endpoints = {}


    def reconcile(self) -> None:
        all_services = self.store.list_by_kind(ResourceType.SERVICE)

        for namespace, services in all_services.items():

            pods_in_ns = self.store.list_by_namespace_and_kind(ResourceType.POD, namespace)

            for service in services.values():
                self._reconcile_single_service(service, pods_in_ns)


    def _reconcile_single_service(self, service, pods_in_namespace) -> None:
        spec = service.spec
        if spec is None:
            return
        
        selector = spec.get("selector")
        if not selector:
            self.endpoints[(service.namespace, service.name)] = set([])
            return
        
        matched_pods = []
        for pod in pods_in_namespace.values():

            metadata = pod.metadata or {}
            labels = metadata.get("labels")

            if not labels:
                continue

            if all(labels.get(k) == v for k, v in selector.items()):
                matched_pods.append(pod.name)

        self.endpoints[(service.namespace, service.name)] = set(matched_pods)


    def get_endpoints(self, namespace: str, service_name: str):
        return self.endpoints.get((namespace, service_name), set())
