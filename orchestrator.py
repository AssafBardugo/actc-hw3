#!/usr/bin/env python3
"""
Orchestrator Entry Point

Responsibility:
- Initialize shared state (ResourceStore, PodmanRuntime)
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

from actual_state.store import ResourceStore
from actual_state.types import ResourceType
from api_runtime.routes import register_routes
from api_runtime.podman import PodmanRuntime
from controllers.base import Controller
from controllers.pod_controller import PodController
from controllers.replicaset_controller import ReplicaSetController
from controllers.service_controller import ServiceController


RECONCILE_INTERVAL = 3
SERVICE_PROXY_REFRESH = 1.0


class ServiceProxyManager:
    def __init__(self, app: FastAPI, store: ResourceStore, host: str, api_port: int) -> None:
        self.app = app
        self.store = store
        self.host = host
        self.api_port = api_port
        self._servers: dict[int, uvicorn.Server] = {}
        self._threads: dict[int, threading.Thread] = {}
        self._lock = threading.Lock()

    def _desired_ports(self) -> set[int]:
        ports: set[int] = set()
        services = self.store.list_by_kind(ResourceType.SERVICE)
        for svc_map in services.values():
            for svc in svc_map.values():
                spec = svc.spec or {}
                svc_ports = spec.get("ports", [])
                if not svc_ports:
                    continue
                port = svc_ports[0].get("port")
                if isinstance(port, int) and port != self.api_port:
                    ports.add(port)
        return ports

    def _start_server(self, port: int) -> None:
        config = uvicorn.Config(self.app, host=self.host, port=port, log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        self._servers[port] = server
        self._threads[port] = thread
        thread.start()

    def _stop_server(self, port: int) -> None:
        server = self._servers.pop(port, None)
        thread = self._threads.pop(port, None)
        if server:
            server.should_exit = True
        if thread:
            thread.join(timeout=2)

    def run(self) -> None:
        while True:
            desired = self._desired_ports()
            with self._lock:
                current = set(self._servers.keys())
                for port in desired - current:
                    self._start_server(port)
                for port in current - desired:
                    self._stop_server(port)
            time.sleep(SERVICE_PROXY_REFRESH)

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
    service_controller = ServiceController(resource_store)

    threading.Thread(target=controller_loop, args=(pod_controller,), daemon=True).start()
    threading.Thread(target=controller_loop, args=(replicaset_controller,), daemon=True).start()
    threading.Thread(target=controller_loop, args=(service_controller,), daemon=True).start()

    app = FastAPI()
    register_routes(app, resource_store, podman_runtime)

    proxy_manager = ServiceProxyManager(app, resource_store, args.host, args.port)
    threading.Thread(target=proxy_manager.run, daemon=True).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
