"""Add authentication role restrictions and token invalidation.

Revision ID: 20261007_0002
Revises: 20261007_0001
Create Date: 2026-10-07 21:00:00
"""

from alembic import op
import sqlalchemy as sa
from uuid import uuid4


revision = "20261007_0002"
down_revision = "20261007_0001"
branch_labels = None
depends_on = None


ROLE_NAMES = ("Admin", "Manager", "Sales Executive")


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String()))
    op.bulk_insert(roles, [{"id": uuid4(), "name": role_name} for role_name in ROLE_NAMES])


def downgrade() -> None:
    op.drop_column("users", "token_version")
