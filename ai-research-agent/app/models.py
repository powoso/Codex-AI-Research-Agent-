from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    question: str = Field(min_length=5)
    constraints: dict[str, Any] | None = None
    urls: list[str] | None = None


class FollowupRequest(BaseModel):
    question: str = Field(min_length=3)


class RunCreateResponse(BaseModel):
    run_id: str


class RunStatusResponse(BaseModel):
    step: str
    progress: int
    logs: list[dict[str, Any]]


class RunResultResponse(BaseModel):
    report_md: str
    evidence_table: list[dict[str, Any]]
    sources: list[dict[str, Any]]


@dataclass
class QueueJob:
    run_id: str
    mode: Literal["start", "followup"]
    question: str | None = None
    enqueued_at: datetime = field(default_factory=datetime.utcnow)
