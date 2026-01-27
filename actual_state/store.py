import threading
from typing import Dict, Optional, Any
from actual_state.resources import Resource
from actual_state.types import ResourceType, PodStatus


class ResourceStore:
    resources: Dict[ResourceType, Dict[str, Dict[str, Resource]]]

    def __init__(self):
        self.resources = {kind: {} for kind in ResourceType}
        self.lock = threading.RLock()


    def create(self, resource: Resource) -> None:
        with self.lock:
            kind = resource.kind
            namespace = resource.namespace
            name = resource.name

            if namespace not in self.resources[kind]:
                self.resources[kind][namespace] = {}

            if name in self.resources[kind][namespace]:
                raise ValueError(
                    f"{kind}: {namespace}/{name} already exists"
                )

            self.resources[kind][namespace][name] = resource


    def get(self, kind: ResourceType, name: str, namespace: str = "default") -> Optional[Resource]:
        with self.lock:
            return self.resources.get(kind, {}).get(namespace, {}).get(name)


    def update_status(self, resource: Resource, new_status: PodStatus) -> PodStatus:
        with self.lock:
            kind = resource.kind
            namespace = resource.namespace
            name = resource.name

            if namespace not in self.resources[kind] or name not in self.resources[kind][namespace]:
                raise KeyError(f"{kind}: {namespace}/{name} does not exist")
            
            self.resources[kind][namespace][name].status["phase"] = new_status

            return new_status


    def delete(self, kind: ResourceType, name: str, namespace: str = "default") -> bool:
        with self.lock:
            ns_resources = self.resources.get(kind, {}).get(namespace, {})
            if name in ns_resources:
                del ns_resources[name]
                return True
            return False


    def list_by_kind(self, kind: ResourceType) -> Dict[str, Dict[str, Resource]]:
        with self.lock:
            return {
                namespace: resources.copy()
                for namespace, resources in self.resources[kind].items()
            }


    def list_by_namespace_and_kind(self, kind: ResourceType, namespace: str) -> Dict[str, Resource]:
        with self.lock:
            return self.resources.get(kind, {}).get(namespace, {}).copy()
