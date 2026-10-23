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
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins |

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
| `app/config.py` | Settings from environment variables |
| `app/db.py` | Engine, session, `DB` dependency |
| `app/models.py` | SQLAlchemy tables |
| `app/schemas.py` | Pydantic request/response models |
| `app/routes/` | One router per resource |
| `tests/` | pytest suite |
