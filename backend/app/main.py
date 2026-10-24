from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS, ENABLE_DOCS, MAX_BODY_BYTES
from app.db import engine
from app.models import Base
from app.routes import cells, folders, notebooks, pages


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # TODO: switch to Alembic migrations once the schema settles
    yield


app = FastAPI(
    title="DevPad API",
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)


@app.middleware("http")
async def limit_body_and_add_headers(request: Request, call_next):
    # Only checks the declared Content-Length; also cap request size at your reverse proxy.
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "Request body too large"}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


# Auth is a bearer token (not a cookie), so browsers never attach it on their own and credentials stay disabled.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(folders.router)
app.include_router(notebooks.router)
app.include_router(pages.router)
app.include_router(cells.router)


@app.get("/health")
def health():
    return {"status": "ok"}
