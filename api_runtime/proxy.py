import threading
import time
import uvicorn
from fastapi import FastAPI

from actual_state.types import ResourceType
from actual_state.store import ResourceStore


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
                port = svc.spec["ports"][0]["port"]
                if port != self.api_port:
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
            time.sleep(1)
