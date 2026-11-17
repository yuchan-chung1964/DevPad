# DevPad: roadmap, changelog and architecture

Last updated 2026-11-16. One document with three sections:

1. [Roadmap](#1-roadmap): where the project stands and what to do next
2. [Changelog](#2-changelog): what has changed so far
3. [Architecture](#3-architecture): how the backend API works, file by file

Current goal: a **team demo / class project** (works for a handful of people; speed over scale).

---

# 1. Roadmap

## Where things stand
- **Backend** (in `main`, whole `backend/` folder, PRs #1 and #2): FastAPI + SQLAlchemy, Supabase JWT sign-in, per-user data,
  rate and size limits, page titles, cell kinds (`code` / `text` / `ink`). 46 unit tests pass. See [backend/README.md](backend/README.md).
- **Postgres:** the smoke test passed (53 of 53) against the Supabase Postgres database with a real Supabase sign-in
  (2026-11-13). Row-level security was enabled on the five tables.
- **iOS integration** (`ios-integration` branch): API client, Supabase sign-in and wired-up views. **Never compiled** (written on
  a PC without Swift), so expect compile errors on the first Xcode build. See [demo/README.md](demo/README.md).
- **Not done yet:** nothing is deployed, the iOS code has never been built, and the RLS read-back check (create a record, read
  it with the publishable key, expect nothing) hasn't been run.

## Decisions made
| Topic | Decision |
|---|---|
| First milestone | Team demo / class project |
| Hosting | Render (container from `backend/Dockerfile`) |
| Before deploying | Test on Postgres first (Supabase database): done |
| Feature order | Typed-note editing, then free placement, then images/attachments, then search and offline sync |
| `ios-integration` | Draft PR for the frontend developer; merge only after a successful Xcode build |
| Xcode builds | The frontend developer builds and fixes the Swift |

## Next steps, in order
1. **Merge the backend.** Done (PRs #1 and #2). Still to do: tell Felix that his `tables` branch was merged with `backend-api`
   (his `store.py` sketch is superseded by `backend/app/models.py`; it is still in history at commit `1586296`).
2. **Test on Postgres. Done 2026-11-13** (53 of 53 passed). Point `DATABASE_URL` at the Supabase database and run
   `backend/scripts/smoke_test.py`. Enter the database password in your own shell or the host's settings, never in chat or in git.
   Use the **session pooler** connection string (port 5432). After the server first creates the tables, **enable row-level
   security on all five** (`users`, `folders`, `notebooks`, `pages`, `cells`; SQL in `backend/README.md`). Supabase exposes
   the `public` schema through its own REST API, so tables without RLS could be read with the publishable key. The backend
   connects as the `postgres` role, which bypasses RLS, so it keeps working.
3. **Deploy on Render.** See "Deploying on Render" in `backend/README.md`. Then run the smoke test against the live URL with a
   real token.
4. **iOS review.** Open `ios-integration` as a **draft** PR. The frontend developer builds it in Xcode, fixes compile errors,
   and tries sign-in, creating a notebook, drawing and relaunching.
5. **Typed-note editing.** Text boxes in the iPad editor. The API already supports it (`kind: "text"`, content in `code`).
   Keep ink in its own `ink` cell so text and drawing don't overwrite each other.
6. **Migrations, then free placement.** Free placement adds position and size to cells (x, y, width, height), which changes
   the schema. Add Alembic migrations first so that change doesn't erase data.
7. **Later:** images and attachments (Supabase Storage), search across notebooks, offline editing and sync.

## Known risks and gaps
- Server accepts missing issuer/audience settings: if `JWT_ISSUER` / `JWT_AUDIENCE` are unset, those checks are skipped.
  Set both in production. Planned fix: refuse to start when `JWT_JWKS_URL` is set without them.
- No database migrations yet. Schema changes mean recreating tables.
- The request-size limit only checks the declared `Content-Length`. Also cap request size at the host.
- The rate limiter keeps counters in memory, so run a single instance until it moves to Redis.
- Quota checks can be raced slightly (count, then insert).
- The Swift code is uncompiled. Known limits once it builds: notebook covers show blank paper until opened, pencil tilt isn't
  saved, and a page over 5,000 strokes fails to save.
- The Docker image, the cross-user check with real tokens, and the RLS read-back check are untested.

## Ideas, not scheduled
Sign in with Apple, sharing and collaboration, trash and restore, tags, page templates beyond blank/lined/grid/dotted,
export to PDF.

---

# 2. Changelog

Most recent first. Commit ids are from the shared repo `yuchan-chung1964/DevPad`.

## 2026-11-16: documentation merged into one file
- `ROADMAP.md` and `CHANGELOG.md` were combined with a new architecture write-up into this file, `PROJECT.md`.
  The READMEs now link here.

## 2026-11-13: Postgres verified
- Ran `backend/scripts/smoke_test.py` against the Supabase Postgres database (session pooler) with a real Supabase token:
  53 passed, 0 failed (three cross-user checks skipped: only one user). The five tables were created by the app on first
  start, and row-level security was then enabled on them.
- Backend `main` now includes PR #1 (merge `556308a`) and PR #2 (merge `049441a`).

## 2026-11-13: documentation
- Added a roadmap and changelog; updated `backend/README.md` (Render steps, known limitations) and `demo/README.md`
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

---

# 3. Architecture

The whole `backend/` folder is in `main`. The API looks complex because each request passes through several layers, and each
layer does one job:

```
request -> main.py (size limit, CORS, headers)
        -> a router in routes/ (matches the URL)
        -> auth.py (check token, rate limit, find the user)
        -> db.py (open a database session)
        -> the route function (the actual work)
        -> schemas.py (validate input / shape output)
        -> models.py (the database tables)
```

Reading order for a newcomer: `main.py`, then `auth.py`, then any one route file. The route files all follow the same pattern.

## Settings and database

**[config.py](backend/app/config.py)** is the one place that reads settings from environment variables.
- `DATABASE_URL`: which database to use. It defaults to a local SQLite file.
- `CORS_ORIGINS`: which web origins may call the API, split on commas.
- `JWT_JWKS_URL`, `JWT_SECRET`, `JWT_AUDIENCE`, `JWT_ISSUER`: how tokens are checked.
- Rate limits: requests per minute: 240 reads, 120 writes, 20 for anonymous callers, over a 60-second window.
- Size limits: 5 MB request body, 100,000 characters of code per cell, 10,000 points per stroke, 5,000 strokes per cell.
- Per-user quotas: 1,000 folders, 500 notebooks, 1,000 pages per notebook, 500 cells per page.
- `ENABLE_DOCS`: turns the `/docs` page on or off.

**[db.py](backend/app/db.py)** connects to the database.
- SQLite special cases: `check_same_thread: False` lets web threads share a connection. An in-memory database (used by tests)
  gets one shared connection so it survives across sessions. `PRAGMA foreign_keys=ON` turns on foreign-key checks, which SQLite
  skips by default.
- `SessionLocal`: a factory for sessions.
- `get_db()`: gives each request one session. It commits if the route succeeds, rolls back if it errors, and always closes.
- `DB = Annotated[Session, Depends(get_db)]`: a shorthand, so routes write `db: DB`.

**[models.py](backend/app/models.py)** defines the five tables.
- `UTCDateTime`: makes sure dates always come back as UTC (SQLite drops time zones).
- `Timestamped`: adds `created_at` and `updated_at` to anything that includes it.
- `User`: `id` is the Supabase user id (the token's `sub` value), stored as text.
- `Folder`: an owner, a `parent_id` pointing at another folder (null means top level), and a name.
- `Notebook`: an owner, an optional folder, a title, a cover color, and its ordered `pages`. `ordering_list("position")` keeps
  each page's `position` number in sync. `page_order` returns the ids in order.
- `Page`: its notebook, `position`, `template`, `title`, and ordered `cells`.
- `Cell`: its page, `position`, `kind`, `language`, `code`, and `strokes` stored as JSON. Strokes must be reassigned, not edited
  in place, or SQLAlchemy won't notice the change.
- `cascade="all, delete-orphan"`: deleting a notebook deletes its pages and cells.

## Request and response shapes

**[schemas.py](backend/app/schemas.py)** uses Pydantic to check what clients send and to shape what we return.
- Reusable field types: `HexColor` (a `#RRGGBB` or `#RRGGBBAA` pattern), `Name` (trimmed, 1-200 characters), `Language`, and
  `Code` (length-limited).
- `NotNull`: for PATCH requests, a field may be left out but not set to `null`. A few fields skip it on purpose, because `null`
  means "move to the top level".
- `ORMModel`: lets responses be built straight from database objects.
- `Point`, `Stroke`: one stroke is an id, a list of points (x, y, time, pressure between 0 and 1), a tool, a color and a width.
- Cells, pages, notebooks, folders: each has a response model (what we return), a `...Create` model (what a POST accepts) and an
  `...Update` model (what a PATCH accepts). `PageSummary` is a lighter page without cells.
- `CellKind`: limited to `code`, `text` or `ink`.

## Security and limits

**[auth.py](backend/app/auth.py)** works out who is calling.
- `_jwks_client`: fetches your provider's public keys once and caches them.
- `_decode(token)`: if a JWKS URL is set, it verifies with the key matching the token (RS256 or ES256). Otherwise it uses the
  shared secret (HS256). With neither set it returns 503, so it never runs open. The accepted algorithms are a fixed list, so a
  token can't choose its own. It requires `exp` and `sub`, and checks audience and issuer only when those are configured.
- `current_user`:
  1. No token: it counts the attempt against a per-IP limit, then returns 401.
  2. Bad token: same throttling, then 401. If the key server is unreachable it returns 503.
  3. Valid token: it applies the per-user rate limit, with separate counters for reads (GET) and writes.
  4. It looks up the user row, or creates it on first sight. It handles two first requests racing each other.
- `CurrentUser`: a shorthand that routes use.

**[ratelimit.py](backend/app/ratelimit.py)**
- `RateLimiter.check(key, limit)`: keeps a list of recent request times per key. It drops entries older than the window. If the
  count has reached the limit it returns 429 with a `Retry-After` header. Otherwise it records the request.
- Housekeeping: every 1,000 calls it deletes idle keys. `reset()` is for tests.
- `enforce_quota`: returns 403 if a user is over a count limit, like 500 notebooks.

## The app entry point

**[main.py](backend/app/main.py)**
- `lifespan`: creates the tables on startup (no migrations yet).
- App setup: `/docs` can be switched off.
- Middleware: it rejects bodies whose declared size is over 5 MB (413). It adds `nosniff` and `no-store` headers to every response.
- CORS: credentials stay off, because tokens are sent in a header and not in cookies.
- Routers: it plugs in the four routers, and adds `/health`.

## The routes, one file per resource
Every route first confirms the item belongs to the caller. Another user's item gives 404 and not 403, so ids can't be probed.

**[routes/folders.py](backend/app/routes/folders.py)**
- `get_folder`: 404 if it's missing or yours isn't.
- `_is_descendant`: walks up the parent chain, so a folder can't be moved into itself or one of its own subfolders.
- Create: checks your quota and that the parent is yours.
- List: filters by `parent_id`, with `limit` and `offset`.
- PATCH: renames, or moves (using `exclude_unset`, so an explicit `null` moves it to the top level).
- Delete: returns 409 unless the folder is empty.

**[routes/notebooks.py](backend/app/routes/notebooks.py)**
- `get_notebook`: same ownership check.
- `check_order`: a reorder list must contain every existing id exactly once.
- Create: checks quota and folder, then adds a notebook with one starter page.
- List: one level at a time, loading pages in the same query.
- PATCH: rename, recolor, move, or reorder pages by rebuilding the list in the new order.
- Delete: removes the notebook and everything inside it.

**[routes/pages.py](backend/app/routes/pages.py)**
- `get_page`: checks the notebook is yours, then that the page belongs to it.
- `touch`: updates `updated_at` on the page and its notebook.
- `insert_at`: inserts at a position, and returns 400 if the position is out of range.
- List: returns summaries, with cell counts computed in the database so strokes aren't loaded.
- Create, read, PATCH: PATCH changes title and template, or reorders cells.
- Delete: returns 409 if it's the notebook's last page.

**[routes/cells.py](backend/app/routes/cells.py)**
- `get_cell`: checks ownership down the chain.
- Create: accepts `kind`, `language`, `code` and optional strokes and position.
- PATCH: changes language and code only. The kind is fixed.
- Delete: removes the cell and renumbers the rest.
- Strokes: POST adds, PUT replaces everything (used for autosave), and DELETE removes one by id. The 5,000-stroke cap is checked here.

## Supporting files
- [requirements.txt](backend/requirements.txt): the Python packages.
- [Dockerfile](backend/Dockerfile), [.dockerignore](backend/.dockerignore): build the container for hosting.
- [pytest.ini](backend/pytest.ini): limits `pytest` to `tests/`.
- [tests/conftest.py](backend/tests/conftest.py): sets a throwaway in-memory database and a test token secret before the app
  loads. It provides `make_token`. The `anon_client`, `client` (user-a), `other_client` (user-b), `notebook` and `page_url`
  fixtures give each test a clean database.
- `backend/tests/test_*.py`: one file per area, 46 tests in all.
- [scripts/smoke_test.py](backend/scripts/smoke_test.py): checks a running server over real HTTP.
  [scripts/dev_jwks.py](backend/scripts/dev_jwks.py): fakes the key server for local testing.
- [backend/README.md](backend/README.md): setup, settings, deployment and known limits.
