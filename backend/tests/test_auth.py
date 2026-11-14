import jwt
import pytest

from app import config
from tests.conftest import auth_headers, make_token


def test_health_is_public(anon_client):
    assert anon_client.get("/health").status_code == 200


@pytest.mark.parametrize("path", ["/folders", "/notebooks"])
def test_missing_token_is_401(anon_client, path):
    r = anon_client.get(path)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_bad_tokens_are_401(anon_client):
    secret = config.JWT_SECRET
    bad = [
        make_token(exp_in=-10),                                                       # expired
        make_token(secret="x" * 40),                                                  # wrong signature
        make_token(audience="someone-else"),                                          # wrong audience
        jwt.encode({"sub": "u", "aud": "devpad"}, secret, algorithm="HS256"),         # no exp
        jwt.encode({"aud": "devpad", "exp": 9999999999}, secret, algorithm="HS256"),  # no sub
        jwt.encode({"sub": "u", "aud": "devpad", "exp": 9999999999}, None, algorithm="none"),  # unsigned
        "not-a-jwt",
    ]
    for token in bad:
        r = anon_client.get("/folders", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, token


def test_first_request_creates_the_user(client):
    from app import models
    from app.db import SessionLocal

    assert client.get("/folders").status_code == 200
    with SessionLocal() as db:
        assert db.get(models.User, "user-a") is not None


def test_no_auth_configured_fails_closed(anon_client, monkeypatch):
    monkeypatch.setattr(config, "JWT_SECRET", None)
    monkeypatch.setattr(config, "JWT_JWKS_URL", None)
    assert anon_client.get("/folders", headers=auth_headers()).status_code == 503


def test_users_cannot_see_or_touch_each_others_data(client, other_client):
    folder = client.post("/folders", json={"name": "mine"}).json()
    nb = client.post("/notebooks", json={"title": "mine", "folder_id": folder["id"]}).json()
    page = nb["page_order"][0]
    base = f"/notebooks/{nb['id']}/pages/{page}"
    cell = client.post(f"{base}/cells", json={"code": "x = 1"}).json()

    # b sees none of it
    assert other_client.get("/folders").json() == []
    assert other_client.get("/notebooks", params={"folder_id": folder["id"]}).json() == []

    # and gets 404 (not 403) on every route that names it
    assert other_client.get(f"/folders/{folder['id']}").status_code == 404
    assert other_client.patch(f"/folders/{folder['id']}", json={"name": "x"}).status_code == 404
    assert other_client.delete(f"/folders/{folder['id']}").status_code == 404
    assert other_client.get(f"/notebooks/{nb['id']}").status_code == 404
    assert other_client.patch(f"/notebooks/{nb['id']}", json={"title": "x"}).status_code == 404
    assert other_client.delete(f"/notebooks/{nb['id']}").status_code == 404
    assert other_client.get(f"/notebooks/{nb['id']}/pages").status_code == 404
    assert other_client.get(base).status_code == 404
    assert other_client.post(f"/notebooks/{nb['id']}/pages", json={}).status_code == 404
    assert other_client.get(f"{base}/cells").status_code == 404
    assert other_client.post(f"{base}/cells", json={}).status_code == 404
    assert other_client.get(f"{base}/cells/{cell['id']}").status_code == 404
    assert other_client.patch(f"{base}/cells/{cell['id']}", json={"code": "pwned"}).status_code == 404
    assert other_client.put(f"{base}/cells/{cell['id']}/strokes", json=[]).status_code == 404

    # b can't file anything into a's folder either
    assert other_client.post("/notebooks", json={"title": "x", "folder_id": folder["id"]}).status_code == 404
    assert other_client.post("/folders", json={"name": "x", "parent_id": folder["id"]}).status_code == 404

    # a's data is untouched
    assert client.get(f"{base}/cells/{cell['id']}").json()["code"] == "x = 1"


def test_rate_limit_per_user_and_bucket(client, other_client, monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_READ", 3)
    monkeypatch.setattr(config, "RATE_LIMIT_WRITE", 2)

    for _ in range(3):
        assert client.get("/folders").status_code == 200
    blocked = client.get("/folders")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1

    # the other user and the write bucket are unaffected
    assert other_client.get("/folders").status_code == 200
    assert client.post("/folders", json={"name": "a"}).status_code == 201
    assert client.post("/folders", json={"name": "b"}).status_code == 201
    assert client.post("/folders", json={"name": "c"}).status_code == 429


def test_anonymous_requests_are_rate_limited(anon_client, monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_ANON", 2)
    assert anon_client.get("/folders").status_code == 401
    assert anon_client.get("/folders", headers={"Authorization": "Bearer junk"}).status_code == 401
    assert anon_client.get("/folders").status_code == 429


def test_oversized_body_is_413(client, monkeypatch):
    monkeypatch.setattr("app.main.MAX_BODY_BYTES", 100)
    assert client.post("/folders", json={"name": "x" * 150}).status_code == 413


def test_input_limits(client, page_url):
    cells = f"{page_url}/cells"
    assert client.post(cells, json={"code": "x" * (config.MAX_CODE_CHARS + 1)}).status_code == 422
    too_many_points = [{"x": 0, "y": 0}] * (config.MAX_POINTS_PER_STROKE + 1)
    assert client.post(cells, json={"strokes": [{"points": too_many_points}]}).status_code == 422


def test_quotas(client, page_url, monkeypatch):
    monkeypatch.setattr(config, "MAX_FOLDERS", 1)
    monkeypatch.setattr(config, "MAX_CELLS_PER_PAGE", 1)
    monkeypatch.setattr(config, "MAX_STROKES_PER_CELL", 1)
    assert client.post("/folders", json={"name": "a"}).status_code == 201
    assert client.post("/folders", json={"name": "b"}).status_code == 403

    cell = client.post(f"{page_url}/cells", json={}).json()
    assert client.post(f"{page_url}/cells", json={}).status_code == 403

    stroke = {"points": [{"x": 0, "y": 0}]}
    url = f"{page_url}/cells/{cell['id']}/strokes"
    assert client.post(url, json=[stroke]).status_code == 201
    assert client.post(url, json=[stroke]).status_code == 413


def test_pagination(client):
    for i in range(3):
        client.post("/folders", json={"name": f"f{i}"})

    def names(**params):
        return [f["name"] for f in client.get("/folders", params=params).json()]

    assert names(limit=2) == ["f0", "f1"]
    assert names(limit=2, offset=2) == ["f2"]
    assert client.get("/folders", params={"limit": 0}).status_code == 422
