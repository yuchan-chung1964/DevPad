from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app import config, models
from app.auth import CurrentUser
from app.db import DB
from app.ratelimit import enforce_quota
from app.routes.pages import get_page, insert_at, touch
from app.schemas import Cell, CellCreate, CellUpdate, Stroke, Strokes

router = APIRouter(prefix="/notebooks/{notebook_id}/pages/{page_id}/cells", tags=["cells"])


def get_cell(db: Session, user: models.User, notebook_id: UUID, page_id: UUID, cell_id: UUID) -> models.Cell:
    page = get_page(db, user, notebook_id, page_id)
    cell = db.get(models.Cell, cell_id)
    if cell is None or cell.page_id != page.id:
        raise HTTPException(404, "Cell not found")
    return cell


def _touch(cell: models.Cell) -> None:
    touch(cell.page)
    cell.updated_at = cell.page.updated_at


def _dump(strokes: list[Stroke]) -> list[dict]:
    return [s.model_dump(mode="json") for s in strokes]


def _check_stroke_count(count: int) -> None:
    if count > config.MAX_STROKES_PER_CELL:
        raise HTTPException(413, f"A cell can hold at most {config.MAX_STROKES_PER_CELL} strokes")


@router.get("", response_model=list[Cell])
def list_cells(notebook_id: UUID, page_id: UUID, db: DB, user: CurrentUser):
    """Cells on the page, in order, with their strokes."""
    return get_page(db, user, notebook_id, page_id).cells


@router.post("", response_model=Cell, status_code=201)
def create_cell(notebook_id: UUID, page_id: UUID, body: CellCreate, db: DB, user: CurrentUser):
    page = get_page(db, user, notebook_id, page_id)
    enforce_quota(len(page.cells), config.MAX_CELLS_PER_PAGE, "cells per page")
    cell = models.Cell(language=body.language, code=body.code, strokes=_dump(body.strokes))
    insert_at(page.cells, cell, body.position)
    touch(page)
    db.flush()
    return cell


@router.get("/{cell_id}", response_model=Cell)
def read_cell(notebook_id: UUID, page_id: UUID, cell_id: UUID, db: DB, user: CurrentUser):
    return get_cell(db, user, notebook_id, page_id, cell_id)


@router.patch("/{cell_id}", response_model=Cell)
def update_cell(notebook_id: UUID, page_id: UUID, cell_id: UUID, body: CellUpdate, db: DB, user: CurrentUser):
    """Update the cell's code or language."""
    cell = get_cell(db, user, notebook_id, page_id, cell_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cell, field, value)
    _touch(cell)
    return cell


@router.delete("/{cell_id}", status_code=204)
def delete_cell(notebook_id: UUID, page_id: UUID, cell_id: UUID, db: DB, user: CurrentUser):
    cell = get_cell(db, user, notebook_id, page_id, cell_id)
    page = cell.page
    page.cells.remove(cell)
    page.cells.reorder()
    touch(page)


# ---------- Strokes ----------
@router.post("/{cell_id}/strokes", response_model=Cell, status_code=201)
def add_strokes(notebook_id: UUID, page_id: UUID, cell_id: UUID, strokes: Strokes, db: DB, user: CurrentUser):
    """Append one or more strokes (call as the user draws, or in batches)."""
    cell = get_cell(db, user, notebook_id, page_id, cell_id)
    _check_stroke_count(len(cell.strokes) + len(strokes))
    cell.strokes = cell.strokes + _dump(strokes)
    _touch(cell)
    return cell


@router.put("/{cell_id}/strokes", response_model=Cell)
def replace_strokes(notebook_id: UUID, page_id: UUID, cell_id: UUID, strokes: Strokes, db: DB, user: CurrentUser):
    """Replace all strokes in the cell (full autosave / sync)."""
    cell = get_cell(db, user, notebook_id, page_id, cell_id)
    cell.strokes = _dump(strokes)
    _touch(cell)
    return cell


@router.delete("/{cell_id}/strokes/{stroke_id}", status_code=204)
def delete_stroke(notebook_id: UUID, page_id: UUID, cell_id: UUID, stroke_id: UUID, db: DB, user: CurrentUser):
    """Erase a single stroke."""
    cell = get_cell(db, user, notebook_id, page_id, cell_id)
    remaining = [s for s in cell.strokes if s["id"] != str(stroke_id)]
    if len(remaining) == len(cell.strokes):
        raise HTTPException(404, "Stroke not found")
    cell.strokes = remaining
    _touch(cell)
