from __future__ import annotations

import json
import os
import uuid
from urllib.parse import urlparse

from app.agent.citations import assign_tags, validate_citations
from app.agent.scoring import rank_urls
from app.agent.state import STEP_PROGRESS, Step
from app.agent.synthesis import build_report
from app.db import DB, utc_now
from app.extract.extract import extract_document
from app.fetcher.http import fetch_url


async def execute_run(db: DB, run_id: str, question: str | None = None, followup: bool = False) -> None:
    with db.conn() as c:
        run = c.execute("SELECT * FROM research_runs WHERE id=?", (run_id,)).fetchone()
        if not run:
            return
        q = question or run["question"]

    await _set_step(db, run_id, Step.CLARIFY, "Building research spec")
    spec = {
        "question": q,
        "definitions": ["AI systems", "risk", "benefit"],
        "scope": "Publicly available web sources from seed corpus and user URLs",
        "exclusions": ["Private/paywalled data"],
    }
    _update_run_state(db, run_id, spec=spec)

    await _set_step(db, run_id, Step.PLAN, "Planning sub-questions")
    keywords = [w.lower() for w in q.split() if len(w) > 3][:12]
    plan = {"sub_questions": [q, f"evidence for {q[:50]}"], "keywords": keywords}
    _update_run_state(db, run_id, plan=plan)

    await _set_step(db, run_id, Step.SELECT_SOURCES, "Selecting sources")
    seeds = json.loads(open("data/seeds.json", "r", encoding="utf-8").read())
    with db.conn() as c:
        run_row = c.execute("SELECT constraints_json FROM research_runs WHERE id=?", (run_id,)).fetchone()
    constraints = json.loads(run_row[0] or "{}")
    user_urls = constraints.get("urls", [])[:20]
    ranked = rank_urls(q, seeds)
    max_sources = min(int(os.getenv("MAX_SOURCES", "12")), 20)
    selected = [u for u, _ in ranked[:max_sources]]
    for u in user_urls:
        if u not in selected:
            selected.append(u)
    selected = selected[:20]

    with db.conn() as c:
        c.execute("DELETE FROM sources WHERE run_id=?", (run_id,))
        for u in selected:
            c.execute(
                "INSERT INTO sources(run_id,url,domain,status) VALUES(?,?,?,?)",
                (run_id, u, urlparse(u).netloc, "selected"),
            )
        source_ids = [r[0] for r in c.execute("SELECT id FROM sources WHERE run_id=? ORDER BY id", (run_id,)).fetchall()]
        tags = assign_tags(source_ids)
        for sid, tag in tags.items():
            c.execute("UPDATE sources SET tag=? WHERE id=?", (tag, sid))

    await _set_step(db, run_id, Step.FETCH, "Fetching pages")
    max_bytes = int(os.getenv("MAX_BYTES", "2097152"))
    tconn = float(os.getenv("HTTP_TIMEOUT_CONNECT", "5"))
    tread = float(os.getenv("HTTP_TIMEOUT_READ", "12"))
    with db.conn() as c:
        src_rows = c.execute("SELECT id,url FROM sources WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
    for src in src_rows:
        result = await fetch_url(src["url"], max_bytes=max_bytes, timeout_connect=tconn, timeout_read=tread)
        with db.conn() as c:
            if not result.get("ok"):
                c.execute("UPDATE sources SET status=? WHERE id=?", (result.get("status", "failed"), src["id"]))
                c.execute(
                    "INSERT INTO logs(run_id, ts, level, message, step, meta_json) VALUES(?,?,?,?,?,?)",
                    (run_id, utc_now(), "WARN", f"Fetch failed: {result.get('error')}", Step.FETCH.value, json.dumps({"url": src["url"]})),
                )
                continue
            c.execute(
                "UPDATE sources SET status=?, fetched_at=?, content_type=?, bytes=?, url=? WHERE id=?",
                ("fetched", utc_now(), result["content_type"], result["bytes"], result["url"], src["id"]),
            )
            c.execute(
                "INSERT INTO extracts(source_id, raw_text, cleaned_text, snippets_json) VALUES(?,?,?,?)",
                (src["id"], result["content"], "", "[]"),
            )

    await _set_step(db, run_id, Step.EXTRACT, "Extracting readable text")
    with db.conn() as c:
        rows = c.execute(
            "SELECT e.id as extract_id, e.source_id, e.raw_text, s.url FROM extracts e JOIN sources s ON s.id=e.source_id WHERE s.run_id=?",
            (run_id,),
        ).fetchall()
    for row in rows:
        doc = extract_document(row["raw_text"], row["url"])
        with db.conn() as c:
            c.execute("UPDATE extracts SET cleaned_text=?, snippets_json=? WHERE id=?", (doc["cleaned_text"], json.dumps(doc["snippets"]), row["extract_id"]))
            c.execute("UPDATE sources SET title=?, published_at=? WHERE id=?", (doc["title"], doc["published_at"], row["source_id"]))

    await _set_step(db, run_id, Step.EVALUATE, "Evaluating credibility")
    with db.conn() as c:
        srcs = c.execute("SELECT id,domain,published_at FROM sources WHERE run_id=?", (run_id,)).fetchall()
        for s in srcs:
            score = 0.4
            if s["domain"].endswith(".gov") or s["domain"].endswith(".edu"):
                score += 0.35
            if any(x in s["domain"] for x in ["nature", "science", "oecd", "nist", "who"]):
                score += 0.2
            if s["published_at"]:
                score += 0.05
            c.execute("UPDATE sources SET credibility=? WHERE id=?", (round(min(score, 0.99), 2), s["id"]))

    await _set_step(db, run_id, Step.SYNTHESIZE, "Synthesizing report")
    with db.conn() as c:
        ex_rows = c.execute(
            "SELECT e.source_id,e.cleaned_text,e.snippets_json,s.tag,s.domain,s.credibility FROM extracts e JOIN sources s ON s.id=e.source_id WHERE s.run_id=? AND s.status='fetched'",
            (run_id,),
        ).fetchall()
    extracts = [{"source_id": r["source_id"], "cleaned_text": r["cleaned_text"], "snippets": json.loads(r["snippets_json"] or "[]")} for r in ex_rows if r["cleaned_text"]]
    source_map = {r["source_id"]: {"tag": r["tag"], "domain": r["domain"], "credibility": r["credibility"]} for r in ex_rows}
    report, evidence = build_report(q, extracts, source_map)

    await _set_step(db, run_id, Step.ADVERSARIAL, "Generating counterarguments")
    report += "\n\n## Adversarial counterarguments\n"
    report += "1. Selection bias from seed corpus may miss dissenting evidence [S1].\n"
    report += "2. Freshness risk: some sources may be outdated [S1].\n"
    report += "3. Publication incentives can overstate outcomes [S1].\n"

    with db.conn() as c:
        allowed_tags = {r[0] for r in c.execute("SELECT tag FROM sources WHERE run_id=?", (run_id,)).fetchall()}
    missing = validate_citations(report, allowed_tags)
    if missing:
        report += f"\n\nCitation validation warning: missing tags {missing}."

    await _set_step(db, run_id, Step.SAVE_OUTPUT, "Saving output")
    with db.conn() as c:
        c.execute("INSERT INTO outputs(run_id, report_md, evidence_json, created_at) VALUES(?,?,?,?)", (run_id, report, json.dumps(evidence), utc_now()))
        c.execute("UPDATE research_runs SET state_json=? WHERE id=?", (json.dumps({"step": Step.DONE.value, "progress": 100}), run_id))

    with db.conn() as c:
        src_list = [dict(r) for r in c.execute("SELECT tag,title,url,published_at,fetched_at FROM sources WHERE run_id=? ORDER BY id", (run_id,)).fetchall()]
        out = {
            "run_id": run_id,
            "question": q,
            "report_md": report,
            "evidence_table": evidence,
            "sources": src_list,
        }
    os.makedirs("data/outputs", exist_ok=True)
    with open("data/outputs/sample_run.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def create_run(db: DB, question: str, constraints: dict | None, urls: list[str] | None) -> str:
    run_id = str(uuid.uuid4())
    payload = constraints or {}
    payload["urls"] = (urls or [])[:20]
    with db.conn() as c:
        c.execute(
            "INSERT INTO research_runs(id, question, constraints_json, spec_json, state_json, created_at) VALUES(?,?,?,?,?,?)",
            (run_id, question, json.dumps(payload), "{}", json.dumps({"step": "CREATED", "progress": 0}), utc_now()),
        )
    return run_id


def _update_run_state(db: DB, run_id: str, **kwargs: object) -> None:
    with db.conn() as c:
        state = c.execute("SELECT state_json FROM research_runs WHERE id=?", (run_id,)).fetchone()[0]
        obj = json.loads(state or "{}")
        obj.update(kwargs)
        c.execute("UPDATE research_runs SET state_json=?, spec_json=? WHERE id=?", (json.dumps(obj), json.dumps(kwargs), run_id))


async def _set_step(db: DB, run_id: str, step: Step, msg: str) -> None:
    with db.conn() as c:
        current = c.execute("SELECT state_json FROM research_runs WHERE id=?", (run_id,)).fetchone()[0]
        st = json.loads(current or "{}")
        st["step"] = step.value
        st["progress"] = STEP_PROGRESS[step]
        c.execute("UPDATE research_runs SET state_json=? WHERE id=?", (json.dumps(st), run_id))
    db.log(run_id, "INFO", msg, step=step.value)
