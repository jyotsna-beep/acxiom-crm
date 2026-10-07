import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="ck_customers_status"),
        Index("ix_customers_name_company", "name", "company_name"),
    )

    customer_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)

    owner: Mapped["User | None"] = relationship(back_populates="owned_customers")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="customer")
    follow_ups: Mapped[list["FollowUp"]] = relationship(back_populates="customer")
    activities: Mapped[list["Activity"]] = relationship(back_populates="customer")
