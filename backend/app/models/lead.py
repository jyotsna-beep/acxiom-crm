import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("status IN ('new', 'contacted', 'qualified', 'unqualified', 'converted', 'lost')", name="ck_leads_status"),
        CheckConstraint("expected_value >= 0", name="ck_leads_expected_value_nonnegative"),
        Index("ix_leads_status_owner", "status", "owner_id"),
    )

    lead_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    company_name: Mapped[str | None] = mapped_column(String(150))
    source: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False, index=True)
    priority: Mapped[str | None] = mapped_column(String(20))
    expected_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    converted_customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"))

    owner: Mapped["User | None"] = relationship(back_populates="owned_leads")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="lead")
    follow_ups: Mapped[list["FollowUp"]] = relationship(back_populates="lead")
    activities: Mapped[list["Activity"]] = relationship(back_populates="lead")
