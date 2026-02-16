"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_organizations",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_in_org", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "organization_id", name="pk_user_organizations"),
    )

    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("student_level", sa.String(length=20), nullable=False),
        sa.Column("interest_tags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("destination_tags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("min_spm_credits", sa.Integer(), nullable=True),
        sa.Column("required_subjects_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("min_cgpa", sa.Numeric(3, 2), nullable=True),
        sa.Column("budget_min", sa.Integer(), nullable=True),
        sa.Column("budget_max", sa.Integer(), nullable=True),
        sa.Column("english_min", sa.String(length=30), nullable=True),
        sa.Column("constraints_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pathway_title", sa.String(length=255), nullable=False),
        sa.Column("pathway_summary", sa.Text(), nullable=False),
        sa.Column("cost_estimate_text", sa.String(length=255), nullable=False),
        sa.Column("visa_note", sa.Text(), nullable=False),
        sa.Column("scholarship_likelihood", sa.String(length=20), nullable=False),
        sa.Column("readiness_gaps", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("next_steps", sa.Text(), nullable=False),
        sa.Column("priority_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("student_level in ('SPM', 'Diploma')", name="ck_rules_student_level"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id"),
    )
    op.create_index("ix_rules_rule_id", "rules", ["rule_id"], unique=False)
    op.create_index("ix_rules_active", "rules", ["active"], unique=False)
    op.create_index("ix_rules_student_level", "rules", ["student_level"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "session_inputs",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inputs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("results_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "content_snippets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_content_snippets"),
    )
    op.create_index("ix_content_snippets_key_language", "content_snippets", ["key", "language"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_content_snippets_key_language", table_name="content_snippets")
    op.drop_table("content_snippets")
    op.drop_table("audit_logs")
    op.drop_table("recommendations")
    op.drop_table("session_inputs")
    op.drop_table("sessions")
    op.drop_index("ix_rules_student_level", table_name="rules")
    op.drop_index("ix_rules_active", table_name="rules")
    op.drop_index("ix_rules_rule_id", table_name="rules")
    op.drop_table("rules")
    op.drop_table("user_organizations")
    op.drop_table("organizations")
    op.drop_table("users")
