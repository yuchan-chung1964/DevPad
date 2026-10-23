from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app import models
from app.db import DB
from app.schemas import Folder, FolderCreate, FolderUpdate

router = APIRouter(prefix="/folders", tags=["folders"])


def get_folder(db: Session, folder_id: UUID) -> models.Folder:
    folder = db.get(models.Folder, folder_id)
    if folder is None:
        raise HTTPException(404, "Folder not found")
    return folder


def _is_descendant(db: Session, folder_id: UUID, ancestor_id: UUID) -> bool:
    """True if `folder_id` is `ancestor_id` or sits anywhere below it."""
    current: Optional[UUID] = folder_id
    while current is not None:
        if current == ancestor_id:
            return True
        current = db.get(models.Folder, current).parent_id
    return False


@router.post("", response_model=Folder, status_code=201)
def create_folder(body: FolderCreate, db: DB):
    if body.parent_id is not None:
        get_folder(db, body.parent_id)
    folder = models.Folder(**body.model_dump())
    db.add(folder)
    db.flush()
    return folder


@router.get("", response_model=list[Folder])
def list_folders(db: DB, parent_id: Optional[UUID] = None):
    """Folders directly inside `parent_id` (omit for the library root)."""
    return db.scalars(
        select(models.Folder).where(models.Folder.parent_id == parent_id).order_by(models.Folder.created_at)
    ).all()


@router.get("/{folder_id}", response_model=Folder)
def read_folder(folder_id: UUID, db: DB):
    return get_folder(db, folder_id)


@router.patch("/{folder_id}", response_model=Folder)
def update_folder(folder_id: UUID, body: FolderUpdate, db: DB):
    """Rename, or move into another folder (`parent_id`, null for the library root)."""
    folder = get_folder(db, folder_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("parent_id") is not None:
        get_folder(db, data["parent_id"])
        if _is_descendant(db, data["parent_id"], folder_id):
            raise HTTPException(400, "A folder can't be moved into itself or one of its subfolders")
    for field, value in data.items():
        setattr(folder, field, value)
    folder.updated_at = models.now()
    return folder


@router.delete("/{folder_id}", status_code=204)
def delete_folder(folder_id: UUID, db: DB):
    """Only empty folders can be deleted."""
    folder = get_folder(db, folder_id)
    has_subfolders = db.scalar(select(exists().where(models.Folder.parent_id == folder_id)))
    has_notebooks = db.scalar(select(exists().where(models.Notebook.folder_id == folder_id)))
    if has_subfolders or has_notebooks:
        raise HTTPException(409, "Folder is not empty")
    db.delete(folder)
