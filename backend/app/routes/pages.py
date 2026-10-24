from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config, models
from app.auth import CurrentUser
from app.db import DB
from app.ratelimit import enforce_quota
from app.routes.notebooks import check_order, get_notebook
from app.schemas import Page, PageCreate, PageSummary, PageUpdate

router = APIRouter(prefix="/notebooks/{notebook_id}/pages", tags=["pages"])


def get_page(db: Session, user: models.User, notebook_id: UUID, page_id: UUID) -> models.Page:
    get_notebook(db, user, notebook_id)  # 404 unless the notebook is the caller's
    page = db.get(models.Page, page_id)
    if page is None or page.notebook_id != notebook_id:
        raise HTTPException(404, "Page not found")
    return page


def touch(page: models.Page) -> None:
    """Bump updated_at on the page and its notebook."""
    page.updated_at = page.notebook.updated_at = models.now()


def insert_at(items: list, item, position: Optional[int]) -> None:
    """Insert into an ordered collection; `position` defaults to the end."""
    if position is None:
        items.append(item)
    elif position > len(items):
        raise HTTPException(400, f"position must be between 0 and {len(items)}")
    else:
        items.insert(position, item)


@router.get("", response_model=list[PageSummary])
def list_pages(notebook_id: UUID, db: DB, user: CurrentUser):
    """Pages in order, without cell data."""
    pages = get_notebook(db, user, notebook_id).pages
    # Count in SQL so we don't load every cell's strokes just to count them.
    counts = dict(db.execute(
        select(models.Cell.page_id, func.count())
        .where(models.Cell.page_id.in_([p.id for p in pages]))
        .group_by(models.Cell.page_id)
    ).all())
    return [
        PageSummary(
            id=p.id,
            notebook_id=p.notebook_id,
            template=p.template,
            cell_count=counts.get(p.id, 0),
            updated_at=p.updated_at,
        )
        for p in pages
    ]


@router.post("", response_model=Page, status_code=201)
def create_page(notebook_id: UUID, body: PageCreate, db: DB, user: CurrentUser):
    nb = get_notebook(db, user, notebook_id)
    enforce_quota(len(nb.pages), config.MAX_PAGES_PER_NOTEBOOK, "pages per notebook")
    page = models.Page(template=body.template)
    insert_at(nb.pages, page, body.position)
    nb.updated_at = models.now()
    db.flush()
    return page


@router.get("/{page_id}", response_model=Page)
def read_page(notebook_id: UUID, page_id: UUID, db: DB, user: CurrentUser):
    """Full page including all cells and their strokes."""
    return get_page(db, user, notebook_id, page_id)


@router.patch("/{page_id}", response_model=Page)
def update_page(notebook_id: UUID, page_id: UUID, body: PageUpdate, db: DB, user: CurrentUser):
    """Change the template, or reorder cells."""
    page = get_page(db, user, notebook_id, page_id)
    data = body.model_dump(exclude_unset=True)
    if "cell_order" in data:
        new_order = data.pop("cell_order")
        check_order(new_order, [c.id for c in page.cells], "cell_order")
        by_id = {c.id: c for c in page.cells}
        page.cells = [by_id[cid] for cid in new_order]
        page.cells.reorder()
    for field, value in data.items():
        setattr(page, field, value)
    touch(page)
    return page


@router.delete("/{page_id}", status_code=204)
def delete_page(notebook_id: UUID, page_id: UUID, db: DB, user: CurrentUser):
    nb = get_notebook(db, user, notebook_id)
    page = get_page(db, user, notebook_id, page_id)
    if len(nb.pages) == 1:
        raise HTTPException(409, "A notebook must keep at least one page")
    nb.pages.remove(page)
    nb.pages.reorder()
    nb.updated_at = models.now()
