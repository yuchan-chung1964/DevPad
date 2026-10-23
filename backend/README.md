# Backend

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive API docs: http://localhost:8000/docs

## Structure

Folder -> Notebook -> Page -> Stroke

# wait shouldn't it be Folder -> Notebook -> Page -> Cell -> Stroke? Each cell should have the code it runs saved along w/ corresponding strokes

| Resource | Endpoints |
|---|---|
| Folders | `POST/GET /folders`, `GET/PATCH/DELETE /folders/{id}` |
| Notebooks | `POST/GET /notebooks`, `GET/PATCH/DELETE /notebooks/{id}` |
| Pages | `GET/POST /notebooks/{id}/pages`, `GET/PATCH/DELETE /notebooks/{id}/pages/{page_id}` |
| Strokes | `POST/PUT /notebooks/{id}/pages/{page_id}/strokes`, `DELETE .../strokes/{stroke_id}` |

Storage is in-memory (`app/store.py`) -- data resets on restart.
