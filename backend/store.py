"""In-memory storage. TODO: replace with a database (e.g. PostgreSQL) -- routes only touch these dicts."""
from uuid import UUID

from schemas import Folder, Notebook, Page

FOLDERS: dict[UUID, Folder] = {}
NOTEBOOKS: dict[UUID, Notebook] = {}
PAGES: dict[UUID, Page] = {}

import psycopg
conn = psycopg.connect("dbname=myapp")
cur = conn.cursor()

"""
table for users
- id (primary key)
- username
- password
- created_at (timestamp)
- updated_at (timestamp)
- folders (foreign key to folders table)
"""

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

"""
table for folders
- id (primary key)
- name
- created_at (timestamp)
- updated_at (timestamp)
- notebooks (foreign key to notebooks table)
"""
cur.execute("""
CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    parent_id UUID,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

"""
table for notebooks
- id (primary key)
- name
- created_at (timestamp)
- updated_at (timestamp)
- pages (foreign key to pages table)
- folder_id (foreign key to folders table)
"""
cur.execute("""
CREATE TABLE IF NOT EXISTS notebooks (
    id UUID PRIMARY KEY,
    folder_id UUID,
    title TEXT NOT NULL,
    cover_color TEXT NOT NULL DEFAULT '#4A6FA5',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);""")

"""
table for pages
- id (primary key)
- name
- content (text)
- created_at (timestamp)
- updated_at (timestamp)
- strokes (foreign key to strokes table)
- notebook_id (foreign key to notebooks table)"""
cur.execute("""
CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY,
    notebook_id UUID NOT NULL,
    template TEXT NOT NULL DEFAULT 'blank',
    position INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);""")

"""
table for strokes
- id (primary key)
- stroke_data (JSON)
- created_at (timestamp)
- updated_at (timestamp)
- page_id (foreign key to pages table)
"""
cur.execute("""
CREATE TABLE IF NOT EXISTS cells (
    id UUID PRIMARY KEY,
    page_id UUID NOT NULL,
    code TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL
);""")

cur.execute("""
CREATE TABLE IF NOT EXISTS strokes (
    id UUID PRIMARY KEY,
    cell_id UUID NOT NULL,
    position INTEGER NOT NULL,
    stroke_data JSONB NOT NULL
);""")

cur.execute("SELECT * FROM pages")
print(cur.fetchall())