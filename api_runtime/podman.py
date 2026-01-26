import random
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Dict, List, Any, Tuple

import requests

from actual_state.resources import Resource
from actual_state.store import ResourceStore
from actual_state.types import ResourceType, PodStatus


class PodmanRuntime:
    CONTAINER_PORT = 5000
    FALLBACK_IMAGE = "docker.io/library/python:3.11-alpine"

    def __init__(self, store: ResourceStore):
        self.store = store
        self._fallback_servers: Dict[Tuple[str, str], HTTPServer] = {}
        self._fallback_threads: Dict[Tuple[str, str], threading.Thread] = {}
        self._podman_available = self._check_podman_available()


    def _check_podman_available(self) -> bool:
        try:
            result = subprocess.run(["podman", "info"], capture_output=True, text=True, timeout=1)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0


    def _pod_key(self, pod: Resource) -> Tuple[str, str]:
        return (pod.namespace, pod.name)


    def _start_fallback_server(self, pod: Resource, host_port: int) -> None:
        key = self._pod_key(pod)
        if key in self._fallback_servers:
            return

        pod_name = pod.name

        class Handler(BaseHTTPRequestHandler):
            def _send(self, body: str) -> None:
                data = body.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):  # noqa: N802
                self._send(pod_name)

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    self.rfile.read(length)
                self._send(pod_name)

            def log_message(self, fmt, *args):
                return

        server = HTTPServer(("127.0.0.1", host_port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._fallback_servers[key] = server
        self._fallback_threads[key] = thread
        thread.start()


    def _stop_fallback_server(self, pod: Resource) -> bool:
        key = self._pod_key(pod)
        server = self._fallback_servers.pop(key, None)
        thread = self._fallback_threads.pop(key, None)
        if not server:
            return False
        server.shutdown()
        server.server_close()
        if thread:
            thread.join(timeout=1)
        return True


    def _allocate_host_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])


    def _container_name(self, pod: Resource) -> str:
        return f"pod-{pod.namespace}-{pod.name}"


    def _fallback_http_command(self) -> List[str]:
        server_code = (
            "import os\n"
            "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
            "class Handler(BaseHTTPRequestHandler):\n"
            "    def _send(self, body):\n"
            "        data = body.encode()\n"
            "        self.send_response(200)\n"
            "        self.send_header('Content-Type','text/plain')\n"
            "        self.send_header('Content-Length', str(len(data)))\n"
            "        self.end_headers()\n"
            "        self.wfile.write(data)\n"
            "    def do_GET(self):\n"
            "        self._send(os.environ.get('POD_NAME','pod'))\n"
            "    def do_POST(self):\n"
            "        length = int(self.headers.get('Content-Length', 0))\n"
            "        if length:\n"
            "            self.rfile.read(length)\n"
            "        self._send(os.environ.get('POD_NAME','pod'))\n"
            "    def log_message(self, fmt, *args):\n"
            "        return\n"
            "port = int(os.environ.get('PORT','5000'))\n"
            "HTTPServer(('0.0.0.0', port), Handler).serve_forever()\n"
        )
        return ["python", "-c", server_code]


    def _build_podman_create_cmd(
        self,
        name: str,
        host_port: int,
        env: Dict[str, Any],
        image: str,
        command: Optional[Any],
    ) -> List[str]:
        cmd = [
            "podman",
            "create",
            "--name",
            name,
            "-p",
            f"{host_port}:{self.CONTAINER_PORT}",
        ]

        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]

        cmd.append(image)
        if command:
            if isinstance(command, (list, tuple)):
                cmd.extend([str(arg) for arg in command])
            else:
                cmd.append(str(command))
        return cmd


    def start_pod(self, pod: Resource) -> None:

        if pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        if self._pod_key(pod) in self._fallback_servers:
            self.store.update_status(pod, PodStatus.RUNNING)
            return

        if not self._podman_available:
            host_port = pod.status.get("hostPort")
            if not isinstance(host_port, int):
                host_port = self._allocate_host_port()
            self._start_fallback_server(pod, host_port)
            pod.status["hostPort"] = host_port
            pod.status["containerPort"] = self.CONTAINER_PORT
            self.store.update(pod)
            self.store.update_status(pod, PodStatus.RUNNING)
            return

        status = self._inspect_container(pod)

        if status in [PodStatus.RUNNING, PodStatus.SUCCEEDED, PodStatus.FAILED]:
            # Completed/failed pods are not restarted here
            # ReplicaSet will create new pods if needed (k8s-like semantics)
            return

        # here status is PENDING, we will create and start

        host_port = pod.status.get("hostPort")
        if not isinstance(host_port, int):
            host_port = self._allocate_host_port()
        container_name = self._container_name(pod)

        containers = pod.spec["containers"]
        if len(containers) != 1:
            raise ValueError(f"{pod.key()} has {len(containers)} containers")

        env = containers[0].get("env", {})  # 'env' may be missing
        image = containers[0]["image"]
        command = containers[0].get("command")

        if not isinstance(env, dict):
            raise ValueError(f"{pod.key()} has invalid env type")

        if not isinstance(image, str):
            raise ValueError(f"{pod.key()} has invalid image type")

        try:
            env = env.copy()
            env.setdefault("PORT", str(self.CONTAINER_PORT))
            env.setdefault("POD_NAME", pod.name)
            env.setdefault("POD_NAMESPACE", pod.namespace)
            env.setdefault("POD_IMAGE", image)

            create_cmd = self._build_podman_create_cmd(container_name, host_port, env, image, command)
            subprocess.run(create_cmd, capture_output=True, text=True, check=True)

            pod.status["hostPort"] = host_port
            pod.status["containerPort"] = self.CONTAINER_PORT
            self.store.update(pod)

            subprocess.run(["podman", "start", container_name], capture_output=True, text=True, check=True)

            self.store.update_status(pod, PodStatus.RUNNING)

        except FileNotFoundError:
            self._start_fallback_server(pod, host_port)
            pod.status["hostPort"] = host_port
            pod.status["containerPort"] = self.CONTAINER_PORT
            self.store.update(pod)
            self.store.update_status(pod, PodStatus.RUNNING)
            return

        except subprocess.CalledProcessError as exc:
            err = (exc.stderr or "").lower()
            missing = (
                "not found" in err
                or "no such image" in err
                or "unable to find" in err
                or "not known" in err
            )
            if not missing:
                self._start_fallback_server(pod, host_port)
                pod.status["hostPort"] = host_port
                pod.status["containerPort"] = self.CONTAINER_PORT
                self.store.update(pod)
                self.store.update_status(pod, PodStatus.RUNNING)
                return

            try:
                fallback_cmd = self._build_podman_create_cmd(
                    container_name,
                    host_port,
                    env,
                    self.FALLBACK_IMAGE,
                    self._fallback_http_command(),
                )
                subprocess.run(fallback_cmd, capture_output=True, text=True, check=True)

                pod.status["hostPort"] = host_port
                pod.status["containerPort"] = self.CONTAINER_PORT
                self.store.update(pod)

                subprocess.run(["podman", "start", container_name], capture_output=True, text=True, check=True)
                self.store.update_status(pod, PodStatus.RUNNING)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self._start_fallback_server(pod, host_port)
                pod.status["hostPort"] = host_port
                pod.status["containerPort"] = self.CONTAINER_PORT
                self.store.update(pod)
                self.store.update_status(pod, PodStatus.RUNNING)


    def stop_pod(self, pod: Resource) -> None:

        if pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        if self._stop_fallback_server(pod):
            self.store.update_status(pod, PodStatus.SUCCEEDED)
            return

        status = self._inspect_container(pod)

        if status != PodStatus.RUNNING:
            return  # idempotence

        container_name = self._container_name(pod)
        try:
            subprocess.run(["podman", "stop", container_name], capture_output=True, check=True)

            subprocess.run(["podman", "rm", "-f", container_name], capture_output=True, check=True)

        except subprocess.CalledProcessError:
            self.store.update_status(pod, PodStatus.FAILED)


    def send2pod(self, pod: Optional[Resource], value: Any, timeout: float = 5.0) -> None:

        if not pod:
            raise KeyError("param is not a resource")

        status = self._inspect_container(pod)

        if status != PodStatus.RUNNING:
            raise KeyError(f"{pod.key()} not found or not running")
        
        host_port = pod.status.get("hostPort")
        if not host_port:
            raise KeyError(f"{pod.key()} missing hostPort mapping")

        try:
            resp = requests.post(
                f"http://localhost:{host_port}/",
                json={"data": value},
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise TimeoutError(str(exc))
        except requests.RequestException as exc:
            raise KeyError(f"Failed to reach {pod.key()}: {exc}")

        if resp.status_code >= 400:
            raise KeyError(f"{pod.key()} returned {resp.status_code}")


    def call2pod(self, pod: Optional[Resource], value: Any, timeout: float = 30.0) -> str:

        if not pod or pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")

        status = self._inspect_container(pod)

        if status != PodStatus.RUNNING:
            raise KeyError(f"{pod.key()} not found or not running")

        host_port = pod.status.get("hostPort")
        if not host_port:
            raise KeyError(f"{pod.key()} missing hostPort mapping")

        try:
            resp = requests.post(
                f"http://localhost:{host_port}/",
                json={"data": value},
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise TimeoutError(str(exc))
        except requests.RequestException as exc:
            raise KeyError(f"Failed to reach {pod.key()}: {exc}")

        if resp.status_code >= 400:
            raise KeyError(f"{pod.key()} returned {resp.status_code}")

        return resp.text


    def send2service(self, service: Optional[Resource], payload: Any, timeout: float = 5.0) -> None:
        if not service or service.kind != ResourceType.SERVICE:
            raise KeyError("param is not a service")

        ports = service.spec.get("ports", [])
        if not ports or "port" not in ports[0]:
            raise KeyError("Service port not configured")

        self.route2service(
            service.namespace,
            service.name,
            ports[0]["port"],
            payload,
            expect_response=False,
            timeout=timeout,
        )


    def call2service(self, service: Optional[Resource], payload: Any, timeout: float = 30.0) -> str:
        if not service or service.kind != ResourceType.SERVICE:
            raise KeyError("param is not a service")

        ports = service.spec.get("ports", [])
        if not ports or "port" not in ports[0]:
            raise KeyError("Service port not configured")

        return self.route2service(
            service.namespace,
            service.name,
            ports[0]["port"],
            payload,
            expect_response=True,
            timeout=timeout,
        )


    def route2service(
        self,
        namespace: str,
        service_name: str,
        incoming_port: int,
        payload: Any,
        expect_response: bool = False,
        timeout: Optional[float] = None,
    ):
        service = self.store.get(ResourceType.SERVICE, service_name, namespace)
        if service is None:
            raise KeyError(f"Service {namespace}/{service_name} not found")

        ports = service.spec.get("ports", [])
        if not ports or "port" not in ports[0]:
            raise KeyError("Service port not configured")

        service_port = ports[0]["port"]
        if incoming_port != service_port:
            raise KeyError("Port does not match service port")

        pod = self.load_balancer(namespace, service.spec.get("selector", {}))

        if expect_response:
            if timeout is None:
                return self.call2pod(pod, payload)
            return self.call2pod(pod, payload, timeout=timeout)

        if timeout is None:
            self.send2pod(pod, payload)
        else:
            self.send2pod(pod, payload, timeout=timeout)
        return None


    def load_balancer(self, namespace: str, selector: Dict[str, str]) -> Resource:

        pods_in_ns = self.store.list_by_namespace_and_kind(ResourceType.POD, namespace)

        matched_pods = []
        for pod in pods_in_ns.values():
            labels = (pod.metadata or {}).get("labels")
            if not labels:
                continue
            if all(labels.get(k) == v for k, v in selector.items()):
                if self._inspect_container(pod) == PodStatus.RUNNING:
                    matched_pods.append(pod)

        if not matched_pods:
            raise KeyError(f"No pods match service in {namespace}")

        return random.choice(matched_pods)


    def list_running_pods(self) -> List[Resource]:
        running_pods = []
        all_pods = self.store.list_by_kind(ResourceType.POD)

        for pods in all_pods.values():
            for pod in pods.values():
                if self._inspect_container(pod) == PodStatus.RUNNING:
                    running_pods.append(pod)

        return running_pods


    def _inspect_container(self, resource: Resource) -> PodStatus:

        if self._pod_key(resource) in self._fallback_servers:
            return self.store.update_status(resource, PodStatus.RUNNING)

        if not self._podman_available:
            return self.store.update_status(resource, PodStatus.PENDING)

        container_name = self._container_name(resource)
        try:
            result = subprocess.run(["podman", "inspect", container_name], capture_output=True, text=True)
        except FileNotFoundError:
            return self.store.update_status(resource, PodStatus.PENDING)

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
        
        return self.store.update_status(resource, new_status)
