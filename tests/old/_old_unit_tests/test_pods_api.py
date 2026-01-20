def test_create_pod(client):
    payload = {
        "kind": "pod",
        "metadata": {
            "name": "test-pod",
            "namespace": "default"
        },
        "spec": {
            "containers": [
                {"name": "c1", "image": "health"}
            ]
        }
    }

    resp = client.post("/api/v1/namespaces/default/pods", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["metadata"]["name"] == "test-pod"


def test_list_pods(client):
    resp = client.get("/api/v1/namespaces/default/pods")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)


def test_get_pod_not_found(client):
    resp = client.get("/api/v1/namespaces/default/pods/nope")
    assert resp.status_code == 404


def test_delete_pod(client):
    payload = {
        "kind": "pod",
        "metadata": {"name": "delete-me"},
        "spec": {"containers": []}
    }

    client.post("/api/v1/namespaces/default/pods", json=payload)
    resp = client.delete("/api/v1/namespaces/default/pods/delete-me")
    assert resp.status_code == 200

    resp = client.get("/api/v1/namespaces/default/pods/delete-me")
    assert resp.status_code == 404

