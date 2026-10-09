"""In-memory storage. TODO: replace with a database (e.g. PostgreSQL) -- routes only touch these dicts."""
from uuid import UUID

from app.schemas import Folder, Notebook, Page

FOLDERS: dict[UUID, Folder] = {}
NOTEBOOKS: dict[UUID, Notebook] = {}
PAGES: dict[UUID, Page] = {}
