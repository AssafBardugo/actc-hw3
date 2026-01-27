
def test_update_pod_replaces_spec(api_client):
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "pod_update",
            "namespace": "default"
        },
        "spec": {
            "containers": [{
                "name": "demo",
                "image": "alpine:latest"
            }]
        }
    }

    create_pod = api_client.post("/api/v1/namespaces/default/pods", json=pod)
    assert create_pod.status_code == 201

    updated_body = pod | {
        "spec": {
            "containers": [{
                "name": "demo",
                "image": "busybox:latest"
            }]
        }
    }
    update_pod = api_client.put("/api/v1/namespaces/default/pods/pod_update", json=updated_body)
    assert update_pod.status_code in (200, 202)
    assert update_pod.json()["spec"]["containers"][0]["image"] == "busybox:latest"

    get_pod = api_client.get("/api/v1/namespaces/default/pods/pod_update")
    assert get_pod.status_code == 200
    assert get_pod.json()["spec"]["containers"][0]["image"] == "busybox:latest"



def test_update_service_defaults_target_port(api_client):
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "service_update",
            "namespace": "default"
        },
        "spec": {
            "selector": {
                "app": "demo"
            },
            "ports": [{
                "port": 8080,
                "targetPort": 8081
            }]
        }
    }

    create_service = api_client.post("/api/v1/namespaces/default/services", json=service)
    assert create_service.status_code == 201

    updated_body = service | {
        "spec": {
            "selector": {
                "app": "demo"
            },
            "ports": [{
                "port": 9090
            }]
        }
    }
    update_service = api_client.put("/api/v1/namespaces/default/services/service_update", json=updated_body)
    assert update_service.status_code in (200, 202)
    assert update_service.json()["spec"]["ports"][0]["targetPort"] == 9090
