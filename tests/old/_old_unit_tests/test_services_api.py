def test_create_service(client):
    payload = {
        "kind": "service",
        "metadata": {
            "name": "svc",
            "namespace": "default"
        },
        "spec": {
            "selector": {"app": "x"},
            "ports": [{"port": 80, "targetPort": 8080}]
        }
    }

    resp = client.post("/api/v1/namespaces/default/services", json=payload)
    assert resp.status_code == 201


def test_list_services(client):
    resp = client.get("/api/v1/namespaces/default/services")
    assert resp.status_code == 200
    assert "items" in resp.json()

