"""
Resource Definitions

Responsibility:
- Define data models for cluster resources (Pod, Service, ReplicaSet).
- Represent Kubernetes-like objects as pure data structures.
- Hold metadata and spec fields.
- Provide lightweight validation helpers if needed.

Important:
- MUST contain NO side effects.
- MUST NOT hold global or mutable shared state.
- MUST NOT start threads or processes.
- Objects must be safe to copy, compare, and serialize.

Resources are passive descriptions of desired state.
They must not contain any behavior or domain-specific logic.
"""

from typing import Dict, Any
from core.types import ResourceType


class Resource:
    def __init__(
        self, 
        kind: ResourceType, 
        name: str, 
        namespace: str, 
        metadata: Dict[str, Any], 
        spec: Dict[str, Any]
    ):
        if not isinstance(kind, ResourceType):
            raise ValueError("Invalid resource kind")
        self.kind = kind
        self.name = name
        self.namespace = namespace
        self.metadata = metadata or {}
        self.spec = spec or {}


    def to_dict(self) -> Dict[str, Any]:
        """Convert resource to Kubernetes-style dict"""
        metadata = {
            "name": self.name,
            "namespace": self.namespace,
        }
        metadata.update(self.metadata)
        return {
            "kind": self.kind,
            "metadata": metadata,
            "spec": self.spec,
        }


    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Resource):
            return False
        return (
            self.kind == other.kind
            and self.name == other.name
            and self.namespace == other.namespace
            and self.metadata == other.metadata
            and self.spec == other.spec
        )


    def __repr__(self) -> str:
        return (
            f"Resource(kind={self.kind!r}, "
            f"name={self.name!r}, "
            f"namespace={self.namespace!r}, "
            f"metadata={self.metadata!r}, "
            f"spec={self.spec!r}"
            ")"
        )

