# Backend

FastAPI + SQLAlchemy API for DevPad.

```
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API docs: http://localhost:8000/docs

Run the tests with `pytest` (from `backend/`). They use a throwaway in-memory database.

## Configuration

| Env var | Default | |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./devpad.db` | For Postgres: `pip install "psycopg[binary]"` and use `postgresql+psycopg://user:pass@host/devpad` |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins (set explicitly in production) |
| `JWT_JWKS_URL` | - | Identity provider's JWKS endpoint (RS256/ES256 tokens). Preferred. |
| `JWT_SECRET` | - | Shared secret for HS256 tokens. Used only if `JWT_JWKS_URL` is unset. |
| `JWT_AUDIENCE` / `JWT_ISSUER` | - | Checked when set. Set both in production. |
| `RATE_LIMIT_READ` / `RATE_LIMIT_WRITE` / `RATE_LIMIT_ANON` | `240` / `120` / `20` | Requests per minute |
| `MAX_BODY_BYTES` | `5242880` | Larger request bodies get 413 |
| `ENABLE_DOCS` | `1` | Set to `0` to hide `/docs`, `/redoc`, `/openapi.json` |

If neither `JWT_JWKS_URL` nor `JWT_SECRET` is set, every data route answers 503 (it never runs open).

## Authentication, ownership, limits

- Every route except `/health` needs `Authorization: Bearer <JWT>` from your identity provider
  (Supabase, Auth0, Clerk, Firebase...). The token must be signed, unexpired, and carry `sub`; `sub` is the user id.
  Users are created on first request. In `/docs`, use **Authorize** to paste a token.
- Folders and notebooks belong to the user that created them (pages and cells through their notebook). Other
  people's resources return **404**, never 403, so ids can't be probed.
- Rate limits are per user (reads and writes counted separately) and per client IP for requests without a valid
  token. Over the limit: **429** with `Retry-After`. The counters are in memory, so with several workers
  use a shared store (Redis) instead.
- Limits: 100k chars of code per cell, 10k points per stroke, 5k strokes per cell, and per-user quotas (see
  `app/config.py`). `GET /folders` and `GET /notebooks` take `limit` (max 500) and `offset`.
- `owner_id` was added to folders and notebooks, so delete an existing `devpad.db` once.

Tables are created on startup if they don't exist. There are no migrations yet, so after changing
`app/models.py`, delete `devpad.db` (or add Alembic once the schema settles).

## Structure

Folder -> Notebook -> Page -> Cell -> Stroke

- A **cell** is a block on a page: the code it represents (`code`, `language`) plus its handwritten strokes.
  The API stores code; it doesn't run it.
- Notebooks keep their pages in order (`page_order`); pages keep their cells in order (`cells`).
- A notebook is created with one blank page and must always keep at least one. A page can have no cells.
- Folders can only be deleted when empty.

| Resource | Endpoints |
|---|---|
| Folders | `POST/GET /folders`, `GET/PATCH/DELETE /folders/{id}` |
| Notebooks | `POST/GET /notebooks`, `GET/PATCH/DELETE /notebooks/{id}` |
| Pages | `GET/POST /notebooks/{id}/pages`, `GET/PATCH/DELETE /notebooks/{id}/pages/{page_id}` |
| Cells | `GET/POST .../pages/{page_id}/cells`, `GET/PATCH/DELETE .../cells/{cell_id}` |
| Strokes | `POST/PUT .../cells/{cell_id}/strokes`, `DELETE .../strokes/{stroke_id}` |

- Reorder pages: `PATCH /notebooks/{id}` with the full new `page_order`.
- Reorder cells: `PATCH .../pages/{page_id}` with the full new `cell_order`.
- Move to the library root: `PATCH` with `"folder_id": null` (notebooks) or `"parent_id": null` (folders).
- Insert at an index: `POST` a page or cell with `"position": n` (defaults to the end).

## Layout

| Path | |
|---|---|
| `app/main.py` | App, CORS, router registration |
| `app/config.py` | Settings from environment variables, size limits and quotas |
| `app/auth.py` | JWT validation, current user, rate-limit hook |
| `app/ratelimit.py` | Sliding-window limiter and quota check |
| `app/db.py` | Engine, session, `DB` dependency |
| `app/models.py` | SQLAlchemy tables |
| `app/schemas.py` | Pydantic request/response models |
| `app/routes/` | One router per resource |
| `tests/` | pytest suite |
