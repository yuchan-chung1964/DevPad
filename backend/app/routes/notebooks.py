from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models
from app.db import DB
from app.routes.folders import get_folder
from app.schemas import Notebook, NotebookCreate, NotebookUpdate

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


def get_notebook(db: Session, notebook_id: UUID) -> models.Notebook:
    nb = db.get(models.Notebook, notebook_id)
    if nb is None:
        raise HTTPException(404, "Notebook not found")
    return nb


def check_order(new_order: list[UUID], current: list[UUID], what: str) -> None:
    """A reorder must list every existing item exactly once."""
    if len(new_order) != len(current) or set(new_order) != set(current):
        raise HTTPException(400, f"{what} must contain each existing item exactly once")


@router.post("", response_model=Notebook, status_code=201)
def create_notebook(body: NotebookCreate, db: DB):
    """Creates a notebook with one starter page."""
    if body.folder_id is not None:
        get_folder(db, body.folder_id)
    nb = models.Notebook(title=body.title, folder_id=body.folder_id, cover_color=body.cover_color)
    nb.pages.append(models.Page(template=body.template))
    db.add(nb)
    db.flush()
    return nb


@router.get("", response_model=list[Notebook])
def list_notebooks(db: DB, folder_id: Optional[UUID] = None):
    """Notebooks directly inside `folder_id` (omit for the library root)."""
    return db.scalars(
        select(models.Notebook)
        .where(models.Notebook.folder_id == folder_id)
        .order_by(models.Notebook.created_at)
        .options(selectinload(models.Notebook.pages))  # for page_order, in one extra query
    ).all()


@router.get("/{notebook_id}", response_model=Notebook)
def read_notebook(notebook_id: UUID, db: DB):
    return get_notebook(db, notebook_id)


@router.patch("/{notebook_id}", response_model=Notebook)
def update_notebook(notebook_id: UUID, body: NotebookUpdate, db: DB):
    """Rename, recolor, move to another folder (null for the library root), or reorder pages."""
    nb = get_notebook(db, notebook_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("folder_id") is not None:
        get_folder(db, data["folder_id"])
    if "page_order" in data:
        new_order = data.pop("page_order")
        check_order(new_order, nb.page_order, "page_order")
        by_id = {p.id: p for p in nb.pages}
        nb.pages = [by_id[pid] for pid in new_order]
        nb.pages.reorder()
    for field, value in data.items():
        setattr(nb, field, value)
    nb.updated_at = models.now()
    return nb


@router.delete("/{notebook_id}", status_code=204)
def delete_notebook(notebook_id: UUID, db: DB):
    """Deletes the notebook with all its pages and cells."""
    db.delete(get_notebook(db, notebook_id))
