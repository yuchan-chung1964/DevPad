# DevPad roadmap

Last updated 2026-11-13. Current goal: a **team demo / class project** (works for a handful of people; speed over scale).

## Where things stand
- **Backend** (`backend-api`): FastAPI + SQLAlchemy, Supabase JWT sign-in, per-user data, rate and size limits, page titles,
  cell kinds (`code` / `text` / `ink`). 46 unit tests pass, and a live smoke test passes against localhost, including with a
  real Supabase token. See `backend/README.md`.
- **iOS integration** (`ios-integration`): API client, Supabase sign-in and wired-up views. **Never compiled** (written on a PC
  without Swift), so expect compile errors on the first Xcode build. See `demo/README.md`.
- **Not done yet:** Postgres has never been run with this code, nothing is deployed, and the PR into `main` hasn't been merged.

## Decisions made
| Topic | Decision |
|---|---|
| First milestone | Team demo / class project |
| Hosting | Render (container from `backend/Dockerfile`) |
| Before deploying | Test on Postgres first (Supabase database) |
| Feature order | Typed-note editing, then free placement, then images/attachments, then search and offline sync |
| `ios-integration` | Draft PR for the frontend developer; merge only after a successful Xcode build |
| Xcode builds | The frontend developer builds and fixes the Swift |

## Next steps, in order
1. **Merge the backend.** Open the PR `backend-api` into `main`
   (<https://github.com/yuchan-chung1964/DevPad/compare/main...backend-api?expand=1>), get a teammate to review it, and merge.
   Tell Felix that his `tables` branch was merged with `backend-api` (his `store.py` sketch is superseded by
   `backend/app/models.py`; it is still in history at commit `1586296`).
2. **Test on Postgres.** Point `DATABASE_URL` at the Supabase database and run `backend/scripts/smoke_test.py`.
   Enter the database password in your own shell or the host's settings, never in chat or in git.
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
- Postgres, the Docker image, and the cross-user check with real tokens are untested.

## Ideas, not scheduled
Sign in with Apple, sharing and collaboration, trash and restore, tags, page templates beyond blank/lined/grid/dotted,
export to PDF.
