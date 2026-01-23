import queue
from typing import Dict, Any, Optional
from core.types import ResourceType, ResourceStatus


class Resource:
    """
    Data model for cluster resources (Pod, Service, ReplicaSet)
    """

    def __init__(
        self, 
        kind: ResourceType, 
        name: str, 
        namespace: str = "default",
        metadata: Dict[str, Any] = {},
        spec: Dict[str, Any] = {},
        status: Dict[str, Any] = {}
    ):
        if not isinstance(kind, ResourceType):
            raise ValueError("Invalid resource kind")
        self.kind = kind
        self.name = name
        self.namespace = namespace
        self.metadata = metadata
        self.spec = spec
        self.status = status

        self.input_queue = queue.Queue()
        self.status["phase"] = ResourceStatus.PENDING


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
            "status": self.status
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


    def copy(self):
        cloned = Resource(
            self.kind,
            self.name,
            self.namespace,
            metadata=self.metadata.copy(),
            spec=self.spec.copy(),
            status=self.status.copy(),
        )
        cloned.input_queue = self.input_queue
        return cloned


    def key(self) -> str:
        return f"{self.kind}/{self.namespace}/{self.name}"
