from enum import Enum

class ResourceType(Enum):
    POD = "Pod"
    SERVICE = "Service"
    REPLICASET = "ReplicaSet"

class PodStatus(Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"
