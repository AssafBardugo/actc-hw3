"""
Controller Base Abstraction

Responsibility:
- Define the common interface for all controllers.
- Standardize reconciliation behavior.
- Provide shared utilities (logging, timing, error handling).

Important:
- All controllers MUST be idempotent.
- reconcile() may be called repeatedly and at any time.
- Base class MUST NOT know about specific resource kinds.
- MUST NOT perform direct worker management.
"""

