"""
API Routes (HTTP Layer)

Responsibility:
- Define REST API endpoints (Pods, Services, ReplicaSets).
- Validate incoming HTTP requests.
- Translate JSON payloads into internal Resource objects.
- Call ResourceStore CRUD operations.
- Return appropriate HTTP responses and status codes.

Important:
- MUST NOT start or stop workers.
- MUST NOT run reconciliation logic.
- MUST NOT contain loops or background threads.
- MUST be safe to call concurrently.
"""
