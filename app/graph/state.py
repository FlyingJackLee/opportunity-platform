"""LangGraph state shapes.

Differs from spec §67's `OpportunityState` on purpose — see
docs/adr/0001-opportunity-not-persisted.md and
docs/adr/0002-score-per-department-fanout.md, and the CONTEXT.md glossary:

- No `stage` field anywhere: "商机阶段"/Opportunity Stage was dropped during
  design (see CONTEXT.md "Need Maturity" entry) in favor of Need Maturity alone.
- `owner`/`push_result` are not flat top-level fields. Each identified
  Department is an independent Opportunity (ADR-0001) that scores, decides,
  and pushes on its own (ADR-0002) — so those fields live on
  `DepartmentBranchState`, one per department, not once per run.
- `departments` uses `Annotated[list[...], operator.add]`, the LangGraph-
  idiomatic way for parallel `Send()`-dispatched branches to each contribute
  one item to a shared list without racing. Phase 1 does not dispatch `Send()`
  anywhere yet (calculate_score and friends don't exist until Phase 2/4) —
  this shape is fixed now purely so Phase 2/4 don't have to change
  `OpportunityState` again.
- Top-level `score`/`level`/`confidence` are a display-only rollup ("highest
  among all departments in this run" — see CONTEXT.md "Score Level"), never a
  push decision input; the authoritative values are per-department.
"""

import operator
from typing import Annotated, TypedDict


class DepartmentBranchState(TypedDict):
    """One fan-out branch = one independent Opportunity."""

    department_id: str
    organization_id: str
    score: float
    level: str
    confidence: float
    should_push: bool
    owner: dict | None
    push_result: dict | None
    error: str | None


class ScoreFanoutInput(TypedDict):
    """Payload dispatched via Send("calculate_score", ...) -- one per
    identified department (or a synthetic UNKNOWN sentinel if the run
    identified none, so the fan-out is never empty and finalize_result always
    runs). Deliberately a separate, narrower shape than OpportunityState:
    calculate_score only ever needs one department's slice of the run."""

    run_id: str
    department_id: str
    organization_id: str
    department_confidence: float
    organization_score: float
    related_needs: list[dict]
    related_capabilities: list[dict]
    event_relevance: float
    project_signal: (
        str  # raw SignalLevel value, mapped to a weight in calculate_score.py
    )
    procurement_signal: str


class OpportunityState(TypedDict):
    run_id: str
    event: dict
    event_analysis: dict

    industry_context: list
    organization_context: list
    capability_context: list

    expert_result: dict
    model_version: str | None

    event_prompt_version: str | None
    judge_prompt_version: str | None
    review_prompt_version: str | None

    score: float | None
    level: str | None
    confidence: float | None

    review_result: dict

    departments: Annotated[list[DepartmentBranchState], operator.add]

    final_result: dict | None

    status: str
    error: str | None
