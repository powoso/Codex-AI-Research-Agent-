from __future__ import annotations

from enum import Enum


class Step(str, Enum):
    CLARIFY = "CLARIFY"
    PLAN = "PLAN"
    SELECT_SOURCES = "SELECT_SOURCES"
    FETCH = "FETCH"
    EXTRACT = "EXTRACT"
    EVALUATE = "EVALUATE"
    SYNTHESIZE = "SYNTHESIZE"
    ADVERSARIAL = "ADVERSARIAL"
    SAVE_OUTPUT = "SAVE_OUTPUT"
    DONE = "DONE"


STEP_PROGRESS = {
    Step.CLARIFY: 10,
    Step.PLAN: 20,
    Step.SELECT_SOURCES: 35,
    Step.FETCH: 50,
    Step.EXTRACT: 65,
    Step.EVALUATE: 75,
    Step.SYNTHESIZE: 88,
    Step.ADVERSARIAL: 95,
    Step.SAVE_OUTPUT: 99,
    Step.DONE: 100,
}
