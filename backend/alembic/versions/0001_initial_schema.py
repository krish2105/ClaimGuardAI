"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("provider_id", sa.String(10), primary_key=True),
        sa.Column("specialty", sa.String(100)),
        sa.Column("claim_volume_30d_avg", sa.Integer),
        sa.Column("flagged_history_count", sa.Integer, server_default="0"),
    )

    op.create_table(
        "claims",
        sa.Column("claim_id", sa.String(15), primary_key=True),
        sa.Column("patient_id", sa.String(10), nullable=False),
        sa.Column("provider_id", sa.String(10), sa.ForeignKey("providers.provider_id")),
        sa.Column("icd10_codes", ARRAY(sa.String)),
        sa.Column("cpt_codes", ARRAY(sa.String)),
        sa.Column("billed_amount", sa.Numeric(10, 2)),
        sa.Column("approved_amount", sa.Numeric(10, 2)),
        sa.Column("treatment_date", sa.Date),
        sa.Column("plan_type", sa.String(20)),
        sa.Column("prior_auth_required", sa.Boolean),
        sa.Column("prior_auth_obtained", sa.Boolean),
        sa.Column("fraud_label", sa.Boolean),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "decisions",
        sa.Column("decision_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.String(15), sa.ForeignKey("claims.claim_id")),
        sa.Column("coding_flags", ARRAY(sa.String)),
        sa.Column("fraud_score", sa.Numeric(5, 2)),
        sa.Column("fraud_top_features", JSONB),
        sa.Column("retrieved_clauses", JSONB),
        sa.Column("decision_recommendation", sa.String(20)),
        sa.Column("decision_rationale", sa.Text),
        sa.Column("final_decision", sa.String(20)),
        sa.Column("escalation_reason", sa.Text),
        sa.Column("agent_trace", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "escalations",
        sa.Column("escalation_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.String(15), sa.ForeignKey("claims.claim_id")),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("adjuster_decision", sa.String(20)),
        sa.Column("adjuster_notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_log",
        sa.Column("log_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.String(15)),
        sa.Column("event_type", sa.String(50)),
        sa.Column("event_payload", JSONB),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("escalations")
    op.drop_table("decisions")
    op.drop_table("claims")
    op.drop_table("providers")
