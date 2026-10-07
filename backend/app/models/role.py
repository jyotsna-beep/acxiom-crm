from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(
            "name IN ('Admin', 'Manager', 'Sales Executive')",
            name="ck_roles_allowed_names",
        ),
    )

    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="role")
