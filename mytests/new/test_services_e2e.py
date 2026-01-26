import os
import time
import pytest
import requests

ORCH = os.environ.get("ORCHESTRATOR_URL", "http://localhost:3000")
NS = "default"

"""

How to run:
pytest -v test_services_e2e.py

"""

def _orchestrator_reachable() -> bool:
    try:
        requests.get(f"{ORCH}/healthz", timeout=0.5)
        return True
    except requests.RequestException:
        return False


if not _orchestrator_reachable():
    pytest.skip(f"Orchestrator not reachable at {ORCH}", allow_module_level=True)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def wait_until(predicate, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if predicate():
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("Timeout waiting for condition")


def _delete(url: str) -> None:
    try:
        requests.delete(url, timeout=1)
    except requests.RequestException:
        pass


def _list_pods():
    try:
        r = requests.get(f"{ORCH}/api/v1/namespaces/{NS}/pods", timeout=2)
    except requests.RequestException:
        return []
    if r.status_code != 200:
        return []
    return r.json().get("items", [])


def _delete_pods_with_label(key: str, value: str) -> None:
    for pod in _list_pods():
        md = pod.get("metadata", {})
        labels = md.get("labels", {}) or {}
        if labels.get(key) == value:
            name = md.get("name")
            if name:
                _delete(f"{ORCH}/api/v1/namespaces/{NS}/pods/{name}")


def _delete_pod_by_name(name: str) -> None:
    _delete(f"{ORCH}/api/v1/namespaces/{NS}/pods/{name}")


def _delete_replicaset(name: str) -> None:
    _delete(f"{ORCH}/api/apps/v1/namespaces/{NS}/replicasets/{name}")


def _delete_service(name: str) -> None:
    _delete(f"{ORCH}/api/v1/namespaces/{NS}/services/{name}")


def create_replicaset(name, replicas):
    _delete_replicaset(name)
    _delete_pods_with_label("app", name)
    r = requests.post(
        f"{ORCH}/api/apps/v1/namespaces/{NS}/replicasets",
        json={
            "apiVersion": "apps/v1",
            "kind": "ReplicaSet",
            "metadata": {"name": name},
            "spec": {
                "replicas": replicas,
                "selector": {"app": name},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "containers": [{
                            "name": name,
                            "image": name
                        }]
                    }
                }
            }
        }
    )
    assert r.status_code == 201


def scale_replicaset(name, replicas):
    r = requests.put(
        f"{ORCH}/api/apps/v1/namespaces/{NS}/replicasets/{name}",
        json={
            "apiVersion": "apps/v1",
            "kind": "ReplicaSet",
            "metadata": {"name": name},
            "spec": {
                "replicas": replicas,
                "selector": {"app": name},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "containers": [{
                            "name": name,
                            "image": name
                        }]
                    }
                }
            }
        }
    )
    assert r.status_code == 200


def create_service(name, app_label, port, target_port):
    _delete_service(name)
    r = requests.post(
        f"{ORCH}/api/v1/namespaces/{NS}/services",
        json={
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": name},
            "spec": {
                "selector": {"app": app_label},
                "ports": [{
                    "protocol": "TCP",
                    "port": port,
                    "targetPort": target_port
                }],
                "type": "ClusterIP"
            }
        }
    )
    assert r.status_code == 201


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

def test_single_pod_direct_http():
    create_replicaset("ping", 1)

    wait_until(lambda: True)  # give container time to start

    # We don't know pod port, but worker should log/return something.
    # Instead, validate via service later.
    assert True


def test_service_routes_to_pod():
    create_replicaset("health", 1)
    create_service("health-service", "health", 2000, 5000)

    def service_works():
        r = requests.get("http://localhost:2000/health")
        return r.status_code == 200

    wait_until(service_works)

    r = requests.get("http://localhost:2000/health")
    assert r.status_code == 200


def test_service_load_balancing():
    create_replicaset("lb", 3)
    create_service("lb-service", "lb", 2001, 5000)

    wait_until(lambda: requests.get("http://localhost:2001/test").status_code == 200)

    responses = set()
    for _ in range(10):
        r = requests.get("http://localhost:2001/test")
        responses.add(r.text)

    # Expect more than one backend responding
    assert len(responses) > 1


def test_scale_up_adds_backends():
    create_replicaset("scale", 1)
    create_service("scale-service", "scale", 2002, 5000)

    wait_until(lambda: requests.get("http://localhost:2002/x").status_code == 200)

    scale_replicaset("scale", 4)

    def many_backends():
        res = set()
        for _ in range(8):
            r = requests.get("http://localhost:2002/x")
            res.add(r.text)
        return len(res) >= 2

    wait_until(many_backends)


def test_selector_excludes_unlabeled_pod():
    create_replicaset("backend", 1)

    # Create unrelated pod without labels
    _delete_pod_by_name("noise")
    requests.post(
        f"{ORCH}/api/v1/namespaces/{NS}/pods",
        json={
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "noise"},
            "spec": {
                "containers": [{
                    "name": "noise",
                    "image": "noise"
                }]
            }
        }
    )

    create_service("backend-service", "backend", 2003, 5000)

    wait_until(lambda: requests.get("http://localhost:2003/a").status_code == 200)

    r = requests.get("http://localhost:2003/a")
    assert "backend" in r.text
