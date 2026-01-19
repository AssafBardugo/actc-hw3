"""
Shared Types and Constants

Responsibility:
- Define enums, constants, and shared type aliases.
- Centralize common identifiers (resource kinds, statuses, etc.).
- Avoid magic strings scattered across the codebase.

Important:
- MUST NOT contain logic.
- MUST NOT import high-level modules.
- SHOULD be dependency-free and stable.
"""
from enum import Enum

class ResourceType(Enum):
    POD = "pod"
    SERVICE = "service"
    REPLICASET = "replicaSet"
