"""Conditional-edge routing. route_to_score_fanout is the one real routing
function in Phase 2 -- dispatches Send("calculate_score", ...) per identified
department (ADR-0002). should_push's routing (Phase 4) will live here too."""

from langgraph.types import Send

from app.graph.state import OpportunityState, ScoreFanoutInput

UNKNOWN = "UNKNOWN"


def route_to_score_fanout(state: OpportunityState) -> list[Send]:
    """Guaranteed non-empty (see design judgment #3 in the Phase 2 plan): if
    Expert Judge identified zero departments, synthesize one UNKNOWN/UNKNOWN
    sentinel branch (spec §104 principle 6 -- UNKNOWN is sanctioned) so
    calculate_score -> finalize_result always runs at least once and the
    graph never hangs at mini_review."""
    expert_result = state["expert_result"]
    departments = expert_result.get("departments", [])
    event_analysis = state["event_analysis"]
    signals = event_analysis.get("signals", {})
    event_relevance = state["event"].get("filter_score") or 1.0

    org_scores = {
        org["organization_id"]: org["score"]
        for org in expert_result.get("organizations", [])
    }

    if not departments:
        payload: ScoreFanoutInput = {
            "run_id": state["run_id"],
            "department_id": UNKNOWN,
            "organization_id": UNKNOWN,
            "department_confidence": 0.0,
            "organization_score": 0.0,
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
