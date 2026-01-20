import json
import os
import shutil
import subprocess
import sys
import time

import httpx
import pytest

pytestmark = [pytest.mark.phase2, pytest.mark.e2e, pytest.mark.podman]

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
        # debug
        print("WAITING FOR HEALTHZ", base_url)
        try:
            resp = httpx.get(f"{base_url}/healthz", timeout=1.0)
            if resp.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("orchestrator did not become healthy")


def _wait_for_container_running(name: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        result = subprocess.run(
            ["podman", "inspect", name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)[0]
            if data["State"]["Running"]:
                return
        else:
            last_error = result.stderr
        time.sleep(1)
    raise AssertionError(f"container {name} did not reach Running state: {last_error}")


def test_podman_runtime_starts_real_container(e2e_base_url):
    if not shutil.which("podman"):
        pytest.skip("Podman binary not available")
    
    if not _podman_usable():
        pytest.skip("Rootless Podman not available in this environment")

    env = os.environ.copy()
    proc = subprocess.Popen(        # start orchestrator.py in the background
        [sys.executable, "orchestrator.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    container_name = None
    try:
        _wait_for_healthz(e2e_base_url)

        pod_name = "phase2-real"
        container_name = f"pod-default-{pod_name}"
        pod_body = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": pod_name, "namespace": "default"},
            "spec": {
                "containers": [
                    {"name": pod_name, "image": "docker.io/library/alpine:latest", "command": ["/bin/sh", "-c", "sleep 30"]}
                ]
            }
        }

        resp = httpx.post(
            f"{e2e_base_url}/api/v1/namespaces/default/pods",
            json=pod_body,
            timeout=10.0,
        )
        assert resp.status_code == 201

        _wait_for_container_running(container_name)

        exec_res = subprocess.run(
            ["podman", "exec", container_name, "/bin/sh", "-c", "echo ok"],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        assert exec_res.returncode == 0
        assert exec_res.stdout.strip() == "ok"
    finally:
        if container_name:
            subprocess.run(["podman", "rm", "-f", container_name], capture_output=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
