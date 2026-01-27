import subprocess
import time
import threading
from typing import Dict

from fastapi import FastAPI

from actual_state.types import ResourceType
from actual_state.store import ResourceStore


class ServiceProxyManager:

    def __init__(self, app: FastAPI, store: ResourceStore, host: str, api_port: int) -> None:
        self.app = app
        self.store = store
        self.host = host
        self.api_port = api_port

        self._servers: Dict[int, subprocess.Popen] = {}
        self._lock = threading.Lock()


    def _desired_ports(self) -> set[int]:
        ports: set[int] = set()

        services = self.store.list_by_kind(ResourceType.SERVICE)
        for svc_map in services.values():
            for svc in svc_map.values():
                try:
                    port = svc.spec["ports"][0]["port"]
                    if port != self.api_port:
                        ports.add(port)
                except Exception:
                    continue
        return ports


    def _start_server(self, port: int) -> None:
        print(f"[proxy] Starting service proxy on port {port}")

        proc = subprocess.Popen(
            [ "uvicorn", "orchestrator:app", "--host", self.host, "--port", str(port), "--log-level", "warning"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self._servers[port] = proc


    def _stop_server(self, port: int) -> None:
        proc = self._servers.pop(port, None)
        if not proc:
            return

        print(f"[proxy] Stopping service proxy on port {port}")
        proc.terminate()

        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


    def run(self) -> None:
        while True:
            desired = self._desired_ports()

            with self._lock:
                current = set(self._servers.keys())

                # start new ports
                for port in desired - current:
                    self._start_server(port)

                # stop removed ports
                for port in current - desired:
                    self._stop_server(port)
            time.sleep(1)
