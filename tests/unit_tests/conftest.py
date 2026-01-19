import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from runtime.workers import WorkerRuntime
from core.store import ResourceStore
from api.routes import register_routes


@pytest.fixture
def runtime_worker():
    return WorkerRuntime()


@pytest.fixture
def resource_store():
    return ResourceStore()


@pytest.fixture
def app(resource_store):
    app = FastAPI()
    register_routes(app, resource_store)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)

