"""
Pod Controller

Responsibility:
- Ensure that each desired Pod has a corresponding running worker.
- Start workers for newly created Pods.
- Stop workers when Pods are deleted.
- Maintain mapping between Pods and running workers.

Invariant:
- For every Pod that exists in desired state, exactly one worker is running.
- For every running worker, there exists a corresponding Pod in desired state.

PodController is responsible only for aligning desired Pod resources
with the actual runtime state.

It does not create or delete Pods; it only starts and stops workers
corresponding to existing Pod resources.
"""
from controllers.base import Controller
from core.types import ResourceType
from core.store import ResourceStore
from runtime.podman import PodmanRuntime


class PodController(Controller):
    """Reconcile desired state with actual state"""

    def __init__(self, store: ResourceStore, runtime: WorkerRuntime):
        self.desired_state = store
        self.actual_state = runtime


    def reconcile(self):
        desired_pods = self.desired_state.list_by_kind(ResourceType.POD)
        running_pods = self.actual_state.list_running_pods()

        for namespace, resources in desired_pods.items():
            for name in resources:
                if (namespace, name) not in running_pods:
                    self.actual_state.start_pod((namespace, name))

        for namespace, name in running_pods:
            if not self.desired_state.get(ResourceType.POD, name, namespace):
                self.actual_state.stop_pod((namespace, name))
