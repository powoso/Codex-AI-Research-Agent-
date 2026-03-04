from __future__ import annotations

import asyncio
import os

from app.agent.pipeline import create_run, execute_run
from app.db import DB


async def main() -> None:
    db = DB(os.getenv("DB_PATH", "app.db"))
    db.migrate()
    run_id = create_run(
        db,
        "How do major institutions frame AI risk management in 2026?",
        {"region": "global", "time_window": "last 3 years"},
        [],
    )
    await execute_run(db, run_id)
    print(f"Demo run complete: {run_id}")


if __name__ == "__main__":
    asyncio.run(main())
