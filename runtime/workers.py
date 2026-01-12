"""
Worker Runtime

Responsibility:
- Manage the actual execution of workers (threads).
- Start workers for Pods.
- Stop workers when requested.
- Track currently running_pods workers and their state.

Important:
- Represents the ACTUAL state of the system.
- MUST NOT modify desired state (ResourceStore).
- MUST NOT know about ReplicaSets or Services.
- MUST provide introspection for controllers.

Critical invariants:
- At most one worker per Pod
- Starting an already-running_pods Pod is safe (idempotent)
- Stopping a non-running_pods Pod is safe
- Runtime state is thread-safe
- Runtime does not modify ResourceStore
"""

import threading
from typing import Set
from core.types import PodIdentity


class WorkerRuntime:
    """Manage the actual execution of workers"""

    lock: threading.RLock
    running_pods: Set[PodIdentity]

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.running_pods = set()


    def start_pod(self, pod: PodIdentity) -> None:
        with self.lock:
            self.running_pods.add(pod)


    def stop_pod(self, pod: PodIdentity) -> None:
        with self.lock:
            self.running_pods.discard(pod)


    def is_running(self, pod: PodIdentity) -> bool:
        with self.lock:
            return pod in self.running_pods


    def list_running_pods(self) -> Set[PodIdentity]:
        with self.lock:
            return self.running_pods.copy()
