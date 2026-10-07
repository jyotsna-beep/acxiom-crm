import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_count: Mapped[int] = mapped_column(default=0, nullable=False)
    lockout_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_version: Mapped[int] = mapped_column(default=0, nullable=False)

    role: Mapped["Role"] = relationship(back_populates="users")
    manager: Mapped["User | None"] = relationship(remote_side="User.id", back_populates="reports")
    reports: Mapped[list["User"]] = relationship(back_populates="manager")
    owned_customers: Mapped[list["Customer"]] = relationship(back_populates="owner")
    owned_leads: Mapped[list["Lead"]] = relationship(back_populates="owner")
    owned_opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="owner")
    assigned_follow_ups: Mapped[list["FollowUp"]] = relationship(back_populates="assigned_user")
    assigned_activities: Mapped[list["Activity"]] = relationship(back_populates="assigned_user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
