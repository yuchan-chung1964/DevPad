import uuid


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_list_folders(client):
    root = client.post("/folders", json={"name": "CS Notes"})
    assert root.status_code == 201
    root = root.json()
    child = client.post("/folders", json={"name": "Trees", "parent_id": root["id"]}).json()

    assert [f["name"] for f in client.get("/folders").json()] == ["CS Notes"]
    assert [f["id"] for f in client.get("/folders", params={"parent_id": root["id"]}).json()] == [child["id"]]
    assert client.get(f"/folders/{child['id']}").json()["parent_id"] == root["id"]


def test_name_is_trimmed_and_required(client):
    assert client.post("/folders", json={"name": "  Math  "}).json()["name"] == "Math"
    assert client.post("/folders", json={"name": "   "}).status_code == 422
    assert client.post("/folders", json={}).status_code == 422


def test_unknown_parent_and_folder_404(client):
    assert client.post("/folders", json={"name": "x", "parent_id": str(uuid.uuid4())}).status_code == 404
    assert client.get(f"/folders/{uuid.uuid4()}").status_code == 404


def test_rename_and_move_to_root(client):
    a = client.post("/folders", json={"name": "A"}).json()
    b = client.post("/folders", json={"name": "B", "parent_id": a["id"]}).json()

    r = client.patch(f"/folders/{b['id']}", json={"name": "B2", "parent_id": None})
    assert r.status_code == 200
    assert r.json()["name"] == "B2" and r.json()["parent_id"] is None
    assert r.json()["updated_at"] >= b["updated_at"]


def test_name_cannot_be_null(client):
    a = client.post("/folders", json={"name": "A"}).json()
    assert client.patch(f"/folders/{a['id']}", json={"name": None}).status_code == 422


def test_cannot_create_cycles(client):
    a = client.post("/folders", json={"name": "A"}).json()
    b = client.post("/folders", json={"name": "B", "parent_id": a["id"]}).json()
    c = client.post("/folders", json={"name": "C", "parent_id": b["id"]}).json()

    assert client.patch(f"/folders/{a['id']}", json={"parent_id": a["id"]}).status_code == 400
    assert client.patch(f"/folders/{a['id']}", json={"parent_id": c["id"]}).status_code == 400
    # Moving sideways or up is fine
    assert client.patch(f"/folders/{c['id']}", json={"parent_id": a["id"]}).status_code == 200


def test_delete_only_empty_folders(client):
    a = client.post("/folders", json={"name": "A"}).json()
    b = client.post("/folders", json={"name": "B", "parent_id": a["id"]}).json()
    nb = client.post("/notebooks", json={"title": "N", "folder_id": b["id"]}).json()

    assert client.delete(f"/folders/{a['id']}").status_code == 409
    assert client.delete(f"/folders/{b['id']}").status_code == 409
    client.delete(f"/notebooks/{nb['id']}")
    assert client.delete(f"/folders/{b['id']}").status_code == 204
    assert client.delete(f"/folders/{a['id']}").status_code == 204
    assert client.get(f"/folders/{a['id']}").status_code == 404
