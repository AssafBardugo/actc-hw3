from concurrent.futures import Future
from typing import Any, Optional

from core.resources import Resource
from core.store import ResourceStore
from api.podman import PodmanRuntime


class OrchestratorAPI:
    
    def __init__(self, store: ResourceStore, podman: PodmanRuntime) -> None:
        self.store = store
        self.podman = podman
    
    
    def send2pod(self, pod: Resource, value: Any, is_call = False) -> Optional[Future]:

        ctr_info = self.podman._inspect_container(pod)
        if not ctr_info or not ctr_info.running:
            raise ValueError(f"{pod.key()} not found or not running")
        
        future = Future() if is_call else None
        ctr_info.input_queue.put((value, future))

        return future





# If a message includes a Future:
# Worker must eventually call future.set_result(...)
# Or future.set_exception(...)


# class PodExecutionRuntime:
    
#     def __init__(self, pod_controller: PodController, store: ResourceStore):
#         self.pod_controller = pod_controller
#         self.store = store
    
#     def send_to_pod(
#         self,
#         pod_name: str,
#         value: Any,
#         namespace: str = "default",
#         expect_response: bool = False,
#     ) -> Optional[Future]:
#         raise NotImplementedError
    
#     def send_to_service(
#         self,
#         service_name: str,
#         value: Any,
#         namespace: str = "default",
#         expect_response: bool = False,
#         port: int = None,
#     ) -> Optional[Future]:
#         raise NotImplementedError
    
#     def resolve_service(self, service_ref: str, namespace: str = "default") -> tuple:
#         raise NotImplementedError