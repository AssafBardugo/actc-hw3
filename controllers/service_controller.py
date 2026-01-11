"""
Service Controller

Responsibility:
- Maintain service-to-pod associations based on label selectors.
- Track which Pods belong to each Service.
- Update routing / forwarding metadata used by the runtime.

Important:
- MUST NOT create or delete Pods.
- MUST react to Pod changes, not initiate them.
- MUST be idempotent.
- MUST NOT run network servers or worker threads.
"""

