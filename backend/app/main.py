from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.db import engine
from app.models import Base
from app.routes import cells, folders, notebooks, pages


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # TODO: switch to Alembic migrations once the schema settles
    yield


app = FastAPI(title="DevPad API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(folders.router)
app.include_router(notebooks.router)
app.include_router(pages.router)
app.include_router(cells.router)


@app.get("/health")
def health():
    return {"status": "ok"}
