"""Request/response models for the notetaking API: Folder -> Notebook -> Page -> Cell -> Stroke."""
from datetime import datetime
from typing import Annotated, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from app.config import MAX_CODE_CHARS, MAX_POINTS_PER_STROKE, MAX_STROKES_PER_CELL

HexColor = Annotated[str, Field(pattern=r"^#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")]  # #RRGGBB or #RRGGBBAA
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Language = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Code = Annotated[str, StringConstraints(max_length=MAX_CODE_CHARS)]


def _not_null(value):
    if value is None:
        raise ValueError("may not be null")
    return value


# For PATCH fields that may be omitted but not explicitly set to null.
NotNull = BeforeValidator(_not_null)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Strokes ----------
class Point(BaseModel):
    x: float
    y: float
    t: float = 0.0                                 # timestamp / sequence, for stroke order and replay
    pressure: float = Field(1.0, ge=0.0, le=1.0)   # stylus pressure


class Stroke(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    points: list[Point] = Field(max_length=MAX_POINTS_PER_STROKE)
    tool: Literal["pen", "highlighter", "eraser"] = "pen"
    color: HexColor = "#000000"
    width: float = Field(2.0, gt=0)


Strokes = Annotated[list[Stroke], Field(max_length=MAX_STROKES_PER_CELL)]


# ---------- Cells ----------
CellKind = Literal["code", "text", "ink"]


class Cell(ORMModel):
    """A block on a page: code, typed text (content in `code`), or freehand ink. Any kind may carry strokes."""
    id: UUID
    page_id: UUID
    kind: CellKind
    language: str
    code: str
    strokes: list[Stroke]
    created_at: datetime
    updated_at: datetime


class CellCreate(BaseModel):
    kind: CellKind = "code"                       # fixed once created
    language: Language = "python"
    code: Code = ""
    strokes: Strokes = []
    position: Optional[int] = Field(None, ge=0)   # insert index; defaults to end


class CellUpdate(BaseModel):
    language: Annotated[Optional[Language], NotNull] = None
    code: Annotated[Optional[Code], NotNull] = None


# ---------- Pages ----------
PageTemplate = Literal["blank", "lined", "grid", "dotted"]


class Page(ORMModel):
    """Full page, including every cell and its strokes, in order."""
    id: UUID
    notebook_id: UUID
    title: str
    template: PageTemplate
    cells: list[Cell]
    created_at: datetime
    updated_at: datetime


class PageSummary(BaseModel):
    """Lightweight page info (no cells), e.g. for the page-thumbnail sidebar."""
    id: UUID
    notebook_id: UUID
    title: str
    template: PageTemplate
    cell_count: int
    updated_at: datetime


PageTitle = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]   # empty = untitled


class PageCreate(BaseModel):
    title: PageTitle = ""
    template: PageTemplate = "blank"
    position: Optional[int] = Field(None, ge=0)   # insert index; defaults to end


class PageUpdate(BaseModel):
    title: Annotated[Optional[PageTitle], NotNull] = None
    template: Annotated[Optional[PageTemplate], NotNull] = None
    cell_order: Annotated[Optional[list[UUID]], NotNull] = None   # send full new order to reorder cells


# ---------- Notebooks ----------
class Notebook(ORMModel):
    id: UUID
    folder_id: Optional[UUID]   # None = library root
    title: str
    cover_color: str
    page_order: list[UUID]
    created_at: datetime
    updated_at: datetime


class NotebookCreate(BaseModel):
    title: Name = "Untitled"
    folder_id: Optional[UUID] = None
    cover_color: HexColor = "#4A6FA5"
    template: PageTemplate = "blank"   # template of the first page


class NotebookUpdate(BaseModel):
    title: Annotated[Optional[Name], NotNull] = None
    folder_id: Optional[UUID] = None   # null moves the notebook to the library root
    cover_color: Annotated[Optional[HexColor], NotNull] = None
    page_order: Annotated[Optional[list[UUID]], NotNull] = None   # send full new order to reorder pages


# ---------- Folders ----------
class Folder(ORMModel):
    id: UUID
    parent_id: Optional[UUID]   # None = library root
    name: str
    created_at: datetime
    updated_at: datetime


class FolderCreate(BaseModel):
    name: Name
    parent_id: Optional[UUID] = None


class FolderUpdate(BaseModel):
    name: Annotated[Optional[Name], NotNull] = None
    parent_id: Optional[UUID] = None   # null moves the folder to the library root
