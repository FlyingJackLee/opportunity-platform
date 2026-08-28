"""customer_owner, push_record

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-28 07:59:19.568423

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_owner",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("owner_name", sa.String(length=100), nullable=False),
        sa.Column("owner_user_id", sa.String(length=100), nullable=True),
        sa.Column("dingtalk_user_id", sa.String(length=100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["department.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "department_id", name="ux_customer_owner_scope"
        ),
    )
    op.create_index(
        "ix_customer_owner_organization_id", "customer_owner", ["organization_id"]
    )
    op.create_index(
        "ux_customer_owner_org_only",
        "customer_owner",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("department_id IS NULL"),
    )

    op.create_table(
        "push_record",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("expert_run_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=True),
        sa.Column("recipient_type", sa.String(length=30), nullable=False),
        sa.Column("recipient_id", sa.String(length=100), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["event.id"]),
        sa.ForeignKeyConstraint(["expert_run_id"], ["expert_run.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["customer_owner.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_push_record_event_id", "push_record", ["event_id"])
    op.create_index("ix_push_record_expert_run_id", "push_record", ["expert_run_id"])


def downgrade() -> None:
    op.drop_index("ix_push_record_expert_run_id", table_name="push_record")
    op.drop_index("ix_push_record_event_id", table_name="push_record")
    op.drop_table("push_record")
    op.drop_index("ux_customer_owner_org_only", table_name="customer_owner")
    op.drop_index("ix_customer_owner_organization_id", table_name="customer_owner")
    op.drop_table("customer_owner")
