import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Activity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("activity_type IN ('call', 'meeting', 'email', 'task')", name="ck_activities_type"),
        Index("ix_activities_date_status_assignee", "activity_date", "status", "assigned_user_id"),
    )

    activity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    activity_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), index=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id"), index=True)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opportunities.id"), index=True)
    assigned_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    customer: Mapped["Customer | None"] = relationship(back_populates="activities")
    lead: Mapped["Lead | None"] = relationship(back_populates="activities")
    opportunity: Mapped["Opportunity | None"] = relationship(back_populates="activities")
    assigned_user: Mapped["User"] = relationship(back_populates="assigned_activities")
