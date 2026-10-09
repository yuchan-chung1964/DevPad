from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.routes.folders import get_folder
from app.schemas import Notebook, NotebookCreate, NotebookUpdate, Page, now
from app.store import NOTEBOOKS, PAGES

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


def get_notebook(notebook_id: UUID) -> Notebook:
    nb = NOTEBOOKS.get(notebook_id)
    if nb is None:
        raise HTTPException(404, "Notebook not found")
    return nb


@router.post("", response_model=Notebook, status_code=201)
def create_notebook(body: NotebookCreate):
    """Creates a notebook with one starter page."""
    if body.folder_id is not None:
        get_folder(body.folder_id)
    nb = Notebook(title=body.title, folder_id=body.folder_id, cover_color=body.cover_color)
    page = Page(notebook_id=nb.id, template=body.template)
    PAGES[page.id] = page
    nb.page_order = [page.id]
    NOTEBOOKS[nb.id] = nb
    return nb


@router.get("", response_model=list[Notebook])
def list_notebooks(folder_id: Optional[UUID] = None):
    """Notebooks directly inside `folder_id` (omit for the library root)."""
    return [n for n in NOTEBOOKS.values() if n.folder_id == folder_id]


@router.get("/{notebook_id}", response_model=Notebook)
def read_notebook(notebook_id: UUID):
    return get_notebook(notebook_id)


@router.patch("/{notebook_id}", response_model=Notebook)
def update_notebook(notebook_id: UUID, body: NotebookUpdate):
    """Rename, recolor, move to another folder, or reorder pages."""
    nb = get_notebook(notebook_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("folder_id") is not None:
        get_folder(data["folder_id"])
    if "page_order" in data and set(data["page_order"]) != set(nb.page_order):
        raise HTTPException(400, "page_order must contain exactly the notebook's existing pages")
    for field, value in data.items():
        setattr(nb, field, value)
    nb.updated_at = now()
    return nb


@router.delete("/{notebook_id}", status_code=204)
def delete_notebook(notebook_id: UUID):
    nb = get_notebook(notebook_id)
    for pid in nb.page_order:
        PAGES.pop(pid, None)
    del NOTEBOOKS[notebook_id]
