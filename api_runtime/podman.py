import random
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Dict, List, Any, Tuple

import requests

from actual_state.resources import Resource
from actual_state.store import ResourceStore
from actual_state.types import ResourceType, PodStatus


class PodmanRuntime:
    # FALLBACK_IMAGE = "docker.io/library/python:3.11-alpine"


    def __init__(self, store: ResourceStore):
        self.store = store
        self._fallback_servers: Dict[str, HTTPServer] = {}
        self._fallback_threads: Dict[str, threading.Thread] = {}
        self._podman_available = self._check_podman_available()


    def _check_podman_available(self) -> bool:
        try:
            result = subprocess.run(["podman", "info"], capture_output=True, text=True, timeout=1)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0


    def start_pod(self, pod: Resource) -> None:

        if pod.kind != ResourceType.POD:
            raise KeyError("param is not a pod")
        
        if pod.key() in self._fallback_servers:
            self.store.update_status(pod, PodStatus.RUNNING)
            return

        if not self._podman_available:
            self._start_fallback_server(pod)
            self.store.update_status(pod, PodStatus.RUNNING)
            return

        status = self._inspect_container(pod)

        if status in [PodStatus.RUNNING, PodStatus.SUCCEEDED, PodStatus.FAILED]:
            # Completed/failed pods are not restarted here
            # ReplicaSet will create new pods if needed (k8s-like semantics)
            return

        # here status is PENDING, we will create and start

        env = pod.spec["containers"][0].get("env", {})
        image = pod.spec["containers"][0]["image"]
        command = pod.spec["containers"][0].get("command")

        try:
            env = env.copy()
            env.setdefault("PORT", str(pod.status["containerPort"]))
            env.setdefault("POD_NAME", pod.name)
            env.setdefault("POD_NAMESPACE", pod.namespace)
            env.setdefault("POD_IMAGE", image)

            cmd = ["podman", "create", "--name", pod.key(), "-p", f'{pod.status["hostPort"]}:{pod.status["containerPort"]}']

            for k, v in env.items():
                cmd += ["-e", f"{k}={v}"]

            if command:
                if isinstance(command, (list, tuple)):
                    cmd.extend([str(arg) for arg in command])
                else:
                    cmd.append(str(command))

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            subprocess.run(["podman", "start", pod.key()], capture_output=True, text=True, check=True)

            self.store.update_status(pod, PodStatus.RUNNING)
        
        except subprocess.CalledProcessError:
            self.store.update_status(pod, PodStatus.FAILED)
        except Exception as e:
            print("Unknown exception was thrown: " + str(e))

        # except FileNotFoundError:
        #     self._start_fallback_server(pod, host_port)
        #     pod.status["hostPort"] = host_port
        #     self.store.update(pod)
        #     self.store.update_status(pod, PodStatus.RUNNING)
        #     return

        # except subprocess.CalledProcessError as exc:
        #     err = (exc.stderr or "").lower()
        #     missing = (
        #         "not found" in err
        #         or "no such image" in err
        #         or "unable to find" in err
        #         or "not known" in err
        #     )
        #     if not missing:
        #         self._start_fallback_server(pod, host_port)
        #         pod.status["hostPort"] = host_port
        #         pod.status["containerPort"] = pod.status["containerPort"]
        #         self.store.update(pod)
        #         self.store.update_status(pod, PodStatus.RUNNING)
        #         return

        #     try:
        #         fallback_cmd = self._build_podman_create_cmd(
        #             pod.key(),
        #             host_port,
        #             env,
        #             self.FALLBACK_IMAGE,
        #             self._fallback_http_command(),
        #         )
        #         subprocess.run(fallback_cmd, capture_output=True, text=True, check=True)

        #         pod.status["hostPort"] = host_port
        #         pod.status["containerPort"] = pod.status["containerPort"]
        #         self.store.update(pod)

        #         subprocess.run(["podman", "start", pod.key()], capture_output=True, text=True, check=True)
        #         self.store.update_status(pod, PodStatus.RUNNING)
        #     except (subprocess.CalledProcessError, FileNotFoundError):
        #         self._start_fallback_server(pod, host_port)
        #         pod.status["hostPort"] = host_port
        #         pod.status["containerPort"] = pod.status["containerPort"]
        #         self.store.update(pod)
        #         self.store.update_status(pod, PodStatus.RUNNING)


    def _start_fallback_server(self, pod: Resource) -> None:

        if pod.key() in self._fallback_servers:
            return

        class Handler(BaseHTTPRequestHandler):
            def _send(self, body: str) -> None:
                data = body.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._send(pod.name)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    self.rfile.read(length)
                self._send(pod.name)

        server = HTTPServer(("127.0.0.1", pod.status["hostPort"]), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._fallback_servers[pod.key()] = server
        self._fallback_threads[pod.key()] = thread
        thread.start()


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


    def send2pod(self, pod: Optional[Resource], value: Any, timeout: float) -> str:
        if not pod:
            raise KeyError("param is not a pod")

        if self._inspect_container(pod) != PodStatus.RUNNING:
            raise KeyError(f"{pod.key()} not found or not running")

        try:
            resp = requests.post(f'http://localhost:{pod.status["hostPort"]}/', json={"data": value}, timeout=timeout)
        except requests.Timeout as e:
            raise TimeoutError(str(e))
        except requests.RequestException as e:
            raise KeyError(f"Failed to reach {pod.key()}: {e}")

        if resp.status_code >= 400:
            raise KeyError(f"{pod.key()} returned {resp.status_code}")
        
        return resp.text


    def load_balancer(self, namespace: str, selector: Dict[str, str]) -> Resource:

        pods_in_ns = self.store.list_by_namespace_and_kind(ResourceType.POD, namespace)

        matched_pods = []
        for pod in pods_in_ns.values():
            if all(pod.metadata["labels"].get(k) == v for k, v in selector.items()):
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


    def _inspect_container(self, pod: Resource) -> PodStatus:

        if pod.key() in self._fallback_servers or not self._podman_available:
            return self.store.update_status(pod, PodStatus.RUNNING)

        try:
            result = subprocess.run(["podman", "inspect", pod.key()], capture_output=True, text=True)
        except FileNotFoundError:
            return self.store.update_status(pod, PodStatus.PENDING)

        if result.returncode != 0:
            err = (result.stderr or "").lower()

            if "no such object" in err or "does not exist" in err:
                return self.store.update_status(pod, PodStatus.PENDING)

            return self.store.update_status(pod, PodStatus.FAILED)

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
