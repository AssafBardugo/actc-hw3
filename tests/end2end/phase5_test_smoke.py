import os
import subprocess
import sys
import time

import httpx
import pytest

pytestmark = [pytest.mark.phase5, pytest.mark.e2e]


def _wait_for_healthz(base_url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{base_url}/healthz", timeout=1.0)
            if resp.status_code == 200:
                return
            last_err = f"status {resp.status_code}"
        except Exception as exc:  # pragma: no cover - best-effort wait loop
            last_err = str(exc)
        time.sleep(0.5)
    raise AssertionError(f"healthz did not become ready: {last_err}")


def test_phase5_smoke_orchestrator_starts(e2e_base_url):
    """
    Optional Phase 5 smoke: orchestrator still boots cleanly and serves /healthz.
    This does not enforce new features—just guards against regressions in polish phase.
    """
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "orchestrator.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        _wait_for_healthz(e2e_base_url)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
