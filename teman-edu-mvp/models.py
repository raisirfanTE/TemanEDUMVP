from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # student | counselor | admin
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user_orgs = relationship("UserOrganization", back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # school | partner
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user_orgs = relationship("UserOrganization", back_populates="organization")


class UserOrganization(Base):
    __tablename__ = "user_organizations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    role_in_org: Mapped[str] = mapped_column(String(50), nullable=False)  # counselor | admin

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "organization_id", name="pk_user_organizations"),
    )

    user = relationship("User", back_populates="user_orgs")
    organization = relationship("Organization", back_populates="user_orgs")


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    student_level: Mapped[str] = mapped_column(String(20), nullable=False)  # SPM | Diploma
    interest_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    destination_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    min_spm_credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    required_subjects_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    min_cgpa: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    budget_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    budget_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    english_min: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    constraints_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    pathway_title: Mapped[str] = mapped_column(String(255), nullable=False)
    pathway_summary: Mapped[str] = mapped_column(Text, nullable=False)
    cost_estimate_text: Mapped[str] = mapped_column(String(255), nullable=False)
    visa_note: Mapped[str] = mapped_column(Text, nullable=False)
    scholarship_likelihood: Mapped[str] = mapped_column(String(20), nullable=False)
    readiness_gaps: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    next_steps: Mapped[str] = mapped_column(Text, nullable=False)
    priority_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("student_level in ('SPM', 'Diploma')", name="ck_rules_student_level"),
        Index("ix_rules_rule_id", "rule_id"),
        Index("ix_rules_active", "active"),
        Index("ix_rules_student_level", "student_level"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # student | counselor
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SessionInput(Base):
    __tablename__ = "session_inputs"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), primary_key=True)
    inputs_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    results_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    details_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ContentSnippet(Base):
    __tablename__ = "content_snippets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (Index("ix_content_snippets_key_language", "key", "language", unique=True),)


class ExternalDataSource(Base):
    __tablename__ = "external_data_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    update_frequency: Mapped[str] = mapped_column(String(40), nullable=False)
    fields_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_external_data_sources_code", "source_code", unique=True),
        Index("ix_external_data_sources_active", "active"),
    )


class UniversityProgram(Base):
    __tablename__ = "university_programs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    university_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    program_level: Mapped[str] = mapped_column(String(40), nullable=False)  # Foundation | Diploma | Bachelor | Top-up
    field_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    intake_terms: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    application_deadline_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    admission_requirements_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tuition_yearly_min_myr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tuition_yearly_max_myr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ielts_min: Mapped[Optional[float]] = mapped_column(Numeric(3, 1), nullable=True)
    toefl_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qs_overall_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qs_subject_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mohe_listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ptptn_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_codes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    source_urls_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    application_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("program_level in ('Foundation', 'Diploma', 'Bachelor', 'Top-up')", name="ck_university_programs_level"),
        Index("ix_university_programs_program_code", "program_code", unique=True),
        Index("ix_university_programs_active", "active"),
        Index("ix_university_programs_country", "country"),
    )


class StudentApplication(Base):
    __tablename__ = "student_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    session_token: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    university_name: Mapped[str] = mapped_column(String(255), nullable=False)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    intake_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deadline_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qs_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tuition_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    application_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="saved")  # saved | in_progress | submitted | accepted | rejected
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status in ('saved', 'in_progress', 'submitted', 'accepted', 'rejected')",
            name="ck_student_applications_status",
        ),
        Index("ix_student_applications_user_id", "user_id"),
        Index("ix_student_applications_session_token", "session_token"),
        Index("ix_student_applications_status", "status"),
    )
