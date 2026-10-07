"""Create the initial AcxiomCRM schema.

Revision ID: 20261007_0001
Revises:
Create Date: 2026-10-07 20:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20261007_0001"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table("roles", sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(32), nullable=False, unique=True), *_timestamps())
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True), sa.Column("username", sa.String(100), unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role_id", uuid, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("manager_id", uuid, sa.ForeignKey("users.id")), sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("failed_login_count", sa.Integer(), nullable=False), sa.Column("lockout_until", sa.DateTime(timezone=True)), *_timestamps(),
    )
    for name, columns in (("ix_users_role_id", ["role_id"]), ("ix_users_manager_id", ["manager_id"])):
        op.create_index(name, "users", columns)

    op.create_table(
        "customers",
        sa.Column("id", uuid, primary_key=True), sa.Column("customer_code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False), sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("phone", sa.String(32), nullable=False, unique=True), sa.Column("company_name", sa.String(150)), sa.Column("address", sa.Text()),
        sa.Column("city", sa.String(100)), sa.Column("state", sa.String(100)), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text()), sa.Column("owner_id", uuid, sa.ForeignKey("users.id")), *_timestamps(),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_customers_status"),
    )
    for name, columns in (("ix_customers_status", ["status"]), ("ix_customers_owner_id", ["owner_id"]), ("ix_customers_name_company", ["name", "company_name"])):
        op.create_index(name, "customers", columns)

    op.create_table(
        "leads",
        sa.Column("id", uuid, primary_key=True), sa.Column("lead_code", sa.String(32), nullable=False, unique=True), sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(254)), sa.Column("phone", sa.String(32)), sa.Column("company_name", sa.String(150)), sa.Column("source", sa.String(100)),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("priority", sa.String(20)), sa.Column("expected_value", sa.Numeric(14, 2)),
        sa.Column("notes", sa.Text()), sa.Column("owner_id", uuid, sa.ForeignKey("users.id")), sa.Column("converted_customer_id", uuid, sa.ForeignKey("customers.id")), *_timestamps(),
        sa.CheckConstraint("status IN ('new', 'contacted', 'qualified', 'unqualified', 'converted', 'lost')", name="ck_leads_status"),
        sa.CheckConstraint("expected_value >= 0", name="ck_leads_expected_value_nonnegative"),
    )
    for name, columns in (("ix_leads_email", ["email"]), ("ix_leads_phone", ["phone"]), ("ix_leads_status", ["status"]), ("ix_leads_owner_id", ["owner_id"]), ("ix_leads_status_owner", ["status", "owner_id"])):
        op.create_index(name, "leads", columns)

    op.create_table(
        "opportunities",
        sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(150), nullable=False), sa.Column("customer_id", uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("lead_id", uuid, sa.ForeignKey("leads.id")), sa.Column("amount", sa.Numeric(14, 2), nullable=False), sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("probability", sa.Numeric(5, 2), nullable=False), sa.Column("expected_close_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(100)), sa.Column("notes", sa.Text()), sa.Column("owner_id", uuid, sa.ForeignKey("users.id")), *_timestamps(),
        sa.CheckConstraint("amount >= 0", name="ck_opportunities_amount_nonnegative"), sa.CheckConstraint("probability >= 0 AND probability <= 100", name="ck_opportunities_probability"),
        sa.CheckConstraint("stage IN ('qualification', 'proposal', 'negotiation', 'won', 'lost')", name="ck_opportunities_stage"),
    )
    for name, columns in (("ix_opportunities_customer_id", ["customer_id"]), ("ix_opportunities_lead_id", ["lead_id"]), ("ix_opportunities_owner_id", ["owner_id"]), ("ix_opportunities_stage", ["stage"]), ("ix_opportunities_status", ["status"]), ("ix_opportunities_expected_close_date", ["expected_close_date"]), ("ix_opportunities_stage_owner", ["stage", "owner_id"])):
        op.create_index(name, "opportunities", columns)

    op.create_table(
        "follow_ups",
        sa.Column("id", uuid, primary_key=True), sa.Column("customer_id", uuid, sa.ForeignKey("customers.id")), sa.Column("lead_id", uuid, sa.ForeignKey("leads.id")),
        sa.Column("opportunity_id", uuid, sa.ForeignKey("opportunities.id")), sa.Column("follow_up_date", sa.Date(), nullable=False), sa.Column("follow_up_type", sa.String(30), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("notes", sa.Text()),
        sa.Column("assigned_user_id", uuid, sa.ForeignKey("users.id"), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), *_timestamps(),
        sa.CheckConstraint("((customer_id IS NOT NULL)::integer + (lead_id IS NOT NULL)::integer + (opportunity_id IS NOT NULL)::integer) = 1", name="ck_follow_ups_one_related_record"),
        sa.CheckConstraint("status IN ('planned', 'completed', 'missed', 'cancelled')", name="ck_follow_ups_status"),
    )
    for name, columns in (("ix_follow_ups_customer_id", ["customer_id"]), ("ix_follow_ups_lead_id", ["lead_id"]), ("ix_follow_ups_opportunity_id", ["opportunity_id"]), ("ix_follow_ups_assigned_user_id", ["assigned_user_id"]), ("ix_follow_ups_status", ["status"]), ("ix_follow_ups_date_status_assignee", ["follow_up_date", "status", "assigned_user_id"])):
        op.create_index(name, "follow_ups", columns)

    op.create_table(
        "activities",
        sa.Column("id", uuid, primary_key=True), sa.Column("activity_type", sa.String(20), nullable=False), sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("activity_date", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("customer_id", uuid, sa.ForeignKey("customers.id")), sa.Column("lead_id", uuid, sa.ForeignKey("leads.id")), sa.Column("opportunity_id", uuid, sa.ForeignKey("opportunities.id")),
        sa.Column("assigned_user_id", uuid, sa.ForeignKey("users.id"), nullable=False), *_timestamps(),
        sa.CheckConstraint("activity_type IN ('call', 'meeting', 'email', 'task')", name="ck_activities_type"),
    )
    for name, columns in (("ix_activities_activity_type", ["activity_type"]), ("ix_activities_activity_date", ["activity_date"]), ("ix_activities_status", ["status"]), ("ix_activities_customer_id", ["customer_id"]), ("ix_activities_lead_id", ["lead_id"]), ("ix_activities_opportunity_id", ["opportunity_id"]), ("ix_activities_assigned_user_id", ["assigned_user_id"]), ("ix_activities_date_status_assignee", ["activity_date", "status", "assigned_user_id"])):
        op.create_index(name, "activities", columns)

    op.create_table(
        "audit_logs",
        sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id")), sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_name", sa.String(100), nullable=False), sa.Column("record_id", sa.String(36)), sa.Column("result", sa.String(30), nullable=False),
        sa.Column("old_value", sa.JSON()), sa.Column("new_value", sa.JSON()), sa.Column("details", sa.Text()), sa.Column("ip_address", sa.String(45)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    for name, columns in (("ix_audit_logs_user_id", ["user_id"]), ("ix_audit_logs_action", ["action"]), ("ix_audit_logs_entity_name", ["entity_name"]), ("ix_audit_logs_record_id", ["record_id"]), ("ix_audit_logs_created_at", ["created_at"]), ("ix_audit_logs_entity_record", ["entity_name", "record_id"]), ("ix_audit_logs_user_created", ["user_id", "created_at"])):
        op.create_index(name, "audit_logs", columns)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("activities")
    op.drop_table("follow_ups")
    op.drop_table("opportunities")
    op.drop_table("leads")
    op.drop_table("customers")
    op.drop_table("users")
    op.drop_table("roles")
