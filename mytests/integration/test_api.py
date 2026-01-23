import pytest

def test_basic_api(api_client):
    """
    test the requests:
    pod:
    GET     /api/v1/namespaces/{namespace}/pods
    POST    /api/v1/namespaces/{namespace}/pods
    GET     /api/v1/namespaces/{namespace}/pods/{podName}
    DELETE  /api/v1/namespaces/{namespace}/pods/{podName}

    service:
    POST    /api/v1/namespaces/{namespace}/services
    GET     /api/v1/namespaces/{namespace}/services
    """

    pod_1 = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "pod_1",
            "namespace": "default"
        },
        "spec": {
            "containers": [{
                "name": "demo", 
                "image": "alpine:latest"
            }]
        }
    }

    service_1 = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "service_1", 
            "namespace": "default"
        },
        "spec": {
            "selector": {
                "app": "demo"
            }, 
            "ports": [{
                "port": 80, 
                "targetPort": 8080
            }]
        }
    }

    create_pod = api_client.post("/api/v1/namespaces/default/pods", json=pod_1)
    assert create_pod.status_code == 201

    list_pods = api_client.get("/api/v1/namespaces/default/pods")
    assert list_pods.status_code == 200
    assert any(item["metadata"]["name"] == "pod_1" for item in list_pods.json()["items"])

    get_pod = api_client.get("/api/v1/namespaces/default/pods/pod_1")
    assert get_pod.status_code == 200
    assert get_pod.json()["metadata"]["name"] == "pod_1"

    create_service = api_client.post("/api/v1/namespaces/default/services", json=service_1)
    assert create_service.status_code == 201

    list_services = api_client.get("/api/v1/namespaces/default/services")
    assert list_services.status_code == 200
    assert any(item["metadata"]["name"] == "service_1" for item in list_services.json()["items"])

    delete_pod = api_client.delete("/api/v1/namespaces/default/pods/pod_1")
    assert delete_pod.status_code in (200, 202, 204)

    missing = api_client.get("/api/v1/namespaces/default/pods/pod_1")
    assert missing.status_code == 404


def test_api_supports_replicaset_crud_and_update(api_client):
    """
    test the requests:
    replicaset:
    POST    /api/apps/v1/namespaces/{namespace}/replicasets
    GET     /api/apps/v1/namespaces/{namespace}/replicasets
    PUT     /api/apps/v1/namespaces/{namespace}/replicasets/{rsName}
    DELETE  /api/apps/v1/namespaces/{namespace}/replicasets/{rsName}
    """

    rs_1 = {
        "apiVersion": "apps/v1",
        "kind": "ReplicaSet",
        "metadata": {
            "name": "rs_1", 
            "namespace": "default"
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "app": "demo"
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "demo"
                    }
                },
                "spec": {
                    "containers": [{
                        "name": "demo", 
                        "image": "alpine:latest"
                    }]
                }
            }
        }
    }

    create_rs = api_client.post("/api/apps/v1/namespaces/default/replicasets", json=rs_1)
    assert create_rs.status_code == 201

    list_rs = api_client.get("/api/apps/v1/namespaces/default/replicasets")
    assert list_rs.status_code == 200
    assert any(item["metadata"]["name"] == "rs_1" for item in list_rs.json()["items"])

    updated_body = rs_1 | {"spec": rs_1["spec"] | {"replicas": 2}}
    update_rs = api_client.put("/api/apps/v1/namespaces/default/replicasets/rs_1", json=updated_body)
    assert update_rs.status_code in (200, 202)
    assert update_rs.json()["spec"]["replicas"] == 2

    delete_rs = api_client.delete("/api/apps/v1/namespaces/default/replicasets/rs_1")
    assert delete_rs.status_code in (200, 202, 204)
