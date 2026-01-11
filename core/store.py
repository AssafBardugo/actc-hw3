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

