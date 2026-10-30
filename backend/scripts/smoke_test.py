"""End-to-end check of a running DevPad API, sending the same requests demo/Networking/APIClient.swift sends.

    JWT_SECRET=... uvicorn app.main:app          # in one terminal
    JWT_SECRET=... python scripts/smoke_test.py  # in another (same secret)

Env: API_URL (default http://localhost:8000), JWT_SECRET (required; HS256), JWT_AUDIENCE / JWT_ISSUER if the server sets them.
"""
import os
import re
import sys
import time
import uuid

import httpx
import jwt

BASE = os.environ.get("API_URL", "http://localhost:8000")
SECRET = os.environ.get("JWT_SECRET")
PRIVATE_KEY_FILE = os.environ.get("SMOKE_PRIVATE_KEY")  # ES256 key from scripts/dev_jwks.py; mimics Supabase's signing keys
# Real tokens (e.g. from Supabase sign-in) for two different users; with these, no signing key is needed.
REAL_TOKEN = os.environ.get("SMOKE_TOKEN")
REAL_TOKEN_OTHER = os.environ.get("SMOKE_TOKEN_OTHER")
CAN_SIGN = bool(SECRET or PRIVATE_KEY_FILE)
if not (CAN_SIGN or REAL_TOKEN):
    sys.exit("Set JWT_SECRET (HS256), SMOKE_PRIVATE_KEY (ES256), or SMOKE_TOKEN (a real token; add SMOKE_TOKEN_OTHER for the cross-user checks)")


def sign(claims: dict) -> str:
    if PRIVATE_KEY_FILE:
        with open(PRIVATE_KEY_FILE) as fh:
            return jwt.encode(claims, fh.read(), algorithm="ES256", headers={"kid": "dev-key"})
    return jwt.encode(claims, SECRET, algorithm="HS256")


def token(sub: str, ttl: int = 3600) -> str:
    claims = {"sub": sub, "exp": int(time.time()) + ttl}
    if os.environ.get("JWT_AUDIENCE"):
        claims["aud"] = os.environ["JWT_AUDIENCE"]
    if os.environ.get("JWT_ISSUER"):
        claims["iss"] = os.environ["JWT_ISSUER"]
    return sign(claims)


def client(sub: str, real_token: str | None = None) -> httpx.Client:
    bearer = real_token or token(sub)
    return httpx.Client(base_url=BASE, headers={"Authorization": f"Bearer {bearer}", "Accept": "application/json"})


passed = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else '  -> ' + detail}")


def expect(name: str, r: httpx.Response, status: int):
    check(name, r.status_code == status, f"got {r.status_code}: {r.text[:200]}")
    return r.json() if r.content else None


# Swift's UUID().uuidString is uppercase in bodies; the client lowercases ids in paths.
def swift_uuid() -> str:
    return str(uuid.uuid4()).upper()


# What APIClient.decodeDate must handle: ISO 8601, microseconds, timezone optional.
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$")

print(f"Smoke test against {BASE}")
user = f"smoke-{uuid.uuid4()}"
def other_cannot_see(name: str, path: str) -> None:
    """A second user must get 404 for the first user's data. Skipped (and said so) without a second identity."""
    if other is None:
        print(f"  skip {name} (no second user)")
    else:
        check(name, other.get(path).status_code == 404)


