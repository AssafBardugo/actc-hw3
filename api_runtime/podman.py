import random
import subprocess
from concurrent.futures import Future
from typing import Optional, Dict, List, Any, Tuple

from actual_state.resources import Resource
from actual_state.store import ResourceStore
from actual_state.types import ResourceType, PodStatus


class PodmanRuntime:
    queues: Dict[str, RuntimeQueue]     # map Resource.key() to msg queue

    def __init__(self, store: ResourceStore):
        self.store = store
        self.queues = {}


    def start_pod(self, pod: Resource) -> None:

        if pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        if status in [PodStatus.RUNNING, PodStatus.SUCCEEDED, PodStatus.FAILED]:
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

            self.store.update_status(pod, PodStatus.RUNNING)

        except subprocess.CalledProcessError:
            self.store.update_status(pod, PodStatus.FAILED)


    def stop_pod(self, pod: Resource) -> None:

        if pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        if status != PodStatus.RUNNING:
            return  # idempotence

        try:
            subprocess.run(["podman", "stop", pod.key()], capture_output=True, check=True)

            subprocess.run(["podman", "rm", "-f", pod.key()], capture_output=True, check=True)

        except subprocess.CalledProcessError:
            self.store.update_status(pod, PodStatus.FAILED)


    def send2pod(self, pod: Optional[Resource], value: Any) -> None:

        if not pod:
            raise KeyError("param is not a resource")

        status = self._inspect_container(pod)

        if status != PodStatus.RUNNING:
            raise KeyError(f"{pod.key()} not found or not running")
        
        pod_key = pod.key()
        if pod_key not in self.queues:
            self.queues[pod_key] = RuntimeQueue()

        # self.queues[pod_key].enqueue((value, None))

        requests.post(
            f"http://localhost:{pod.status['hostPort']}/",
            json=data
        )


    def call2pod(self, pod: Optional[Resource], value: Any) -> Future:

        if not pod or pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        if status != PodStatus.RUNNING:
            raise KeyError(f"{pod.key()} not found or not running")

        future = Future()

        pod_key = pod.key()
        if pod_key not in self.queues:
            self.queues[pod_key] = RuntimeQueue()

        # self.queues[pod_key].enqueue((value, future))
        # return future

        resp = requests.post(
            f"http://localhost:{pod.status['hostPort']}/",
            json=data
        )
        return resp.text


    def route2service(self, service: Resource, request: Any, expect_response: bool = False):
        
        incoming_port = service.spec["ports"][0]["port"]

        service_port = service.spec["ports"][0]["port"]
        target_port = service.spec["ports"][0]["targetPort"]

        if incoming_port != service_port:
            raise KeyError("Port does not match service port")

        pod = self.load_balancer(service.namespace, service.spec["selector"])
        
        if expect_response:
            return self.call2pod(pod, request)
        else:
            self.send2pod(pod, request)
            return None


    def load_balancer(self, namespace: str, selector: Dict[str, str]) -> Resource:

        pods_in_ns = self.store.list_by_namespace_and_kind(ResourceType.POD, namespace)

        matched_pods = []
        for pod in pods_in_ns.values():
            labels = (pod.metadata or {}).get("labels")
            if not labels:
                continue
            if all(labels.get(k) == v for k, v in selector.items()):
                matched_pods.append(pod)

        if not matched_pods:
            raise KeyError(f"No pods match service in {namespace}")

        return random.choice(matched_pods)


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


    def list_running_pods(self) -> List[Resource]:
        running_pods = []
        all_pods = self.store.list_by_kind(ResourceType.POD)

        for pods in all_pods.values():
            for pod in pods.values():
                if self._inspect_container(pod) == PodStatus.RUNNING:
                    running_pods.append(pod)

        return running_pods


    def _inspect_container(self, resource: Resource) -> PodStatus:

        result = subprocess.run(["podman", "inspect", resource.key()], capture_output=True, text=True)

        if result.returncode != 0:
            err = (result.stderr or "").lower()

            if "no such object" in err or "does not exist" in err:
                return self.store.update_status(resource, PodStatus.PENDING)

            return self.store.update_status(resource, PodStatus.FAILED)

        import json
        data = json.loads(result.stdout)[0]
        state = data.get("State", {})

        running = bool(state.get("Running", False))
        status = state.get("Status", "")
        exit_code = int(state.get("ExitCode", 0))

        if running or status == "running":
            new_status = PodStatus.RUNNING

        elif status in ("exited", "stopped", "dead"):
            new_status = PodStatus.SUCCEEDED if exit_code == 0 else PodStatus.FAILED  
        else:
            new_status = PodStatus.PENDING
        
        return self.store.update_status(pod, new_status)

