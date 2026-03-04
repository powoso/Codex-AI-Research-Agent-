from __future__ import annotations

import asyncio

from app.agent.pipeline import execute_run
from app.db import DB
from app.models import QueueJob


class JobQueue:
    def __init__(self, db: DB) -> None:
        self.db = db
        self._queue: asyncio.Queue[QueueJob] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def enqueue(self, job: QueueJob) -> None:
        await self._queue.put(job)

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                await execute_run(self.db, job.run_id, question=job.question, followup=job.mode == "followup")
            except Exception as exc:  # noqa: BLE001
                self.db.log(job.run_id, "ERROR", f"job failed: {exc}", step="QUEUE")
            finally:
                self._queue.task_done()
