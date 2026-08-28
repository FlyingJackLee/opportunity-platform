"""Conditional-edge routing. route_to_score_fanout dispatches
Send("calculate_score", ...) per identified department (ADR-0002).
route_to_push_fanout (Phase 4) dispatches Send("should_push", ...) per
department in the finalized result, starting the push chain."""

from langgraph.types import Send

from app.graph.state import OpportunityState, PushBranchPayload, ScoreFanoutInput

UNKNOWN = "UNKNOWN"


def route_to_score_fanout(state: OpportunityState) -> list[Send]:
    """Guaranteed non-empty (see design judgment #3 in the Phase 2 plan): if
    Expert Judge identified zero departments, synthesize one sentinel branch
    (spec §104 principle 6 -- UNKNOWN is sanctioned) so calculate_score ->
    finalize_result always runs at least once and the graph never hangs at
    mini_review. If an Organization was identified but no Department was
    (CONTEXT.md: Opportunity granularity falls back to the whole
    Organization in that case), the sentinel uses that real organization_id
    -- not a fully-unknown one -- so Organization-level owner routing
    (Phase 4) can still resolve. Fixed here from Phase 2's original version,
    which hardcoded organization_id=UNKNOWN even when an organization was
    identified."""
    expert_result = state["expert_result"]
    departments = expert_result.get("departments", [])
    event_analysis = state["event_analysis"]
    signals = event_analysis.get("signals", {})
    event_relevance = state["event"].get("filter_score") or 1.0

    organizations = expert_result.get("organizations", [])
    org_scores = {org["organization_id"]: org["score"] for org in organizations}

    if not departments:
        sentinel_organization_id = (
            organizations[0]["organization_id"] if organizations else UNKNOWN
        )
        payload: ScoreFanoutInput = {
            "run_id": state["run_id"],
            "department_id": UNKNOWN,
            "organization_id": sentinel_organization_id,
            "department_confidence": 0.0,
            "organization_score": org_scores.get(sentinel_organization_id, 0.0),
            "related_needs": [],
            "related_capabilities": [],
            "event_relevance": event_relevance,
            "project_signal": signals.get("project_signal", UNKNOWN),
            "procurement_signal": signals.get("procurement_signal", UNKNOWN),
        }
        return [Send("calculate_score", payload)]

    sends = []
    for dept in departments:
        payload = {
            "run_id": state["run_id"],
            "department_id": dept["department_id"],
            "organization_id": dept["organization_id"],
            "department_confidence": dept["confidence"],
            "organization_score": org_scores.get(dept["organization_id"], 0.0),
            "related_needs": dept.get("related_needs", []),
            "related_capabilities": dept.get("related_capabilities", []),
            "event_relevance": event_relevance,
            "project_signal": signals.get("project_signal", UNKNOWN),
            "procurement_signal": signals.get("procurement_signal", UNKNOWN),
        }
        sends.append(Send("calculate_score", payload))
    return sends


def route_to_push_fanout(state: OpportunityState) -> list[Send]:
    """Dispatches Send("should_push", ...) per department in the finalized
    result (spec §57-58). Reads state["final_result"]["departments"] --
    the richer FinalResult shape (role/related_needs/related_capabilities),
    not the leaner state["departments"] list calculate_score produced.
    Always non-empty: finalize_result guarantees at least the sentinel
    branch from route_to_score_fanout survives through to FinalResult."""
    final_result = state["final_result"]
    event = state["event"]

    sends = []
    for dept in final_result["departments"]:
        payload: PushBranchPayload = {
            "run_id": state["run_id"],
            "event_id": final_result["event_id"],
            "event_title": event["title"],
            "event_source_url": event.get("source_url"),
            "summary": final_result.get("summary", ""),
            "risks": final_result.get("risks", []),
            "recommended_action": final_result.get("recommended_action", ""),
            "department_id": dept["department_id"],
            "organization_id": dept["organization_id"],
            "role": dept.get("role", UNKNOWN),
            "score": dept["score"],
            "level": dept["level"],
            "confidence": dept["confidence"],
            "related_needs": dept.get("related_needs", []),
            "related_capabilities": dept.get("related_capabilities", []),
            "should_push": False,
            "skip_reason": None,
            "owner": None,
            "message": None,
            "recipient_type": None,
            "recipient_id": None,
            "push_result": None,
            "error": None,
        }
        sends.append(Send("should_push", payload))
    return sends
