from controllers.base import Controller
from actual_state.types import ResourceType
from actual_state.store import ResourceStore

from typing import Dict, Tuple, Set, Optional


class ServiceController(Controller):
    store: ResourceStore
    endpoints: Dict[Tuple[str, str], Set[str]]  # (service.namespace, service.name) -> set of pod names

    def __init__(self, store: ResourceStore) -> None:
        self.store = store
        self.endpoints = {}


    def reconcile(self) -> None:
        all_services = self.store.list_by_kind(ResourceType.SERVICE)

        for namespace, services in all_services.items():

            pods_in_ns = self.store.list_by_namespace_and_kind(ResourceType.POD, namespace)

            for service in services.values():

                if service.spec["selector"] == {}:
                    continue

                matched_pods = []
                for pod in pods_in_ns.values():

                    if all(pod.metadata["labels"].get(k) == v for k, v in service.spec["selector"].items()):
                        matched_pods.append(pod.name)
                
                if not matched_pods:
                    print(f'Warning: Service {service.name} with the selector {service.spec["selector"]} matches no pods')
                
                self.endpoints[(service.namespace, service.name)] = set(matched_pods)
    

    def get_endpoints(self, namespace: str, name: str) -> Set[str]:
        return self.endpoints.get((namespace, name), set())
