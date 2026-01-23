from enum import Enum

class ResourceType(Enum):
    POD = "Pod"
    SERVICE = "Service"
    REPLICASET = "ReplicaSet"

class ResourceStatus(Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"
