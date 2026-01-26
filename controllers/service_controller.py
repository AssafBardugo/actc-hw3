from controllers.base import Controller
from actual_state.types import ResourceType
from actual_state.resources import Resource
from actual_state.store import ResourceStore

from typing import Dict, Tuple, Set, Optional


class ServiceController(Controller):
    store: ResourceStore
    endpoints: Dict[Tuple[str, str], Set[str]]  # (namespace, name) -> set of pod names

    def __init__(self, store: ResourceStore) -> None:
        self.store = store
        self.endpoints = {}


    def reconcile(self) -> None:
        all_services = self.store.list_by_kind(ResourceType.SERVICE)

        for namespace, services in all_services.items():

            pods_in_ns = self.store.list_by_namespace_and_kind(ResourceType.POD, namespace)

            for service in services.values():
                self._reconcile_single_service(service, pods_in_ns)


    def _reconcile_single_service(self, service: Resource, pods_in_namespace: Dict[str, Resource]) -> None:
        try:
            selector, port, target_port = self.get_properties(service)
        except (ValueError, KeyError):
            self.endpoints[(service.namespace, service.name)] = set([])
            return

        matched_pods = []
        for pod in pods_in_namespace.values():

            metadata = pod.metadata or {}
            labels: Optional[Dict[str, str]] = metadata.get("labels")

            if not labels:
                continue

            if all(labels.get(k) == v for k, v in selector.items()):
                matched_pods.append(pod.name)

        self.endpoints[(service.namespace, service.name)] = set(matched_pods)


    def get_endpoints(self, namespace: str, name: str):
        return self.endpoints.get((namespace, name), set())


    def get_properties(self, service: Resource) -> Tuple[Dict[str, str], int, int]:
        spec = service.spec
        if spec is None:
            raise ValueError()
        
        selector: Optional[Dict[str, str]] = spec.get("selector")
        if not selector:
            raise ValueError()
        
        if not service.spec["ports"] or not service.spec["ports"][0]["port"]:
            raise ValueError()
        
        port: int = service.spec["ports"][0]["port"]
        targetPort: int = service.spec["ports"][0].get("targetPort", port)  # target_port = port if targetPort is None

        return selector, port, targetPort
