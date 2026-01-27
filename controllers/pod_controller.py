from controllers.base import Controller
from actual_state.types import ResourceType
from actual_state.store import ResourceStore
from api_runtime.podman import PodmanRuntime


class PodController(Controller):
    """Reconcile desired state with actual state"""

    def __init__(self, store: ResourceStore, runtime: PodmanRuntime):
        self.actual_state = store
        self.desired_state = runtime


    def reconcile(self):
        pods_in_store = self.actual_state.list_by_kind(ResourceType.POD)
        running_pods = self.desired_state.list_running_pods()

        for pods in pods_in_store.values():
            for pod in pods.values():
                if pod not in running_pods:
                    self.desired_state.start_pod(pod)

        for pod in running_pods:
            if not self.actual_state.get(ResourceType.POD, pod.name, pod.namespace):
                self.desired_state.stop_pod(pod)
