import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str = "text/plain") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self._send(200, b"ok")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)
        self._send(200, b"true")

    def log_message(self, fmt: str, *args) -> None:  # quiet default HTTP logs
        return


def main() -> None:
    port = int(os.environ.get("PORT", "5000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"health server listening on {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
