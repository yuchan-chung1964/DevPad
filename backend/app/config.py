import os

# SQLite file by default; set e.g. postgresql+psycopg://user:pass@host/devpad in production.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./devpad.db")

# Comma-separated list of allowed origins, or "*" for any.
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]
