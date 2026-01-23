import json
import os
import shutil
import subprocess
import sys
import time

import httpx
import pytest

pytestmark = [pytest.mark.phase3, pytest.mark.e2e, pytest.mark.podman]


# NOTE:
# Rootless Podman requires a fully functional systemd --user session.
# On shared machines (like our csl) this is often unavailable.
# In such cases we skip the E2E test while still validating
# runtime logic via unit + integration tests.
def _podman_usable() -> bool:
    try:
        subprocess.run(
            ["podman", "info"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _wait_for_healthz(base_url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{base_url}/healthz", timeout=1.0)
            if resp.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("orchestrator did not become healthy")


def _wait_for_container(name: str, timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        res = subprocess.run(["podman", "inspect", name], capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)[0]
            if data["State"]["Running"]:
                return
        else:
            last_error = res.stderr
        time.sleep(1.0)
    raise AssertionError(f"container {name} not running: {last_error}")


def test_pod_can_call_service_through_cluster_network(e2e_base_url):
    if not shutil.which("podman"):
        pytest.skip("Podman binary not available")

    if not _podman_usable():
        pytest.skip("Rootless Podman not available in this environment")

    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "orchestrator.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    backend_container = "pod-default-backend"
    try:
        _wait_for_healthz(e2e_base_url)

        backend_pod = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "backend", "namespace": "default", "labels": {"app": "backend"}},
            "spec": {
                "containers": [
                    {
                        "name": "backend",
                        "image": "docker.io/library/python:3.11-alpine",
                        "command": ["python", "-m", "http.server", "8000"],
                    }
                ]
            },
        }
        svc = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "backend-svc", "namespace": "default"},
            "spec": {
                "selector": {"app": "backend"},
                "ports": [{"protocol": "TCP", "port": 9000, "targetPort": 8000}],
            },
        }

        resp_backend = httpx.post(f"{e2e_base_url}/api/v1/namespaces/default/pods", json=backend_pod, timeout=10.0)
        assert resp_backend.status_code == 201

        resp_service = httpx.post(f"{e2e_base_url}/api/v1/namespaces/default/services", json=svc, timeout=10.0)
        assert resp_service.status_code == 201

        _wait_for_container(backend_container)

        deadline = time.time() + 60
        last_error = None
        while time.time() < deadline:
            try:
                resp = httpx.get("http://localhost:9000", timeout=2.0)
                if resp.status_code == 200:
                    return
                last_error = f"status {resp.status_code}"
            except Exception as exc:  # pragma: no cover - waiting loop
                last_error = str(exc)
            time.sleep(1.0)
        raise AssertionError(f"Service not reachable on host port 9000: {last_error}")
    finally:
        subprocess.run(["podman", "rm", "-f", backend_container], capture_output=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
