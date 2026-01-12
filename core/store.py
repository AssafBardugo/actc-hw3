"""
Resource Store (Desired State)

Responsibility:
- Store the desired state of all resources in the cluster.
- Provide thread-safe CRUD operations on resources.
- Support queries by kind, namespace, name, and labels.

Important:
- This is the SINGLE SOURCE OF TRUTH for desired state.
- MUST be thread-safe.
- MUST NOT start or stop workers.
- MUST NOT perform reconciliation.
- MUST NOT sleep, loop, or spawn threads.
"""

import threading
from typing import Dict, Optional
from core.resources import Resource
from core.types import ResourceType


class ResourceStore:
    """In-memory resource tree"""

    # self.resources[Resource.kind][Resource.namespace][Resource.name] = Resource
    resources: Dict[ResourceType, Dict[str, Dict[str, Resource]]]


    def __init__(self):
        self.resources = {kind: {} for kind in ResourceType}
        self.lock = threading.RLock()


    def create(self, resource: Resource):
        """Create a resource"""
        with self.lock:
            if resource.namespace not in self.resources[resource.kind]:
                self.resources[resource.kind][resource.namespace] = {}

            if resource.name in self.resources[resource.kind][resource.namespace]:
                raise ValueError(
                    f"{resource.kind} : {resource.namespace}/{resource.name} already exists"
                )
            self.resources[resource.kind][resource.namespace][resource.name] = resource


    def get(self, kind: ResourceType, name: str, namespace: str = "default") -> Optional[Resource]:
        """Get a resource by kind, namespace, and name. return None if missing"""
        with self.lock:
            return self.resources.get(kind, {}).get(namespace, {}).get(name)


    def update(self, resource: Resource):
        """Update a resource"""
        with self.lock:
            if resource.namespace not in self.resources[resource.kind] \
                or resource.name not in self.resources[resource.kind][resource.namespace]:
                raise KeyError(
                    f"{resource.kind} : {resource.namespace}/{resource.name} does not exist"
                )
            self.resources[resource.kind][resource.namespace][resource.name] = resource


    def delete(self, kind: ResourceType, name: str, namespace: str = "default") -> bool:
        """Delete a resource"""
        with self.lock:
            if name in self.resources.get(kind, {}).get(namespace, {}):
                del self.resources[kind][namespace][name]
                return True
            return False
    

    def list_by_kind(self, kind: ResourceType) -> Dict[str, Dict[str, Resource]]:
        """List all resources of a kind"""
        with self.lock:
            return {
                namespace: dict(resources)
                for namespace, resources in self.resources.get(kind, {}).items()
            }

    
    def list_by_namespace(self, namespace: str) -> Dict[ResourceType, Dict[str, Resource]]:
        """List all resources by a namespace"""
        with self.lock:
            return {
                kind: dict(self.resources.get(kind, {}).get(namespace, {}))
                for kind in ResourceType
            }


    def list_all(self) -> Dict[ResourceType, Dict[str, Dict[str, Resource]]]:
        """List all resources"""
        with self.lock:
            return {
                kind: {
                    namespace: dict(resources)
                    for namespace, resources in namespaces.items()
                }
                for kind, namespaces in self.resources.items()
            }
