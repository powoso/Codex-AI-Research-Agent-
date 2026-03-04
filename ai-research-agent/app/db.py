from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS research_runs(
  id TEXT PRIMARY KEY,
  question TEXT NOT NULL,
  constraints_json TEXT,
  spec_json TEXT,
  state_json TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources(
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL,
  tag TEXT,
  url TEXT NOT NULL,
  title TEXT,
  domain TEXT,
  published_at TEXT,
  fetched_at TEXT,
  credibility REAL,
  status TEXT,
  content_type TEXT,
  bytes INTEGER
);
CREATE TABLE IF NOT EXISTS extracts(
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL,
  raw_text TEXT,
  cleaned_text TEXT,
  snippets_json TEXT
);
CREATE TABLE IF NOT EXISTS outputs(
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL,
  report_md TEXT,
  evidence_json TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS logs(
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  step TEXT,
  meta_json TEXT
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DB:
    def __init__(self, path: str = "app.db") -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def migrate(self) -> None:
        with self.conn() as c:
            c.executescript(SCHEMA_SQL)
            c.execute("PRAGMA journal_mode=WAL;")

    def log(self, run_id: str, level: str, message: str, step: str = "", meta: dict[str, Any] | None = None) -> None:
        with self.conn() as c:
            c.execute(
                "INSERT INTO logs(run_id, ts, level, message, step, meta_json) VALUES(?,?,?,?,?,?)",
                (run_id, utc_now(), level, message, step, json.dumps(meta or {})),
            )

    def get_logs(self, run_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.conn() as c:
            rows = c.execute(
                "SELECT ts, level, message, step, meta_json FROM logs WHERE run_id=? ORDER BY id DESC LIMIT ?",
                (run_id, limit),
            ).fetchall()
        return [dict(r) for r in rows][::-1]
