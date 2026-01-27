#!/usr/bin/env bash
set -euo pipefail

echo "===> Creating folders"
mkdir -p images/ping
mkdir -p images/health

# -------------------------------------------------
# Ping service
# -------------------------------------------------
echo "===> Writing ping.py"
cat > images/ping/ping.py <<'EOF'
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ping")

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 5000), Handler).serve_forever()
EOF

echo "===> Writing ping Dockerfile"
cat > images/ping/Dockerfile <<'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY ping.py .
CMD ["python", "ping.py"]
EOF

# -------------------------------------------------
# Health service
# -------------------------------------------------
echo "===> Writing health.py"
cat > images/health/health.py <<'EOF'
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import socket

PORT = int(os.environ.get("PORT", "5000"))
POD_NAME = os.environ.get("POD_NAME", socket.gethostname())

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = POD_NAME.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
EOF

echo "===> Writing health Dockerfile"
cat > images/health/Dockerfile <<'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY health.py .
CMD ["python", "health.py"]
EOF

# -------------------------------------------------
# Build images
# -------------------------------------------------
echo "===> Building ping image"
podman build -t ping:latest images/ping

echo "===> Building health image"
podman build -t health:latest images/health

# -------------------------------------------------
# Verify images
# -------------------------------------------------
echo "===> Verifying images"
podman images | grep -E "ping|health" || {
  echo "Images not found after build"
  exit 1
}

# -------------------------------------------------
# Smoke test ping (retry)
# -------------------------------------------------
echo "===> Smoke test ping"
cid=$(podman run -d -P ping:latest)
PORT=$(podman port "$cid" 5000/tcp | cut -d: -f2)

for i in {1..10}; do
  if curl -s "localhost:$PORT" | grep -q ping; then
    echo "ping"
    break
  fi
  sleep 1
done

podman stop "$cid" >/dev/null
podman rm "$cid" >/dev/null

# -------------------------------------------------
# Smoke test health (retry)
# -------------------------------------------------
echo "===> Smoke test health"
cid=$(podman run -d -P health:latest)
PORT=$(podman port "$cid" 5000/tcp | cut -d: -f2)

for i in {1..10}; do
  resp=$(curl -s "localhost:$PORT" || true)
  if [[ -n "$resp" ]]; then
    echo "$resp"
    break
  fi
  sleep 1
done

podman stop "$cid" >/dev/null
podman rm "$cid" >/dev/null

echo
echo "======================================"
echo " Images ready:"
echo "   ping:latest"
echo "   health:latest"
echo "======================================"
