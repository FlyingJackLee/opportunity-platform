from app.core.logging import log_node
from app.graph.state import OpportunityState


@log_node("initialize")
async def initialize(state: OpportunityState) -> dict:
    """Normalizes the incoming event and marks the run as started."""
    return {"status": "RUNNING", "departments": []}
