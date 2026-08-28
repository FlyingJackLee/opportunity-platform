"""resize embedding columns to 1024 (BGE-m3)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-28

"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_DIMENSION = 1536
NEW_DIMENSION = 1024

# A vector from one embedding model can't be reinterpreted as another
# dimension -- there's no meaningful cast, only re-ingestion. Since one-期
# hasn't started real data prep yet (spec §102), both tables are expected to
# be empty; TRUNCATE makes that assumption explicit instead of silently
# nulling out NOT NULL columns (which would fail anyway if rows existed).
def upgrade() -> None:
    op.execute("TRUNCATE knowledge_chunk, capability")
    op.alter_column("knowledge_chunk", "embedding", type_=Vector(NEW_DIMENSION))
    op.alter_column("capability", "embedding", type_=Vector(NEW_DIMENSION))


def downgrade() -> None:
    op.execute("TRUNCATE knowledge_chunk, capability")
    op.alter_column("knowledge_chunk", "embedding", type_=Vector(OLD_DIMENSION))
    op.alter_column("capability", "embedding", type_=Vector(OLD_DIMENSION))
