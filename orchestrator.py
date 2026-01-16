#!/usr/bin/env python3
"""
Orchestrator Entry Point

Responsibility:
- Compose and wire together all core components of the system.
- Create the FastAPI application.
- Initialize the ResourceStore.
- Initialize and start all controllers.
- Start background reconciliation loops.
- Start the HTTP server (uvicorn).

Important:
- MUST NOT contain business logic.
- MUST NOT perform reconciliation itself.
- MUST NOT directly manipulate resources or workers.
- Acts purely as the system bootstrap / main().

DESIGN NOTE:

orchestrator.py is responsible only for wiring components together:
- initializing stores and runtimes
- starting controllers
- starting the HTTP API
"""

import uvicorn


def main():
    """Run the orchestrator server"""
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrator API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind to")
    args = parser.parse_args()

    print(f"Starting Orchestrator API on {args.host}:{args.port}")
    #uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
