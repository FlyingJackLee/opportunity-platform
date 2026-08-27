"""collector_source, event_filter_rule, event hash/metadata columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-27 21:45:13.395364

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collector_source",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=True),
        sa.Column("list_url", sa.String(length=2048), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("schedule", sa.String(length=100), nullable=False),
        sa.Column("parser_type", sa.String(length=50), nullable=False),
        sa.Column("industry_tags", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("region_tags", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "event_filter_rule",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("rule_type", sa.String(length=30), nullable=False),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("event", sa.Column("url_hash", sa.String(length=64), nullable=True))
    op.add_column("event", sa.Column("title_hash", sa.String(length=64), nullable=True))
    op.add_column("event", sa.Column("metadata", sa.JSON(), nullable=True))
    op.add_column("event", sa.Column("collector_source_id", sa.UUID(), nullable=True))

    op.alter_column(
        "event",
        "published_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "event",
        "collected_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )

    op.create_index("ix_event_url_hash", "event", ["url_hash"])
    op.create_index("ix_event_title_hash", "event", ["title_hash"])
    op.create_foreign_key(
        "fk_event_collector_source_id",
        "event",
        "collector_source",
        ["collector_source_id"],
        ["id"],
    )

    # Defensive backstop against two sources' jobs racing on the same
    # republished article at the same instant -- the app-level find_duplicate
    # check (app/collector/dedup.py) is the primary/fast path. Supersedes the
    # plain non-unique ix_event_content_hash from migration 0001.
    op.drop_index("ix_event_content_hash", table_name="event")
    op.create_index(
        "ux_event_content_hash",
        "event",
        ["content_hash"],
        unique=True,
        postgresql_where=sa.text("content_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_event_content_hash", table_name="event")
    op.create_index("ix_event_content_hash", "event", ["content_hash"])
    op.drop_constraint("fk_event_collector_source_id", "event", type_="foreignkey")
    op.drop_index("ix_event_title_hash", table_name="event")
    op.drop_index("ix_event_url_hash", table_name="event")
    op.alter_column(
        "event",
        "collected_at",
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "event",
        "published_at",
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
    op.drop_column("event", "collector_source_id")
    op.drop_column("event", "metadata")
    op.drop_column("event", "title_hash")
    op.drop_column("event", "url_hash")
    op.drop_table("event_filter_rule")
    op.drop_table("collector_source")
