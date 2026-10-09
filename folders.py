from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas import Folder, FolderCreate, FolderUpdate, now
from app.store import FOLDERS, NOTEBOOKS

router = APIRouter(prefix="/folders", tags=["folders"])


def get_folder(folder_id: UUID) -> Folder:
    folder = FOLDERS.get(folder_id)
    if folder is None:
        raise HTTPException(404, "Folder not found")
    return folder


@router.post("", response_model=Folder, status_code=201)
def create_folder(body: FolderCreate):
    if body.parent_id is not None:
        get_folder(body.parent_id)
    folder = Folder(**body.model_dump())
    FOLDERS[folder.id] = folder
    return folder


@router.get("", response_model=list[Folder])
def list_folders(parent_id: Optional[UUID] = None):
    """Folders directly inside `parent_id` (omit for the library root)."""
    return [f for f in FOLDERS.values() if f.parent_id == parent_id]


@router.get("/{folder_id}", response_model=Folder)
def read_folder(folder_id: UUID):
    return get_folder(folder_id)


@router.patch("/{folder_id}", response_model=Folder)
def update_folder(folder_id: UUID, body: FolderUpdate):
    folder = get_folder(folder_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("parent_id") is not None:
        if data["parent_id"] == folder_id:
            raise HTTPException(400, "A folder can't be its own parent")
        get_folder(data["parent_id"])
    for field, value in data.items():
        setattr(folder, field, value)
    folder.updated_at = now()
    return folder


@router.delete("/{folder_id}", status_code=204)
def delete_folder(folder_id: UUID):
    get_folder(folder_id)
    has_subfolders = any(f.parent_id == folder_id for f in FOLDERS.values())
    has_notebooks = any(n.folder_id == folder_id for n in NOTEBOOKS.values())
    if has_subfolders or has_notebooks:
        raise HTTPException(409, "Folder is not empty")
    del FOLDERS[folder_id]
