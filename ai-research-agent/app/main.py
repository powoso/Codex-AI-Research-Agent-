from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from app.agent.pipeline import create_run
from app.db import DB
from app.models import FollowupRequest, QueueJob, RunCreateRequest, RunCreateResponse, RunResultResponse, RunStatusResponse
from app.queue import JobQueue
from app.ui import render_ui

load_dotenv()

app = FastAPI(title="AI Research Agent Demo")
db = DB(os.getenv("DB_PATH", "app.db"))
queue = JobQueue(db)


@app.on_event("startup")
async def startup() -> None:
    db.migrate()
    await queue.start()


@app.get("/")
async def home():
    return render_ui()


@app.post("/api/research/run", response_model=RunCreateResponse)
async def create_research_run(req: RunCreateRequest) -> RunCreateResponse:
    run_id = create_run(db, req.question, req.constraints, req.urls)
    db.log(run_id, "INFO", "Run created", step="CREATE")
    return RunCreateResponse(run_id=run_id)


@app.post("/api/research/{run_id}/start")
async def start_research(run_id: str) -> dict:
    await queue.enqueue(QueueJob(run_id=run_id, mode="start"))
    db.log(run_id, "INFO", "Run queued", step="QUEUE")
    return {"ok": True}


@app.get("/api/research/{run_id}/status", response_model=RunStatusResponse)
async def run_status(run_id: str) -> RunStatusResponse:
    with db.conn() as c:
        row = c.execute("SELECT state_json FROM research_runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "run not found")
    state = json.loads(row[0] or "{}")
    return RunStatusResponse(step=state.get("step", "UNKNOWN"), progress=int(state.get("progress", 0)), logs=db.get_logs(run_id))


@app.get("/api/research/{run_id}", response_model=RunResultResponse)
async def run_result(run_id: str) -> RunResultResponse:
    with db.conn() as c:
        out = c.execute("SELECT report_md,evidence_json FROM outputs WHERE run_id=? ORDER BY id DESC LIMIT 1", (run_id,)).fetchone()
        src = [dict(r) for r in c.execute("SELECT tag,title,url,published_at,fetched_at FROM sources WHERE run_id=? ORDER BY id", (run_id,)).fetchall()]
    if not out:
        raise HTTPException(404, "output not ready")
    return RunResultResponse(report_md=out[0], evidence_table=json.loads(out[1] or "[]"), sources=src)


@app.post("/api/research/{run_id}/followup")
async def followup(run_id: str, req: FollowupRequest) -> dict:
    await queue.enqueue(QueueJob(run_id=run_id, mode="followup", question=req.question))
    db.log(run_id, "INFO", "Followup queued", step="QUEUE")
    return {"ok": True}
