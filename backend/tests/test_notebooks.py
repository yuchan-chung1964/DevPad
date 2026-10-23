import uuid


def test_create_notebook_with_starter_page(client):
    r = client.post("/notebooks", json={"title": "Lecture 1", "template": "lined"})
    assert r.status_code == 201
    nb = r.json()
    assert nb["cover_color"] == "#4A6FA5" and nb["folder_id"] is None
    assert len(nb["page_order"]) == 1
    assert nb["created_at"].endswith("Z") or nb["created_at"].endswith("+00:00")

    page = client.get(f"/notebooks/{nb['id']}/pages/{nb['page_order'][0]}").json()
    assert page["template"] == "lined" and page["cells"] == []


def test_defaults_and_validation(client):
    assert client.post("/notebooks", json={}).json()["title"] == "Untitled"
    assert client.post("/notebooks", json={"cover_color": "blue"}).status_code == 422
    assert client.post("/notebooks", json={"cover_color": "#11223344"}).status_code == 201
    assert client.post("/notebooks", json={"template": "hexagons"}).status_code == 422
    assert client.post("/notebooks", json={"folder_id": str(uuid.uuid4())}).status_code == 404


def test_list_by_folder(client):
    folder = client.post("/folders", json={"name": "Math"}).json()
    client.post("/notebooks", json={"title": "Root"})
    client.post("/notebooks", json={"title": "Algebra", "folder_id": folder["id"]})

    assert [n["title"] for n in client.get("/notebooks").json()] == ["Root"]
    assert [n["title"] for n in client.get("/notebooks", params={"folder_id": folder["id"]}).json()] == ["Algebra"]


def test_update_and_move(client, notebook):
    folder = client.post("/folders", json={"name": "CS"}).json()
    url = f"/notebooks/{notebook['id']}"

    r = client.patch(url, json={"title": "Recursion II", "cover_color": "#000000", "folder_id": folder["id"]})
    assert r.status_code == 200
    assert r.json()["title"] == "Recursion II" and r.json()["folder_id"] == folder["id"]

    assert client.patch(url, json={"folder_id": None}).json()["folder_id"] is None
    assert client.patch(url, json={"title": None}).status_code == 422
    assert client.patch(url, json={"folder_id": str(uuid.uuid4())}).status_code == 404


def test_reorder_pages(client, notebook):
    url = f"/notebooks/{notebook['id']}"
    first = notebook["page_order"][0]
    second = client.post(f"{url}/pages", json={}).json()["id"]
    third = client.post(f"{url}/pages", json={}).json()["id"]

    r = client.patch(url, json={"page_order": [third, first, second]})
    assert r.json()["page_order"] == [third, first, second]
    assert [p["id"] for p in client.get(f"{url}/pages").json()] == [third, first, second]


def test_reorder_rejects_bad_orders(client, notebook):
    url = f"/notebooks/{notebook['id']}"
    first = notebook["page_order"][0]
    second = client.post(f"{url}/pages", json={}).json()["id"]

    for bad in ([first], [first, first], [first, second, second], [first, str(uuid.uuid4())], []):
        assert client.patch(url, json={"page_order": bad}).status_code == 400, bad
    assert client.patch(url, json={"page_order": None}).status_code == 422


def test_delete_notebook_cascades(client, notebook, page_url):
    cell = client.post(f"{page_url}/cells", json={"code": "print(1)"}).json()
    assert client.delete(f"/notebooks/{notebook['id']}").status_code == 204
    assert client.get(f"/notebooks/{notebook['id']}").status_code == 404
    assert client.get(f"{page_url}/cells/{cell['id']}").status_code == 404
    assert client.delete(f"/notebooks/{notebook['id']}").status_code == 404
