---
title: Helix Backend
emoji: 🧬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# Helix — backend (FastAPI)

Phase 1: a thin API that streams agent events to the Studio. The pipeline is a
scripted mock today and is swapped for the real LangGraph agents in Phase 2,
behind the same `/api/run` contract.

## Run

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then point the frontend at it: in `frontend/.env.local` set
`NEXT_PUBLIC_API_URL=http://localhost:8000` and reload the Studio. With no
backend running, the Studio falls back to its built-in simulation.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | liveness check |
| GET | `/api/datasets` | sample dataset metadata |
| POST | `/api/run` | **SSE** stream of `{stage, status, log}` events, then `result`, then `done` |

### `/api/run` event protocol

Each SSE `data:` line is one JSON object:

- `{"t":"start","dataset":"…"}`
- `{"t":"event","stage":"planner","status":"active"|"done"|"error"|null,"log":{"text":"…","kind":"info|code|ok|err|warn|muted"}|null}`
- `{"t":"result","results":{…}}`  (matches the frontend `RunResults` type)
- `{"t":"done"}`
