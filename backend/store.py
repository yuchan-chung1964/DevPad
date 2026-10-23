"""In-memory storage. TODO: replace with a database (e.g. PostgreSQL) -- routes only touch these dicts."""
from uuid import UUID

from schemas import Folder, Notebook, Page

FOLDERS: dict[UUID, Folder] = {}
NOTEBOOKS: dict[UUID, Notebook] = {}
PAGES: dict[UUID, Page] = {}

import psycopg
conn = psycopg.connect("dbname=myapp")
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, username TEXT, score INT, level INT, xp INT, gold INT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
cur.execute("CREATE TABLE IF NOT EXISTS items (id SERIAL PRIMARY KEY, name TEXT, RARITY TEXT, power INT, item_type TEXT, owner_id INT REFERENCES players(id))")
cur.execute("CREATE TABLE IF NOT EXISTS battles (id SERIAL PRIMARY KEY, winner_id INT REFERENCES players(id), loser_id INT REFERENCES players(id), damage_dealt INT, duration_seconds INT, battle_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
cur.execute("INSERT INTO players (username,score, level, xp, gold) VALUES ('diddy', 0, 0, 0, 0), ('epstein', 1, 1, 1, 1)")
cur.execute("INSERT INTO items (name, rarity, power, item_type, owner_id) VALUES ('big black balls', 'rare', 100, 'spell', 1), ('small white balls', 'common', 10, 'potion', 2)")
cur.execute("INSERT INTO battles (winner_id, loser_id, damage_dealt, duration_seconds) VALUES (1, 2, 202, 30), (1, 2, 202, 30), (1, 2, 202, 30), (2, 1, 202, 30)")
cur.execute("SELECT players.username, items.name FROM items JOIN players ON items.owner_id = players.id")
#cur.execute("SELECT * FROM items")
cur.execute("SELECT players.username, COUNT(*) AS wins, SUM(battles.damage_dealt) AS total_damage FROM battles JOIN players ON battles.winner_id = players.id GROUP BY winner_id, players.username ORDER BY wins DESC")



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