import json
import os
import shutil
import subprocess
import sys
import time

import httpx
import pytest

pytestmark = [pytest.mark.phase4, pytest.mark.e2e, pytest.mark.podman]


def _wait_for_healthz(base_url: str, timeout: float = 30.0) -> None:
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


def _running_container(name: str) -> bool:
    res = subprocess.run(["podman", "inspect", name], capture_output=True, text=True)
    if res.returncode != 0:
        return False
    data = json.loads(res.stdout)[0]
    return data["State"]["Running"]


def _list_pods(base_url: str) -> list[dict]:
    resp = httpx.get(f"{base_url}/api/v1/namespaces/default/pods", timeout=5.0)
    resp.raise_for_status()
    return resp.json().get("items", [])


def test_replicaset_scales_up_without_deleting_existing_pods(e2e_base_url):
    if not shutil.which("podman"):
        pytest.skip("Podman binary not available")

    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "orchestrator.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    created_containers: list[str] = []
    rs_name = "scale-rs"
    try:
        _wait_for_healthz(e2e_base_url)

        rs_body = {
            "apiVersion": "apps/v1",
            "kind": "ReplicaSet",
            "metadata": {"name": rs_name, "namespace": "default"},
            "spec": {
                "replicas": 1,
                "selector": {"app": "scalable"},
                "template": {
                    "metadata": {"labels": {"app": "scalable"}},
                    "spec": {"containers": [{"name": "c", "image": "docker.io/library/alpine:latest", "command": ["sleep", "120"]}]},
                },
            },
        }

        create_rs = httpx.post(
            f"{e2e_base_url}/api/apps/v1/namespaces/default/replicasets",
            json=rs_body,
            timeout=10.0,
        )
        assert create_rs.status_code == 201

        deadline = time.time() + 90
        while time.time() < deadline:
            pods = _list_pods(e2e_base_url)
            if pods:
                break
            time.sleep(1.0)
        else:
            raise AssertionError("ReplicaSet did not create pods")

        initial_pod_names = [p["metadata"]["name"] for p in pods]

        # scale up
        scaled_body = rs_body | {"spec": rs_body["spec"] | {"replicas": 2}}
        scale_resp = httpx.put(
            f"{e2e_base_url}/api/apps/v1/namespaces/default/replicasets/{rs_name}",
            json=scaled_body,
            timeout=10.0,
        )
        assert scale_resp.status_code in (200, 202)

        # wait for second pod
        deadline = time.time() + 90
        while time.time() < deadline:
            pods = _list_pods(e2e_base_url)
            if len(pods) >= 2:
                break
            time.sleep(1.0)
        else:
            raise AssertionError("ReplicaSet did not scale up to 2 pods")

        new_pod_names = [p["metadata"]["name"] for p in pods]
        assert set(initial_pod_names).issubset(set(new_pod_names))

        for pod_name in new_pod_names:
            container_name = f"pod-default-{pod_name}"
            created_containers.append(container_name)
            assert _running_container(container_name)
    finally:
        for name in created_containers:
            subprocess.run(["podman", "rm", "-f", name], capture_output=True)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
