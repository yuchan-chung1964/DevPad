# Changelog

Most recent first. Commit ids are from the shared repo `yuchan-chung1964/DevPad`.

## 2026-11-13: documentation
- Added `ROADMAP.md` and this file; updated `backend/README.md` (Render steps, known limitations) and `demo/README.md`
  (integration status).

## `tables` branch (Felix): merged with `backend-api`, `9616f87`
- Merged `backend-api` into `tables`. Removed the superseded in-memory/raw-SQL `backend/store.py` and a committed `.pyc` file.
  History is preserved, nothing was force-pushed, and the tree now matches `backend-api`.

## `ios-integration`: `9842cd9` (pushed, no PR yet, never compiled)
- `demo/Networking/`: typed API client (bearer auth, 429 retry, error mapping), wire models, PencilKit-stroke conversion,
  and `LibraryStore` (on-demand loading, debounced autosave).
- `demo/Auth/`: Supabase email sign-in.
- `NotesApp`, `FolderView`, `EditorView`, `NewNotebookSheet`, `Models` now use the store instead of sample data; pages can be titled.

## `backend-api`: Dockerfile and deployment notes, `1df3493`
- `backend/Dockerfile` and `.dockerignore` (single worker, non-root, docs off by default, config from environment variables).
- README "Deploying" section. The image has not been built or run.

## `backend-api`: page titles, cell kinds, live smoke test, `e730464`
- Pages have an optional `title` (up to 200 characters, trimmed).
- Cells have a fixed `kind`: `code` (default), `text` (content in `code`), or `ink`.
- `backend/scripts/smoke_test.py`: live HTTP check that works with HS256, ES256 via JWKS, or real tokens (e.g. Supabase).
- `backend/scripts/dev_jwks.py`: local fake of Supabase's signing-key endpoint.
- `backend/pytest.ini` limits collection to `tests/`; `.gitignore` excludes `*.pem` and `.env*`.
- README documents the Supabase JWT settings.
- Existing local databases must be deleted once (new columns, no migrations).

## Earlier, already on `backend-api` before this changelog
- `31e6265`: JWT auth, per-user ownership, rate limiting, input limits.
- `54afb93`: database persistence (SQLAlchemy), cells, tests.
