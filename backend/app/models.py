"""Database tables: Folder -> Notebook -> Page -> Cell (strokes are stored as JSON on the cell)."""
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, TypeDecorator
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Always returns timezone-aware UTC datetimes (SQLite drops tzinfo on its own)."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value: Optional[datetime], dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    pass


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)


class Folder(Timestamped, Base):
    __tablename__ = "folders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("folders.id"), index=True)  # None = library root
    name: Mapped[str] = mapped_column(String(200))


class Notebook(Timestamped, Base):
    __tablename__ = "notebooks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    folder_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("folders.id"), index=True)  # None = library root
    title: Mapped[str] = mapped_column(String(200))
    cover_color: Mapped[str] = mapped_column(String(9), default="#4A6FA5")

    pages: Mapped[list["Page"]] = relationship(
        back_populates="notebook",
        order_by="Page.position",
        collection_class=ordering_list("position"),
        cascade="all, delete-orphan",
    )

    @property
    def page_order(self) -> list[UUID]:
        return [p.id for p in self.pages]


class Page(Timestamped, Base):
    __tablename__ = "pages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    notebook_id: Mapped[UUID] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    template: Mapped[str] = mapped_column(String(16), default="blank")

    notebook: Mapped[Notebook] = relationship(back_populates="pages")
    cells: Mapped[list["Cell"]] = relationship(
        back_populates="page",
        order_by="Cell.position",
        collection_class=ordering_list("position"),
        cascade="all, delete-orphan",
    )


class Cell(Timestamped, Base):
    """A block on a page: handwritten strokes plus the code they represent."""
    __tablename__ = "cells"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    page_id: Mapped[UUID] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    language: Mapped[str] = mapped_column(String(32), default="python")
    code: Mapped[str] = mapped_column(Text, default="")
    # Always reassign (never mutate in place) so SQLAlchemy notices the change.
    strokes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    page: Mapped[Page] = relationship(back_populates="cells")
