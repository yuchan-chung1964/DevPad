import os

# Must be set before the app is imported: tests run against a throwaway in-memory database.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # runs the lifespan, which creates the tables
        yield c


@pytest.fixture
def notebook(client):
    return client.post("/notebooks", json={"title": "Recursion"}).json()


@pytest.fixture
def page_url(notebook):
    return f"/notebooks/{notebook['id']}/pages/{notebook['page_order'][0]}"
