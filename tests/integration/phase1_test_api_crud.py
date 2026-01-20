import pytest

pytestmark = [pytest.mark.phase1, pytest.mark.integration]


def test_api_allows_basic_pod_and_service_crud(api_client):
    pod_body = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "phase1-pod", "namespace": "default"},
        "spec": {"containers": [{"name": "demo", "image": "alpine:latest"}]},
    }
    create_pod = api_client.post("/api/v1/namespaces/default/pods", json=pod_body)
    assert create_pod.status_code == 201

    list_pods = api_client.get("/api/v1/namespaces/default/pods")
    assert list_pods.status_code == 200
    assert any(item["metadata"]["name"] == "phase1-pod" for item in list_pods.json()["items"])

    get_pod = api_client.get("/api/v1/namespaces/default/pods/phase1-pod")
    assert get_pod.status_code == 200
    assert get_pod.json()["metadata"]["name"] == "phase1-pod"

    svc_body = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "phase1-svc", "namespace": "default"},
        "spec": {"selector": {"app": "demo"}, "ports": [{"port": 80, "targetPort": 8080}]},
    }
    create_svc = api_client.post("/api/v1/namespaces/default/services", json=svc_body)
    assert create_svc.status_code == 201

    list_svcs = api_client.get("/api/v1/namespaces/default/services")
    assert list_svcs.status_code == 200
    assert any(item["metadata"]["name"] == "phase1-svc" for item in list_svcs.json()["items"])

    delete_pod = api_client.delete("/api/v1/namespaces/default/pods/phase1-pod")
    assert delete_pod.status_code in (200, 202, 204)

    missing = api_client.get("/api/v1/namespaces/default/pods/phase1-pod")
    assert missing.status_code == 404


def test_api_supports_replicaset_crud_and_update(api_client):
    rs_body = {
        "apiVersion": "apps/v1",
        "kind": "ReplicaSet",
        "metadata": {"name": "phase1-rs", "namespace": "default"},
        "spec": {
            "replicas": 1,
            "selector": {"app": "demo"},
            "template": {
                "metadata": {"labels": {"app": "demo"}},
                "spec": {"containers": [{"name": "demo", "image": "alpine:latest"}]},
            },
        },
    }

    create_rs = api_client.post("/api/apps/v1/namespaces/default/replicasets", json=rs_body)
    assert create_rs.status_code == 201

    list_rs = api_client.get("/api/apps/v1/namespaces/default/replicasets")
    assert list_rs.status_code == 200
    assert any(item["metadata"]["name"] == "phase1-rs" for item in list_rs.json()["items"])

    updated_body = rs_body | {"spec": rs_body["spec"] | {"replicas": 2}}
    update_rs = api_client.put("/api/apps/v1/namespaces/default/replicasets/phase1-rs", json=updated_body)
    assert update_rs.status_code in (200, 202)
    assert update_rs.json()["spec"]["replicas"] == 2

    delete_rs = api_client.delete("/api/apps/v1/namespaces/default/replicasets/phase1-rs")
    assert delete_rs.status_code in (200, 202, 204)
