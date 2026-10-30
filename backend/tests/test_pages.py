import uuid


def test_create_page_at_position(client, notebook):
    url = f"/notebooks/{notebook['id']}/pages"
    first = notebook["page_order"][0]

    end = client.post(url, json={"template": "grid"})
    assert end.status_code == 201 and end.json()["template"] == "grid"
    front = client.post(url, json={"position": 0}).json()

    order = client.get(f"/notebooks/{notebook['id']}").json()["page_order"]
    assert order == [front["id"], first, end.json()["id"]]


def test_position_out_of_range(client, notebook):
    url = f"/notebooks/{notebook['id']}/pages"
    assert client.post(url, json={"position": 5}).status_code == 400
    assert client.post(url, json={"position": -1}).status_code == 422
    assert client.post(url, json={"position": 1}).status_code == 201  # == len is allowed (append)


def test_list_pages_summary(client, notebook, page_url):
    client.post(f"{page_url}/cells", json={})
    client.post(f"{page_url}/cells", json={})
    pages = client.get(f"/notebooks/{notebook['id']}/pages").json()
    assert len(pages) == 1
    assert pages[0]["cell_count"] == 2 and "cells" not in pages[0]


def test_page_title(client, notebook, page_url):
    assert client.get(page_url).json()["title"] == ""          # untitled by default

    created = client.post(f"/notebooks/{notebook['id']}/pages", json={"title": "  Lecture 3  "}).json()
    assert created["title"] == "Lecture 3"                      # whitespace is trimmed

    r = client.patch(page_url, json={"title": "Big-O notes"})
    assert r.status_code == 200 and r.json()["title"] == "Big-O notes"
    assert client.patch(page_url, json={"title": ""}).json()["title"] == ""   # can be cleared

    titles = [p["title"] for p in client.get(f"/notebooks/{notebook['id']}/pages").json()]
    assert titles == ["", "Lecture 3"]

    assert client.patch(page_url, json={"title": None}).status_code == 422
    assert client.patch(page_url, json={"title": "x" * 201}).status_code == 422


def test_update_template_touches_notebook(client, notebook, page_url):
    r = client.patch(page_url, json={"template": "dotted"})
    assert r.status_code == 200 and r.json()["template"] == "dotted"
    nb = client.get(f"/notebooks/{notebook['id']}").json()
    assert nb["updated_at"] > notebook["updated_at"]
    assert client.patch(page_url, json={"template": None}).status_code == 422


def test_page_scoped_to_its_notebook(client, notebook, page_url):
    other = client.post("/notebooks", json={}).json()
    page_id = notebook["page_order"][0]
    assert client.get(f"/notebooks/{other['id']}/pages/{page_id}").status_code == 404
    assert client.get(f"/notebooks/{notebook['id']}/pages/{uuid.uuid4()}").status_code == 404
    assert client.get(f"/notebooks/{uuid.uuid4()}/pages").status_code == 404


def test_delete_page_keeps_at_least_one(client, notebook, page_url):
    assert client.delete(page_url).status_code == 409

    url = f"/notebooks/{notebook['id']}/pages"
    second = client.post(url, json={}).json()["id"]
    third = client.post(url, json={}).json()["id"]
    assert client.delete(page_url).status_code == 204
    assert client.get(page_url).status_code == 404
    assert client.get(f"/notebooks/{notebook['id']}").json()["page_order"] == [second, third]

    # Positions stay contiguous after a delete, so inserts land where expected
    new = client.post(url, json={"position": 1}).json()["id"]
    assert client.get(f"/notebooks/{notebook['id']}").json()["page_order"] == [second, new, third]
