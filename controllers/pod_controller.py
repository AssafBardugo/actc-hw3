"""
Pod Controller

Responsibility:
- Ensure that each desired Pod has a corresponding running worker.
- Start workers for newly created Pods.
- Stop workers when Pods are deleted.
- Maintain mapping between Pods and running workers.

Important:
- MUST reconcile desired Pods against actual runtime state.
- MUST be idempotent.
- MUST NOT implement ReplicaSet logic.
- MUST NOT modify desired state except for Pod-related status if applicable.
"""

