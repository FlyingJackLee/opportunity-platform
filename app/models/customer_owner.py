import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CustomerOwner(Base, TimestampMixin):
    """spec §59. Our own internal account manager responsible for an
    Organization/Department relationship -- NOT a contact inside the client
    org (see CONTEXT.md's Customer Owner entry). department_id=NULL means
    this row is the Organization-level fallback owner."""

    __tablename__ = "customer_owner"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "department_id", name="ux_customer_owner_scope"
        ),
        Index(
            "ux_customer_owner_org_only",
            "organization_id",
            unique=True,
            postgresql_where=text("department_id IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization.id"), index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("department.id")
    )
    owner_name: Mapped[str] = mapped_column(String(100))
    owner_user_id: Mapped[str | None] = mapped_column(String(100))
    dingtalk_user_id: Mapped[str | None] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
