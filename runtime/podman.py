import subprocess
from concurrent.futures import Future
from typing import Optional, Dict, List, Any, Tuple

from core.resources import Resource
from core.store import ResourceStore
from core.types import ResourceType, ResourceStatus
from runtime.queue import RuntimeQueue


class PodmanRuntime:
    queues: Dict[str, RuntimeQueue]     # map Resource.key() to msg queue

    def __init__(self, store: ResourceStore):
        self.store = store
        self.queues = {}


    def start_pod(self, pod: Resource) -> None:

        if pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        if status in [ResourceStatus.RUNNING, ResourceStatus.SUCCEEDED, ResourceStatus.FAILED]:
            # Completed/failed pods are not restarted here
            # ReplicaSet will create new pods if needed (k8s-like semantics)
            return

        # here status is PENDING, we will create and start

        cmd = ["podman", "create", "--name", pod.key()]

        containers = pod.spec["containers"]
        if len(containers) != 1:
            raise ValueError(f"{pod.key()} has {len(containers)} containers")

        env = containers[0].get("env", {})  # 'env' may be missing
        image = containers[0]["image"]

        if not isinstance(env, dict):
            raise ValueError(f"{pod.key()} has invalid env type")

        if not isinstance(image, str):
            raise ValueError(f"{pod.key()} has invalid image type")

        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]
        cmd.append(image)

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            subprocess.run(["podman", "start", pod.key()], capture_output=True, text=True, check=True)

            self.store.update_status(pod, ResourceStatus.RUNNING)

        except subprocess.CalledProcessError:
            self.store.update_status(pod, ResourceStatus.FAILED)


    def stop_pod(self, pod: Resource) -> None:

        if pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        if status != ResourceStatus.RUNNING:
            return  # idempotence

        try:
            subprocess.run(["podman", "stop", pod.key()], capture_output=True, check=True)

            subprocess.run(["podman", "rm", "-f", pod.key()], capture_output=True, check=True)

        except subprocess.CalledProcessError:
            self.store.update_status(pod, ResourceStatus.FAILED)


    def send2pod(self, pod: Optional[Resource], value: Any) -> None:

        if not pod or pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        if status != ResourceStatus.RUNNING:
            raise KeyError(f"{pod.key()} not found or not running")
        
        pod_key = pod.key()
        if pod_key not in self.queues:
            self.queues[pod_key] = RuntimeQueue()

        self.queues[pod_key].enqueue((value, None))


    def call2pod(self, pod: Optional[Resource], value: Any) -> Future:

        if not pod or pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        if status != ResourceStatus.RUNNING:
            raise KeyError(f"{pod.key()} not found or not running")

        future = Future()

        pod_key = pod.key()
        if pod_key not in self.queues:
            self.queues[pod_key] = RuntimeQueue()

        self.queues[pod_key].enqueue((value, future))
        return future


    def get_queue(self, pod: Optional[Resource]) -> Dict[str, Any]:

        if not pod or pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        items = self.queues[pod.key()].get_items()

        return {"pod": pod.key(), "phase": status, "size": len(items), "items": items}


    def clear_queue(self, pod: Optional[Resource]) -> None:

        if not pod or pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")
        
        self.queues[pod.key()].clear()


    def send2service(self, service: Resource, value: Any, is_call = False) -> Optional[Future]:
        raise NotImplementedError


    def list_running_pods(self) -> List[Resource]:
        running_pods = []
        all_pods = self.store.list_by_kind(ResourceType.POD)

        for pods in all_pods.values():
            for pod in pods.values():
                if self._inspect_container(pod) == ResourceStatus.RUNNING:
                    running_pods.append(pod)

        return running_pods


    def _inspect_container(self, pod: Resource) -> ResourceStatus:

        result = subprocess.run(["podman", "inspect", pod.key()], capture_output=True, text=True)

        if result.returncode != 0:
            err = (result.stderr or "").lower()

            if "no such object" in err or "does not exist" in err:
                return self.store.update_status(pod, ResourceStatus.PENDING)

            return self.store.update_status(pod, ResourceStatus.FAILED)

        import json
        data = json.loads(result.stdout)[0]
        state = data.get("State", {})

        running = bool(state.get("Running", False))
        status = state.get("Status", "")
        exit_code = int(state.get("ExitCode", 0))

        if running or status == "running":
            new_status = ResourceStatus.RUNNING

        elif status in ("exited", "stopped", "dead"):
            new_status = ResourceStatus.SUCCEEDED if exit_code == 0 else ResourceStatus.FAILED  
        else:
            new_status = ResourceStatus.PENDING
        
        return self.store.update_status(pod, new_status)


# If a message includes a Future:
# Worker must eventually call future.set_result(...)
# Or future.set_exception(...)


# class PodExecutionRuntime:
    
#     def __init__(self, pod_controller: PodController, store: ResourceStore):
#         self.pod_controller = pod_controller
#         self.store = store

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