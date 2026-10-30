import uuid


def stroke(**overrides):
    return {"points": [{"x": 0, "y": 0}, {"x": 10, "y": 5, "pressure": 0.5}], **overrides}


def test_create_cell_defaults(client, page_url):
    r = client.post(f"{page_url}/cells", json={})
    assert r.status_code == 201
    cell = r.json()
    assert cell["language"] == "python" and cell["code"] == "" and cell["strokes"] == []


def test_cell_kinds(client, page_url):
    assert client.post(f"{page_url}/cells", json={}).json()["kind"] == "code"   # existing default

    note = client.post(f"{page_url}/cells", json={"kind": "text", "language": "markdown", "code": "- [ ] buy milk"})
    assert note.status_code == 201
    assert note.json()["kind"] == "text" and note.json()["code"] == "- [ ] buy milk"

    ink = client.post(f"{page_url}/cells", json={"kind": "ink", "strokes": [stroke()]}).json()
    assert ink["kind"] == "ink" and len(ink["strokes"]) == 1

    kinds = [c["kind"] for c in client.get(f"{page_url}/cells").json()]
    assert kinds == ["code", "text", "ink"]

    assert client.post(f"{page_url}/cells", json={"kind": "image"}).status_code == 422
    # The kind is fixed once created: PATCH ignores it rather than changing it.
    url = f"{page_url}/cells/{note.json()['id']}"
    assert client.patch(url, json={"kind": "ink", "code": "done"}).json()["kind"] == "text"


def test_create_cell_with_content_and_position(client, page_url):
    a = client.post(f"{page_url}/cells", json={"code": "a = 1"}).json()
    b = client.post(f"{page_url}/cells", json={"code": "b = 2", "language": "javascript",
                                                "strokes": [stroke()], "position": 0}).json()
    assert b["language"] == "javascript" and len(b["strokes"]) == 1

    page = client.get(page_url).json()
    assert [c["id"] for c in page["cells"]] == [b["id"], a["id"]]
    assert [c["id"] for c in client.get(f"{page_url}/cells").json()] == [b["id"], a["id"]]
    assert client.post(f"{page_url}/cells", json={"position": 9}).status_code == 400


def test_update_cell(client, page_url):
    cell = client.post(f"{page_url}/cells", json={}).json()
    url = f"{page_url}/cells/{cell['id']}"

    r = client.patch(url, json={"code": "def f(n):\n    return n", "language": "python"})
    assert r.status_code == 200
    assert r.json()["code"] == "def f(n):\n    return n"
    assert r.json()["updated_at"] > cell["updated_at"]
    assert client.get(url).json()["code"] == "def f(n):\n    return n"

    assert client.patch(url, json={"code": None}).status_code == 422
    assert client.patch(url, json={"language": ""}).status_code == 422


def test_reorder_cells(client, page_url):
    ids = [client.post(f"{page_url}/cells", json={}).json()["id"] for _ in range(3)]
    r = client.patch(page_url, json={"cell_order": [ids[2], ids[0], ids[1]]})
    assert [c["id"] for c in r.json()["cells"]] == [ids[2], ids[0], ids[1]]
    assert client.patch(page_url, json={"cell_order": ids[:2]}).status_code == 400


def test_delete_cell(client, page_url):
    a, b, c = (client.post(f"{page_url}/cells", json={}).json()["id"] for _ in range(3))
    assert client.delete(f"{page_url}/cells/{b}").status_code == 204
    assert client.get(f"{page_url}/cells/{b}").status_code == 404
    assert [x["id"] for x in client.get(page_url).json()["cells"]] == [a, c]
    # A page may end up with no cells
    client.delete(f"{page_url}/cells/{a}")
    client.delete(f"{page_url}/cells/{c}")
    assert client.get(page_url).json()["cells"] == []


def test_cell_scoped_to_its_page(client, notebook, page_url):
    cell = client.post(f"{page_url}/cells", json={}).json()
    other_page = client.post(f"/notebooks/{notebook['id']}/pages", json={}).json()
    other_url = f"/notebooks/{notebook['id']}/pages/{other_page['id']}"
    assert client.get(f"{other_url}/cells/{cell['id']}").status_code == 404
    assert client.get(f"{page_url}/cells/{uuid.uuid4()}").status_code == 404


def test_add_replace_and_erase_strokes(client, page_url):
    cell = client.post(f"{page_url}/cells", json={}).json()
    url = f"{page_url}/cells/{cell['id']}/strokes"

    r = client.post(url, json=[stroke(), stroke(tool="highlighter", color="#FFB300", width=24)])
    assert r.status_code == 201
    strokes = r.json()["strokes"]
    assert len(strokes) == 2 and strokes[1]["tool"] == "highlighter"
    assert strokes[0]["points"][1] == {"x": 10, "y": 5, "t": 0.0, "pressure": 0.5}

    assert len(client.post(url, json=[stroke()]).json()["strokes"]) == 3

    assert client.delete(f"{url}/{strokes[0]['id']}").status_code == 204
    remaining = client.get(f"{page_url}/cells/{cell['id']}").json()["strokes"]
    assert [s["id"] for s in remaining][0] == strokes[1]["id"] and len(remaining) == 2
    assert client.delete(f"{url}/{strokes[0]['id']}").status_code == 404

    r = client.put(url, json=[stroke()])
    assert r.status_code == 200 and len(r.json()["strokes"]) == 1
    assert len(client.put(url, json=[]).json()["strokes"]) == 0


def test_stroke_ids_are_preserved(client, page_url):
    cell = client.post(f"{page_url}/cells", json={}).json()
    sid = str(uuid.uuid4())
    r = client.put(f"{page_url}/cells/{cell['id']}/strokes", json=[stroke(id=sid)])
    assert r.json()["strokes"][0]["id"] == sid


def test_stroke_validation(client, page_url):
    cell = client.post(f"{page_url}/cells", json={}).json()
    url = f"{page_url}/cells/{cell['id']}/strokes"
    assert client.post(url, json=[stroke(color="red")]).status_code == 422
    assert client.post(url, json=[stroke(tool="crayon")]).status_code == 422
    assert client.post(url, json=[stroke(width=0)]).status_code == 422
    assert client.post(url, json=[{"points": [{"x": 0, "y": 0, "pressure": 2}]}]).status_code == 422


def test_strokes_persist_across_sessions(client, page_url):
    """Strokes go through a real DB round-trip, not just the in-memory object."""
    from app.db import SessionLocal
    from app import models

    cell = client.post(f"{page_url}/cells", json={"strokes": [stroke()]}).json()
    with SessionLocal() as db:
        stored = db.get(models.Cell, uuid.UUID(cell["id"]))
        assert len(stored.strokes) == 1 and stored.strokes[0]["tool"] == "pen"
