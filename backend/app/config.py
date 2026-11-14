import os

# SQLite file by default; set e.g. postgresql+psycopg://user:pass@host/devpad in production.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./devpad.db")

# Comma-separated list of allowed origins, or "*" for any.
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]

# ---------- Authentication ----------
# Requests carry `Authorization: Bearer <JWT>` issued by an external identity provider (Supabase, Auth0, Clerk, Firebase...).
# Set JWT_JWKS_URL for providers that sign with RS256/ES256 (recommended), or JWT_SECRET for HS256 (e.g. Supabase's
# legacy shared secret). With neither set, every authenticated route answers 503 rather than running open.
JWT_JWKS_URL = os.environ.get("JWT_JWKS_URL")
JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE")  # checked when set
JWT_ISSUER = os.environ.get("JWT_ISSUER")      # checked when set

# ---------- Rate limiting (requests per minute, per user; per client IP for unauthenticated requests) ----------
RATE_LIMIT_READ = int(os.environ.get("RATE_LIMIT_READ", "240"))
RATE_LIMIT_WRITE = int(os.environ.get("RATE_LIMIT_WRITE", "120"))
RATE_LIMIT_ANON = int(os.environ.get("RATE_LIMIT_ANON", "20"))
RATE_LIMIT_WINDOW_SECONDS = 60

# ---------- Size limits ----------
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", str(5 * 1024 * 1024)))
MAX_CODE_CHARS = 100_000
MAX_POINTS_PER_STROKE = 10_000
MAX_STROKES_PER_CELL = 5_000

# Per-user quotas.
MAX_FOLDERS = 1_000
MAX_NOTEBOOKS = 500
MAX_PAGES_PER_NOTEBOOK = 1_000
MAX_CELLS_PER_PAGE = 500

# Interactive docs (/docs, /redoc, /openapi.json). Turn off in production.
ENABLE_DOCS = os.environ.get("ENABLE_DOCS", "1") == "1"
