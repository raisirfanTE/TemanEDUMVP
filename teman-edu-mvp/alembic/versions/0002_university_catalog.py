"""add university catalog tables

Revision ID: 0002_university_catalog
Revises: 0001_initial
Create Date: 2026-02-15 21:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_university_catalog"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("update_frequency", sa.String(length=40), nullable=False),
        sa.Column("fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_code"),
    )
    op.create_index("ix_external_data_sources_code", "external_data_sources", ["source_code"], unique=True)
    op.create_index("ix_external_data_sources_active", "external_data_sources", ["active"], unique=False)

    op.create_table(
        "university_programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_code", sa.String(length=120), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("university_name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("program_name", sa.String(length=255), nullable=False),
        sa.Column("program_level", sa.String(length=40), nullable=False),
        sa.Column("field_tags", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("intake_terms", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("application_deadline_text", sa.String(length=255), nullable=True),
        sa.Column("admission_requirements_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tuition_yearly_min_myr", sa.Integer(), nullable=True),
        sa.Column("tuition_yearly_max_myr", sa.Integer(), nullable=True),
        sa.Column("ielts_min", sa.Numeric(3, 1), nullable=True),
        sa.Column("toefl_min", sa.Integer(), nullable=True),
        sa.Column("qs_overall_rank", sa.Integer(), nullable=True),
        sa.Column("qs_subject_rank", sa.Integer(), nullable=True),
        sa.Column("mohe_listed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ptptn_eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_codes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("source_urls_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("application_url", sa.String(length=500), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("program_level in ('Foundation', 'Diploma', 'Bachelor', 'Top-up')", name="ck_university_programs_level"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_code"),
    )
    op.create_index("ix_university_programs_program_code", "university_programs", ["program_code"], unique=True)
    op.create_index("ix_university_programs_active", "university_programs", ["active"], unique=False)
    op.create_index("ix_university_programs_country", "university_programs", ["country"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_university_programs_country", table_name="university_programs")
    op.drop_index("ix_university_programs_active", table_name="university_programs")
    op.drop_index("ix_university_programs_program_code", table_name="university_programs")
    op.drop_table("university_programs")

    op.drop_index("ix_external_data_sources_active", table_name="external_data_sources")
    op.drop_index("ix_external_data_sources_code", table_name="external_data_sources")
    op.drop_table("external_data_sources")
