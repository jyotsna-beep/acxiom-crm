import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class FollowUp(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "follow_ups"
    __table_args__ = (
        CheckConstraint("((customer_id IS NOT NULL)::integer + (lead_id IS NOT NULL)::integer + (opportunity_id IS NOT NULL)::integer) = 1", name="ck_follow_ups_one_related_record"),
        CheckConstraint("status IN ('planned', 'completed', 'missed', 'cancelled')", name="ck_follow_ups_status"),
        Index("ix_follow_ups_date_status_assignee", "follow_up_date", "status", "assigned_user_id"),
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), index=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id"), index=True)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opportunities.id"), index=True)
    follow_up_date: Mapped[date] = mapped_column(Date, nullable=False)
    follow_up_type: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="planned", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    assigned_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer | None"] = relationship(back_populates="follow_ups")
    lead: Mapped["Lead | None"] = relationship(back_populates="follow_ups")
    opportunity: Mapped["Opportunity | None"] = relationship(back_populates="follow_ups")
    assigned_user: Mapped["User"] = relationship(back_populates="assigned_follow_ups")
