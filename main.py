from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import folders, notebooks, pages

app = FastAPI(title="Notes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten once client origins are known
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(folders.router)
app.include_router(notebooks.router)
app.include_router(pages.router)


@app.get("/health")
def health():
    return {"status": "ok"}
