import os

# Must be set before the app is imported: tests run against a throwaway in-memory database.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-0123"
os.environ["JWT_AUDIENCE"] = "devpad"

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base
from app.ratelimit import limiter


def make_token(sub="user-a", *, exp_in=3600, secret=None, audience="devpad", algorithm="HS256"):
    claims = {"sub": sub, "aud": audience, "exp": int(time.time()) + exp_in}
    return jwt.encode(claims, secret or os.environ["JWT_SECRET"], algorithm=algorithm)


def auth_headers(sub="user-a", **kwargs):
    return {"Authorization": f"Bearer {make_token(sub, **kwargs)}"}


@pytest.fixture
def anon_client():
    """A client with no credentials."""
    Base.metadata.drop_all(engine)
    limiter.reset()
    with TestClient(app) as c:  # runs the lifespan, which creates the tables
        yield c


@pytest.fixture
def client(anon_client):
    """Signed in as user-a."""
    anon_client.headers.update(auth_headers("user-a"))
    return anon_client


@pytest.fixture
def other_client(client):
    """A second client on the same app and database, signed in as user-b."""
    with TestClient(app, headers=auth_headers("user-b")) as c:
        yield c


@pytest.fixture
def notebook(client):
    return client.post("/notebooks", json={"title": "Recursion"}).json()


@pytest.fixture
def page_url(notebook):
    return f"/notebooks/{notebook['id']}/pages/{notebook['page_order'][0]}"
