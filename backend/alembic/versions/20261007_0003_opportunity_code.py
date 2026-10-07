"""Add required business identifier for opportunities.

Revision ID: 20261007_0003
Revises: 20261007_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20261007_0003"
down_revision = "20261007_0002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("opportunities") as batch:
        batch.add_column(sa.Column("opportunity_code", sa.String(length=32), nullable=True))
    op.execute("UPDATE opportunities SET opportunity_code = 'OPP-' || upper(hex(randomblob(6))) WHERE opportunity_code IS NULL")
    with op.batch_alter_table("opportunities") as batch:
        batch.alter_column("opportunity_code", existing_type=sa.String(length=32), nullable=False)
        batch.create_unique_constraint("uq_opportunities_opportunity_code", ["opportunity_code"])

def downgrade() -> None:
    with op.batch_alter_table("opportunities") as batch:
        batch.drop_constraint("uq_opportunities_opportunity_code", type_="unique")
        batch.drop_column("opportunity_code")
