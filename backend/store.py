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
table for folders
- id (primary key)
- name
- created_at (timestamp)
- updated_at (timestamp)
"""
cur.execute("CREATE TABLE IF NOT EXISTS folders (id SERIAL PRIMARY KEY, name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

"""
table for notebooks
- id (primary key)
- name
- created_at (timestamp)
- updated_at (timestamp)
- pages (foreign key to pages table)
- folder_id (foreign key to folders table)
"""
cur.execute("CREATE TABLE IF NOT EXISTS notebooks (id SERIAL PRIMARY KEY, name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, folder_id INT REFERENCES folders(id))")

"""
table for pages
- id (primary key)
- name
- content (text)
- created_at (timestamp)
- updated_at (timestamp)
- strokes (foreign key to strokes table)
- notebook_id (foreign key to notebooks table)"""
cur.execute("CREATE TABLE IF NOT EXISTS pages (id SERIAL PRIMARY KEY, name TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notebook_id INT REFERENCES notebooks(id))")

"""
table for strokes
- id (primary key)
- stroke_data (JSON)
- created_at (timestamp)
- updated_at (timestamp)
- page_id (foreign key to pages table)
"""
cur.execute("CREATE TABLE IF NOT EXISTS strokes (id SERIAL PRIMARY KEY, stroke_data JSON, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, page_id INT REFERENCES pages(id))")
cur.execute("SELECT * FROM pages")
print(cur.fetchall())