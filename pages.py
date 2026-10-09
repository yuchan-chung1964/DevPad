from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.routes.notebooks import get_notebook
from app.schemas import Page, PageCreate, PageSummary, PageUpdate, Stroke, now
from app.store import PAGES

router = APIRouter(prefix="/notebooks/{notebook_id}/pages", tags=["pages"])


def get_page(notebook_id: UUID, page_id: UUID) -> Page:
    page = PAGES.get(page_id)
    if page is None or page.notebook_id != notebook_id:
        raise HTTPException(404, "Page not found")
    return page


def _touch(notebook_id: UUID, page: Page) -> None:
    page.updated_at = now()
    get_notebook(notebook_id).updated_at = page.updated_at


@router.get("", response_model=list[PageSummary])
def list_pages(notebook_id: UUID):
    """Pages in order, without stroke data."""
    nb = get_notebook(notebook_id)
    return [
        PageSummary(
            id=p.id,
            notebook_id=p.notebook_id,
            template=p.template,
            stroke_count=len(p.strokes),
            updated_at=p.updated_at,
        )
        for p in (PAGES[pid] for pid in nb.page_order)
    ]


@router.post("", response_model=Page, status_code=201)
def create_page(notebook_id: UUID, body: PageCreate):
    nb = get_notebook(notebook_id)
    page = Page(notebook_id=notebook_id, template=body.template)
    PAGES[page.id] = page
    position = body.position if body.position is not None else len(nb.page_order)
    nb.page_order.insert(position, page.id)
    nb.updated_at = now()
    return page


@router.get("/{page_id}", response_model=Page)
def read_page(notebook_id: UUID, page_id: UUID):
    """Full page including all strokes."""
    return get_page(notebook_id, page_id)


@router.patch("/{page_id}", response_model=Page)
def update_page(notebook_id: UUID, page_id: UUID, body: PageUpdate):
    page = get_page(notebook_id, page_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(page, field, value)
    _touch(notebook_id, page)
    return page


@router.delete("/{page_id}", status_code=204)
def delete_page(notebook_id: UUID, page_id: UUID):
    nb = get_notebook(notebook_id)
    get_page(notebook_id, page_id)
    if len(nb.page_order) == 1:
        raise HTTPException(409, "A notebook must keep at least one page")
    nb.page_order.remove(page_id)
    del PAGES[page_id]
    nb.updated_at = now()


# ---------- Strokes ----------
@router.post("/{page_id}/strokes", response_model=Page, status_code=201)
def add_strokes(notebook_id: UUID, page_id: UUID, strokes: list[Stroke]):
    """Append one or more strokes (call as the user draws, or in batches)."""
    page = get_page(notebook_id, page_id)
    page.strokes.extend(strokes)
    _touch(notebook_id, page)
    return page


@router.put("/{page_id}/strokes", response_model=Page)
def replace_strokes(notebook_id: UUID, page_id: UUID, strokes: list[Stroke]):
    """Replace all strokes on the page (full autosave / sync)."""
    page = get_page(notebook_id, page_id)
    page.strokes = strokes
    _touch(notebook_id, page)
    return page


@router.delete("/{page_id}/strokes/{stroke_id}", status_code=204)
def delete_stroke(notebook_id: UUID, page_id: UUID, stroke_id: UUID):
    """Erase a single stroke."""
    page = get_page(notebook_id, page_id)
    remaining = [s for s in page.strokes if s.id != stroke_id]
    if len(remaining) == len(page.strokes):
        raise HTTPException(404, "Stroke not found")
    page.strokes = remaining
    _touch(notebook_id, page)
