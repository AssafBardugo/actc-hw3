from enum import Enum

class ResourceType(Enum):
    POD = "pod"
    SERVICE = "service"
    REPLICASET = "replicaSet"

class ResourceStatus(Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"
