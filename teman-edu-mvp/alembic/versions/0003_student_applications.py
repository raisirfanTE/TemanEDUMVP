"""add student applications tracker

Revision ID: 0003_student_applications
Revises: 0002_university_catalog
Create Date: 2026-02-15 21:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_student_applications"
down_revision: Union[str, Sequence[str], None] = "0002_university_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_token", sa.String(length=80), nullable=True),
        sa.Column("university_name", sa.String(length=255), nullable=False),
        sa.Column("program_name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("intake_text", sa.String(length=255), nullable=True),
        sa.Column("deadline_text", sa.String(length=255), nullable=True),
        sa.Column("qs_rank", sa.Integer(), nullable=True),
        sa.Column("tuition_text", sa.String(length=255), nullable=True),
        sa.Column("application_url", sa.String(length=500), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="saved"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status in ('saved', 'in_progress', 'submitted', 'accepted', 'rejected')",
            name="ck_student_applications_status",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_applications_user_id", "student_applications", ["user_id"], unique=False)
    op.create_index("ix_student_applications_session_token", "student_applications", ["session_token"], unique=False)
    op.create_index("ix_student_applications_status", "student_applications", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_student_applications_status", table_name="student_applications")
    op.drop_index("ix_student_applications_session_token", table_name="student_applications")
    op.drop_index("ix_student_applications_user_id", table_name="student_applications")
    op.drop_table("student_applications")
