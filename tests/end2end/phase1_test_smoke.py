import os
import subprocess
import sys
import time

import httpx
import pytest

pytestmark = [pytest.mark.phase1, pytest.mark.e2e]


def _wait_for_healthz(base_url: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    last_exc = None
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{base_url}/healthz", timeout=1.0)
            if resp.status_code == 200:
                return
        except Exception as exc:  # pragma: no cover - used only during bring-up
            last_exc = exc
        time.sleep(0.2)
    raise RuntimeError(f"orchestrator did not become healthy: {last_exc}")


def test_health_and_pod_creation_end_to_end(e2e_base_url):
    """
    Full-system smoke test for Phase 1:
    - orchestrator serves /healthz
    - creating a Pod through the public API succeeds
    """
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "orchestrator.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        _wait_for_healthz(e2e_base_url)

        pod_body = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "smoke-pod", "namespace": "default"},
            "spec": {"containers": [{"name": "demo", "image": "alpine:latest"}]},
        }
        resp = httpx.post(
            f"{e2e_base_url}/api/v1/namespaces/default/pods",
            json=pod_body,
            timeout=5.0,
        )
        assert resp.status_code == 201

        listed = httpx.get(f"{e2e_base_url}/api/v1/namespaces/default/pods", timeout=5.0)
        assert listed.status_code == 200
        assert any(item["metadata"]["name"] == "smoke-pod" for item in listed.json()["items"])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
