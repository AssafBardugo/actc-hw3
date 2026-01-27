#!/usr/bin/env bash
set -e

./setup_images.sh

uv run orchestrator.py >/dev/null 2>&1 &
ORCH_PID=$!

echo "Started orchestrator.py (pid=$ORCH_PID)"
sleep 1

cleanup() {
    echo "Stopping orchestrator.py..."
    kill $ORCH_PID 2>/dev/null || true
}
trap cleanup EXIT

make