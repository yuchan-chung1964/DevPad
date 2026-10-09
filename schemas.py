"""Data models for the notetaking API: Folder -> Notebook -> Page -> Stroke."""
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Strokes ----------
class Point(BaseModel):
    x: float
    y: float
    t: float = 0.0           # timestamp / sequence, for stroke order and replay
    pressure: float = 1.0    # stylus pressure, 0..1


class Stroke(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    points: list[Point]
    tool: Literal["pen", "highlighter", "eraser"] = "pen"
    color: str = "#000000"   # hex
    width: float = 2.0


# ---------- Pages ----------
PageTemplate = Literal["blank", "lined", "grid", "dotted"]


class Page(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    notebook_id: UUID
    template: PageTemplate = "blank"
    strokes: list[Stroke] = []
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class PageSummary(BaseModel):
    """Lightweight page info (no strokes), e.g. for the page-thumbnail sidebar."""
    id: UUID
    notebook_id: UUID
    template: PageTemplate
    stroke_count: int
    updated_at: datetime


class PageCreate(BaseModel):
    template: PageTemplate = "blank"
    position: Optional[int] = None   # insert index; defaults to end


class PageUpdate(BaseModel):
    template: Optional[PageTemplate] = None


# ---------- Notebooks ----------
class Notebook(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    folder_id: Optional[UUID] = None   # None = library root
    title: str
    cover_color: str = "#4A6FA5"
    page_order: list[UUID] = []
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class NotebookCreate(BaseModel):
    title: str = "Untitled"
    folder_id: Optional[UUID] = None
    cover_color: str = "#4A6FA5"
    template: PageTemplate = "blank"   # template of the first page


class NotebookUpdate(BaseModel):
    title: Optional[str] = None
    folder_id: Optional[UUID] = None
    cover_color: Optional[str] = None
    page_order: Optional[list[UUID]] = None   # send full new order to reorder pages


# ---------- Folders ----------
class Folder(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    parent_id: Optional[UUID] = None   # None = library root
    name: str
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[UUID] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[UUID] = None