has_other = CAN_SIGN or bool(REAL_TOKEN_OTHER)
other = client(f"other-{uuid.uuid4()}", REAL_TOKEN_OTHER) if has_other else None
with client(user, REAL_TOKEN) as c:
    print("health / auth")
    expect("GET /health (no token)", httpx.get(f"{BASE}/health"), 200)
    check("no token -> 401", httpx.get(f"{BASE}/folders").status_code == 401)
    check("garbage token -> 401", httpx.get(f"{BASE}/folders", headers={"Authorization": "Bearer nope"}).status_code == 401)
    if CAN_SIGN:  # forging tokens needs our own signing key
        expired = sign({"sub": "x", "exp": int(time.time()) - 60, **{k: v for k, v in (("aud", os.environ.get("JWT_AUDIENCE")), ("iss", os.environ.get("JWT_ISSUER"))) if v}})
        wrong_aud = sign({"sub": "x", "exp": int(time.time()) + 600, "aud": "somebody-else"}) if os.environ.get("JWT_AUDIENCE") else None
        if wrong_aud:
            check("wrong audience -> 401", httpx.get(f"{BASE}/folders", headers={"Authorization": f"Bearer {wrong_aud}"}).status_code == 401)
        check("expired token -> 401", httpx.get(f"{BASE}/folders", headers={"Authorization": f"Bearer {expired}"}).status_code == 401)

    print("folders")
    f = expect("POST /folders", c.post("/folders", json={"name": "School", "parent_id": None}), 201)
    sub = expect("POST /folders (nested)", c.post("/folders", json={"name": "CS", "parent_id": f["id"]}), 201)
    check("folder dates parse", all(DATE_RE.match(f[k]) for k in ("created_at", "updated_at")), str(f))
    root = expect("GET /folders", c.get("/folders", params={"limit": 100, "offset": 0}), 200)
    check("root list holds only the root folder", [x["id"] for x in root] == [f["id"]])
    children = c.get("/folders", params={"parent_id": f["id"].upper().lower(), "limit": 100, "offset": 0}).json()
    check("child list by parent_id", [x["id"] for x in children] == [sub["id"]])
    expect("PATCH rename (parent_id omitted)", c.patch(f"/folders/{sub['id']}", json={"name": "CS 61A"}), 200)
    check("rename left parent alone", c.get(f"/folders/{sub['id']}").json()["parent_id"] == f["id"])
    moved = expect("PATCH parent_id: null moves to root", c.patch(f"/folders/{sub['id']}", json={"parent_id": None}), 200)
    check("moved folder is at root", moved["parent_id"] is None)
    other_cannot_see("other user can't see folder (404)", f"/folders/{f['id']}")
    check("blank name -> 422", c.post("/folders", json={"name": "  "}).status_code == 422)

    print("notebooks / pages")
    nb = expect("POST /notebooks", c.post("/notebooks", json={
        "title": "Algorithms", "folder_id": f["id"], "cover_color": "#4A6FA5", "template": "lined"}), 201)
    check("starter page exists", len(nb["page_order"]) == 1)
    check("folder with notebook can't be deleted (409)", c.delete(f"/folders/{f['id']}").status_code == 409)
    check("bad color -> 422", c.post("/notebooks", json={"title": "x", "cover_color": "blue"}).status_code == 422)
    nbid = nb["id"]
    pg2 = expect("POST page at position 0", c.post(f"/notebooks/{nbid}/pages", json={"template": "grid", "position": 0}), 201)
    summaries = expect("GET pages (summaries)", c.get(f"/notebooks/{nbid}/pages"), 200)
    check("summaries have cell_count", all("cell_count" in s for s in summaries))
    order = [pg2["id"], nb["page_order"][0]]
    expect("PATCH page_order (uppercase ids)", c.patch(f"/notebooks/{nbid}", json={"page_order": [i.upper() for i in reversed(order)]}), 200)
    check("page_order unknown id -> 400", c.patch(f"/notebooks/{nbid}", json={"page_order": [swift_uuid()]}).status_code == 400)
    expect("PATCH move notebook to root (folder_id null)", c.patch(f"/notebooks/{nbid}", json={"folder_id": None}), 200)
    check("list root notebooks", nbid in [n["id"] for n in c.get("/notebooks", params={"limit": 100, "offset": 0}).json()])
    other_cannot_see("other user can't open notebook (404)", f"/notebooks/{nbid}")

    print("page titles")
    pid = nb["page_order"][0]
    titled = expect("PATCH page title", c.patch(f"/notebooks/{nbid}/pages/{pid}", json={"title": "Week 1"}), 200)
    check("title saved", titled["title"] == "Week 1")
    check("title in page summaries", "Week 1" in [p["title"] for p in c.get(f"/notebooks/{nbid}/pages").json()])
    check("title: null -> 422", c.patch(f"/notebooks/{nbid}/pages/{pid}", json={"title": None}).status_code == 422)

    print("cells / strokes")
    cp = f"/notebooks/{nbid}/pages/{pid}/cells"
    ink_cell = expect("POST ink cell (kind)", c.post(cp, json={"kind": "ink", "language": "text", "code": "", "strokes": []}), 201)
    note = expect("POST text cell (kind)", c.post(cp, json={"kind": "text", "language": "markdown", "code": "hello"}), 201)
    check("kinds returned", (ink_cell["kind"], note["kind"]) == ("ink", "text"))
    check("unknown kind -> 422", c.post(cp, json={"kind": "image"}).status_code == 422)
    expect("DELETE ink cell", c.delete(f"{cp}/{ink_cell['id']}"), 204)
    expect("DELETE text cell", c.delete(f"{cp}/{note['id']}"), 204)
    cell = expect("POST cell", c.post(cp, json={"language": "swift", "code": "print(1)", "strokes": [], "position": None}), 201)
    cid = cell["id"]
    stroke = {
        "id": swift_uuid(),
        "points": [{"x": 10.5, "y": 20.25, "t": 0.0, "pressure": 0.4}, {"x": 11, "y": 21, "t": 0.016, "pressure": 1.0}],
        "tool": "pen", "color": "#1A2B3C", "width": 2.5,
    }
    expect("POST strokes (append)", c.post(f"{cp}/{cid}/strokes", json=[stroke]), 201)
    marker = {**stroke, "id": swift_uuid(), "tool": "highlighter", "color": "#FFEB3B80"}
    replaced = expect("PUT strokes (replace, #RRGGBBAA)", c.put(f"{cp}/{cid}/strokes", json=[stroke, marker]), 200)
    check("strokes round-trip", [s["id"] for s in replaced["strokes"]] == [stroke["id"].lower(), marker["id"].lower()], str(replaced["strokes"])[:200])
    check("point data preserved", replaced["strokes"][0]["points"][0] == stroke["points"][0])
    bad = {**stroke, "points": [{"x": 0, "y": 0, "t": 0, "pressure": 1.5}]}
    check("pressure > 1 -> 422", c.put(f"{cp}/{cid}/strokes", json=[bad]).status_code == 422)
    expect("DELETE one stroke (lowercase id in path)", c.delete(f"{cp}/{cid}/strokes/{stroke['id'].lower()}"), 204)
    check("deleting it again -> 404", c.delete(f"{cp}/{cid}/strokes/{stroke['id'].lower()}").status_code == 404)
    expect("PATCH cell code", c.patch(f"{cp}/{cid}", json={"code": "print(2)"}), 200)
    check("PATCH code: null -> 422", c.patch(f"{cp}/{cid}", json={"code": None}).status_code == 422)
    full = expect("GET full page", c.get(f"/notebooks/{nbid}/pages/{pid}"), 200)
    check("page embeds the cell with its stroke", len(full["cells"]) == 1 and len(full["cells"][0]["strokes"]) == 1)
    check("cell dates parse", all(DATE_RE.match(full["cells"][0][k]) for k in ("created_at", "updated_at")), str(full["cells"][0]))
    other_cannot_see("other user can't read cell (404)", f"{cp}/{cid}")
    big = [{**stroke, "id": swift_uuid()}] * 5001
    check("5001 strokes -> 4xx", 400 <= c.put(f"{cp}/{cid}/strokes", json=big).status_code < 500)

    print("cleanup")
    expect("DELETE cell", c.delete(f"{cp}/{cid}"), 204)
    expect("DELETE notebook", c.delete(f"/notebooks/{nbid}"), 204)
    expect("DELETE subfolder", c.delete(f"/folders/{sub['id']}"), 204)
    expect("DELETE parent folder", c.delete(f"/folders/{f['id']}"), 204)

if other is not None:
    other.close()
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
