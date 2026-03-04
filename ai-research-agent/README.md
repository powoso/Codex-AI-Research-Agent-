# AI Research Agent (Demo Mode)

Python-only AI research workflow with FastAPI UI + JSON API, SQLite storage, in-process queue, and no API keys.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>

## Environment

Copy `.env.example` to `.env` and tweak limits as needed.

## Run demo headlessly

```bash
python -m app.scripts.run_demo
```

Generates `data/outputs/sample_run.json`.

## API

- `POST /api/research/run`
- `POST /api/research/{run_id}/start`
- `GET /api/research/{run_id}/status`
- `GET /api/research/{run_id}`
- `POST /api/research/{run_id}/followup`

## Notes

- Source selection is from `data/seeds.json` + optional user URLs.
- Fetch safety blocks localhost/private network ranges and unsupported schemes.
- Citations use stable tags `[S1..SN]` per run.
