from collections.abc import Awaitable, Callable

from langgraph.types import Command, Send
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import log_node
from app.graph.state import PushBranchPayload
from app.repositories import customer_owner_repository


async def resolve_owner(
    session: AsyncSession, organization_id: str, department_id: str
) -> dict | None:
    """Thin wrapper over customer_owner_repository.resolve_owner, returning a
    plain dict (not the ORM-backed OwnerMatch) so it's independently
    unit-testable without a graph and safe to carry through Send payloads."""
    match = await customer_owner_repository.resolve_owner(
        session, organization_id=organization_id, department_id=department_id
    )
    if match is None:
        return None
    return {
        "id": str(match.owner.id),
        "owner_name": match.owner.owner_name,
        "dingtalk_user_id": match.owner.dingtalk_user_id,
        "recipient_type": match.recipient_type,
    }


def make_resolve_owner_node(
    session_factory: async_sessionmaker,
) -> Callable[[PushBranchPayload], Awaitable[Command]]:
    """DB read, no RetryPolicy (not in spec §71's list). Always continues --
    owner=None just means build_message routes to the public group fallback
    (spec §62), not an error (spec §72)."""

    @log_node("resolve_owner")
    async def resolve_owner_node(payload: PushBranchPayload) -> Command:
        async with session_factory() as session:
            owner = await resolve_owner(
                session, payload["organization_id"], payload["department_id"]
            )
        return Command(goto=Send("build_message", {**payload, "owner": owner}))

    return resolve_owner_node
