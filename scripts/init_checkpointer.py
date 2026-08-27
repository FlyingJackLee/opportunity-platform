"""Idempotent one-off: creates the langgraph-checkpoint-postgres tables
(checkpoints/checkpoint_blobs/checkpoint_writes/checkpoint_migrations).
Independent of Alembic (see app/graph/checkpoint.py). Run after `alembic
upgrade head`:

    uv run python scripts/init_checkpointer.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.graph.checkpoint import checkpointer_context, setup_checkpointer


async def main() -> None:
    settings = get_settings()
    async with checkpointer_context(settings) as checkpointer:
        await setup_checkpointer(checkpointer)
    print("checkpointer tables ready")


if __name__ == "__main__":
    asyncio.run(main())
