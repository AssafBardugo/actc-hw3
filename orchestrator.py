#!/usr/bin/env python3
import argparse
import threading
import time
import uvicorn
from fastapi import FastAPI

from actual_state.store import ResourceStore
from controllers.base import Controller
from controllers.pod_controller import PodController
from controllers.replicaset_controller import ReplicaSetController
from controllers.service_controller import ServiceController
from api_runtime.podman import PodmanRuntime
from api_runtime.routes import register_routes
from api_runtime.proxy import ServiceProxyManager

app = FastAPI()

RECONCILE_INTERVAL = 3

def controller_loop(controller: Controller):
    while True:
        try:
            controller.reconcile()
        except Exception as e:
            print(f"{controller.__class__.__name__}: {e}")
        time.sleep(RECONCILE_INTERVAL)


def main():
    parser = argparse.ArgumentParser(description="Orchestrator API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind to")
    args = parser.parse_args()
    print(f"Starting Orchestrator API on {args.host}:{args.port}")

    resource_store = ResourceStore()
    podman_runtime = PodmanRuntime(resource_store)

    pod_controller = PodController(resource_store, podman_runtime)
    replicaset_controller = ReplicaSetController(resource_store)
    service_controller = ServiceController(resource_store, podman_runtime)

    threading.Thread(target=controller_loop, args=(pod_controller,), daemon=True).start()
    threading.Thread(target=controller_loop, args=(replicaset_controller,), daemon=True).start()
    threading.Thread(target=controller_loop, args=(service_controller,), daemon=True).start()

    register_routes(app, resource_store, podman_runtime)

    proxy_manager = ServiceProxyManager(app, resource_store, args.host, args.port)
    threading.Thread(target=proxy_manager.run, daemon=True).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
