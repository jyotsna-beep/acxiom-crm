import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Opportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_opportunities_amount_nonnegative"),
        CheckConstraint("probability >= 0 AND probability <= 100", name="ck_opportunities_probability"),
        CheckConstraint("stage IN ('qualification', 'proposal', 'negotiation', 'won', 'lost')", name="ck_opportunities_stage"),
        Index("ix_opportunities_stage_owner", "stage", "owner_id"),
        Index("ix_opportunities_expected_close_date", "expected_close_date"),
    )

    opportunity_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), default="qualification", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    probability: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    expected_close_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)

    customer: Mapped["Customer"] = relationship(back_populates="opportunities")
    lead: Mapped["Lead | None"] = relationship(back_populates="opportunities")
    owner: Mapped["User | None"] = relationship(back_populates="owned_opportunities")
    follow_ups: Mapped[list["FollowUp"]] = relationship(back_populates="opportunity")
    activities: Mapped[list["Activity"]] = relationship(back_populates="opportunity")
