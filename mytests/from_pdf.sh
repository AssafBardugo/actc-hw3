#!/bin/bash

export ORCHESTRATOR=localhost:3000

curl -X POST https://localhost:3000/api/apps/v1/namespaces/default/replicasets   \
        -H "Content-Type: application/json" \
        -d '{
            "apiVersion": "apps/v1",
            "kind": "ReplicaSet",
            "metadata": {
                "name": "health-replicaset"
            },
            "spec": {
                "replicas": 3,
                "selector": {
                    "name": "health"
                },
                "template": {
                    "metadata": {
                        "app": "health"
                    },
                    "spec": {
                        "containers": [{
                            "name": "health",
                            "image": "health:latest"
                        }]
                    },
                }
            }
        }'


curl -X POST https://localhost:3000/api/v1/namespaces/default/pods   \
        -H "Content-Type: application/json" \
        -d '{
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "health-service"
            },
            "spec": {
                "selector": {
                    "app": "health"
                },
                "ports": [{
                    "protocol": "TCP",
                    "port": 2000,
                    "targetPort": 5000
                }],
                "type": "ClusterIP"
            }
        }'


curl -X POST https://localhost:3000/api/v1/namespaces/default/pods   \
        -H "Content-Type: application/json" \
        -d '{
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "ping"
            },
            "spec": {
                "containers": [{
                    "name": "ping",
                    "image": "ping:latest",
                    "env": {
                        "HEALTH_SERVICE": "health-service:2000"
                    }
                }]
            }
        }'


# If we then then ran this, it would cause 2 additional replicas to be created:
curl -X PUT https://localhost:3000/api/apps/v1/namespaces/default/replicasets/health-replicaset  \
        -H "Content-Type: application/json" \
        -d '{
            "apiVersion": "apps/v1",
            "kind": "ReplicaSet",
            "metadata": {
                "name": "health-replicaset"
            },
            "spec": {
                "replicas": 5,
                "selector": {
                    "name": "health"
                },
                "template": {
                    "metadata": {
                        "app": "health"
                    },
                    "spec": {
                        "containers": [{
                            "name": "health",
                            "image": "health:latest"
                        }]
                    }
                }
            }
        }'
