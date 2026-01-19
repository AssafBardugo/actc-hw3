#!/usr/bin/env python3
"""
Orchestrator Entry Point

Responsibility:
- Initialize shared state (ResourceStore, WorkerRuntime)
- Instantiate and start controllers
- Start the HTTP API server

Important:
- No business logic is implemented here
- No reconciliation logic is implemented here
- This file acts as the system entry point only

DESIGN NOTE:
orchestrator.py is responsible only for wiring components together:
- initializing stores and runtimes
- starting controllers
- starting the HTTP API
"""
import argparse
import threading
import time
import uvicorn
from fastapi import FastAPI

from api.routes import register_routes
from core.store import ResourceStore
from runtime.podman import PodmanRuntime
from controllers.base import Controller
from controllers.pod_controller import PodController
from controllers.replicaset_controller import ReplicaSetController
from controllers.service_controller import ServiceController


RECONCILE_INTERVAL = 1

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
    runtime_worker = WorkerRuntime()

    pod_controller = PodController(resource_store, runtime_worker)
    replicaset_controller = ReplicaSetController(resource_store)
    service_controller = ServiceController(resource_store)

    threading.Thread(target=controller_loop, args=(pod_controller,), daemon=True).start()
    threading.Thread(target=controller_loop, args=(replicaset_controller,), daemon=True).start()
    threading.Thread(target=controller_loop, args=(service_controller,), daemon=True).start()

    app = FastAPI()
    register_routes(app, resource_store)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
