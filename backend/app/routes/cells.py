from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.db import DB
from app.routes.pages import get_page, insert_at, touch
from app.schemas import Cell, CellCreate, CellUpdate, Stroke

router = APIRouter(prefix="/notebooks/{notebook_id}/pages/{page_id}/cells", tags=["cells"])


def get_cell(db: Session, notebook_id: UUID, page_id: UUID, cell_id: UUID) -> models.Cell:
    page = get_page(db, notebook_id, page_id)
    cell = db.get(models.Cell, cell_id)
    if cell is None or cell.page_id != page.id:
        raise HTTPException(404, "Cell not found")
    return cell


def _touch(cell: models.Cell) -> None:
    touch(cell.page)
    cell.updated_at = cell.page.updated_at


def _dump(strokes: list[Stroke]) -> list[dict]:
    return [s.model_dump(mode="json") for s in strokes]


@router.get("", response_model=list[Cell])
def list_cells(notebook_id: UUID, page_id: UUID, db: DB):
    """Cells on the page, in order, with their strokes."""
    return get_page(db, notebook_id, page_id).cells


@router.post("", response_model=Cell, status_code=201)
def create_cell(notebook_id: UUID, page_id: UUID, body: CellCreate, db: DB):
    page = get_page(db, notebook_id, page_id)
    cell = models.Cell(language=body.language, code=body.code, strokes=_dump(body.strokes))
    insert_at(page.cells, cell, body.position)
    touch(page)
    db.flush()
    return cell


@router.get("/{cell_id}", response_model=Cell)
def read_cell(notebook_id: UUID, page_id: UUID, cell_id: UUID, db: DB):
    return get_cell(db, notebook_id, page_id, cell_id)


@router.patch("/{cell_id}", response_model=Cell)
def update_cell(notebook_id: UUID, page_id: UUID, cell_id: UUID, body: CellUpdate, db: DB):
    """Update the cell's code or language."""
    cell = get_cell(db, notebook_id, page_id, cell_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cell, field, value)
    _touch(cell)
    return cell


@router.delete("/{cell_id}", status_code=204)
def delete_cell(notebook_id: UUID, page_id: UUID, cell_id: UUID, db: DB):
    cell = get_cell(db, notebook_id, page_id, cell_id)
    page = cell.page
    page.cells.remove(cell)
    page.cells.reorder()
    touch(page)


# ---------- Strokes ----------
@router.post("/{cell_id}/strokes", response_model=Cell, status_code=201)
def add_strokes(notebook_id: UUID, page_id: UUID, cell_id: UUID, strokes: list[Stroke], db: DB):
    """Append one or more strokes (call as the user draws, or in batches)."""
    cell = get_cell(db, notebook_id, page_id, cell_id)
    cell.strokes = cell.strokes + _dump(strokes)
    _touch(cell)
    return cell


@router.put("/{cell_id}/strokes", response_model=Cell)
def replace_strokes(notebook_id: UUID, page_id: UUID, cell_id: UUID, strokes: list[Stroke], db: DB):
    """Replace all strokes in the cell (full autosave / sync)."""
    cell = get_cell(db, notebook_id, page_id, cell_id)
    cell.strokes = _dump(strokes)
    _touch(cell)
    return cell


@router.delete("/{cell_id}/strokes/{stroke_id}", status_code=204)
def delete_stroke(notebook_id: UUID, page_id: UUID, cell_id: UUID, stroke_id: UUID, db: DB):
    """Erase a single stroke."""
    cell = get_cell(db, notebook_id, page_id, cell_id)
    remaining = [s for s in cell.strokes if s["id"] != str(stroke_id)]
    if len(remaining) == len(cell.strokes):
        raise HTTPException(404, "Stroke not found")
    cell.strokes = remaining
    _touch(cell)
