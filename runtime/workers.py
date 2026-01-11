"""
Worker Runtime

Responsibility:
- Manage the actual execution of workers (threads).
- Start workers for Pods.
- Stop workers when requested.
- Track currently running workers and their state.

Important:
- Represents the ACTUAL state of the system.
- MUST NOT modify desired state (ResourceStore).
- MUST NOT know about ReplicaSets or Services.
- MUST provide introspection for controllers.
"""
