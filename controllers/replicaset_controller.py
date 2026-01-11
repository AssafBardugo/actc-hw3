"""
ReplicaSet Controller

Responsibility:
- Ensure the number of Pods matching a ReplicaSet selector
  equals spec.replicas.

Important:
- MUST be idempotent.
- MUST only modify desired state (ResourceStore).
- MUST NOT start or stop workers directly.
- MUST create/delete Pods via the ResourceStore only.
"""

