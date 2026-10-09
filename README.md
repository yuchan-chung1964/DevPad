# Backend

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API docs: http://localhost:8000/docs

## Structure

Folder -> Notebook -> Page -> Stroke

| Resource | Endpoints |
|---|---|
| Folders | `POST/GET /folders`, `GET/PATCH/DELETE /folders/{id}` |
| Notebooks | `POST/GET /notebooks`, `GET/PATCH/DELETE /notebooks/{id}` |
| Pages | `GET/POST /notebooks/{id}/pages`, `GET/PATCH/DELETE /notebooks/{id}/pages/{page_id}` |
| Strokes | `POST/PUT /notebooks/{id}/pages/{page_id}/strokes`, `DELETE .../strokes/{stroke_id}` |

Storage is in-memory (`app/store.py`) -- data resets on restart.
