import subprocess
from typing import Optional, Dict, Tuple, Set
from dataclasses import dataclass
from core.resources import Resource
from core.types import ResourceType


PodID = Tuple[str, str]  # (namespace, name)


@dataclass
class ContainerInfo:
    container_id: str
    name: str
    running: bool


class PodmanRuntime:

    def __init__(self):
        self._cache: Dict[PodID, ContainerInfo] = {}


    def start_pod(self, pod: Resource) -> None:
        if pod.kind != ResourceType.POD:
            return

        pod_id = (pod.namespace, pod.name)
        container_name = self._container_name(pod)

        info = self._inspect_container(container_name)

        if info and info.running:
            return  # already running

        if info and not info.running:
            self._podman_start(container_name)
            self._cache[pod_id] = ContainerInfo(
                container_id=info.container_id,
                name=container_name,
                running=True
            )
            return

        image = self._extract_image(pod)
        env = self._extract_env(pod)

        container_id = self._podman_create(container_name, image, env)
        self._podman_start(container_name)

        self._cache[pod_id] = ContainerInfo(
            container_id=container_id,
            name=container_name,
            running=True,
        )


    def stop_pod(self, pod_id: PodID) -> None:
        container_name = self._container_name_from_id(pod_id)

        info = self._inspect_container(container_name)
        if not info:
            self._cache.pop(pod_id, None)
            return

        if info.running:
            self._podman_stop(container_name)

        self._podman_rm(container_name)
        self._cache.pop(pod_id, None)


    def is_running(self, pod_id: PodID) -> bool:
        container_name = self._container_name_from_id(pod_id)
        info = self._inspect_container(container_name)
        return bool(info and info.running)


    def list_running_pods(self) -> Set[PodID]:
        running_pods = set()
        for pod_id in self._cache:
            if self.is_running(pod_id):
                running_pods.add(pod_id)
        return running_pods


    def _container_name(self, pod: Resource) -> str:
        return f"pod-{pod.namespace}-{pod.name}"


    def _container_name_from_id(self, pod_id: PodID) -> str:
        ns, name = pod_id
        return f"pod-{ns}-{name}"


    def _podman_create(self, name: str, image: str, env: Dict[str, str]) -> str:
        cmd = ["podman", "create", "--name", name]

        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]

        cmd.append(image)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


    def _podman_start(self, name: str) -> None:
        subprocess.run(
            ["podman", "start", name],
            capture_output=True,
            check=True,
        )


    def _podman_stop(self, name: str) -> None:
        subprocess.run(
            ["podman", "stop", name],
            capture_output=True,
        )


    def _podman_rm(self, name: str) -> None:
        subprocess.run(
            ["podman", "rm", "-f", name],
            capture_output=True,
        )


    def _inspect_container(self, name: str) -> Optional[ContainerInfo]:
        result = subprocess.run(
            ["podman", "inspect", name],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return None

        import json
        data = json.loads(result.stdout)[0]

        return ContainerInfo(
            container_id=data["Id"],
            name=name,
            running=data["State"]["Running"],
        )


    def _extract_image(self, pod: Resource) -> str:
        containers = pod.spec.get("containers", [])
        if not containers:
            raise ValueError("Pod has no containers")
        return containers[0]["image"]


    def _extract_env(self, pod: Resource) -> Dict[str, str]:
        containers = pod.spec.get("containers", [])
        if not containers:
            return {}
        return containers[0].get("env", {})
