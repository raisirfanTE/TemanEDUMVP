from __future__ import annotations

import base64
import json
import uuid
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from auth import authenticate_user
from db import db_session, init_schema
from export import build_json_summary, build_pdf_report
from logic import evaluate_rules
from models import (
    AuditLog,
    ContentSnippet,
    ExternalDataSource,
    Organization,
    Recommendation,
    Rule,
    Session as SessionModel,
    SessionInput,
    StudentApplication,
    UniversityProgram,
    User,
    UserOrganization,
)
from seed import (
    load_rules_from_csv,
    preview_diff,
    seed_content_snippets,
    seed_default_users_and_org,
    seed_external_data_sources,
    seed_rules_if_empty,
    seed_university_programs,
    upsert_rules,
)
from ui import (
    inject_interaction_js,
    inject_mobile_css,
    render_disclaimers,
    render_meter,
    t,
)


st.set_page_config(page_title="TemanEDU MVP", layout="wide")
inject_mobile_css()

STUDENT_PAGES = {
    "student-chat",
    "student-pathway",
    "results",
    "course-finder",
    "application-tracker",
    "about",
}

PROGRAM_TAG_MAP: dict[str, list[str]] = {
    "Digital Marketing & E-commerce": ["Business", "Digital Marketing", "Creative"],
    "Data Science & Analytics": ["IT", "Data", "Engineering"],
    "Artificial Intelligence & Machine Learning": ["IT", "Data", "Engineering"],
    "Biomedical Engineering": ["Engineering", "Health", "Science"],
    "Financial Technology (FinTech)": ["Business", "IT", "Data"],
    "Hospitality & Tourism Management": ["Business", "Hospitality"],
    "Graphic Design & Multimedia": ["Creative", "Design", "Digital Marketing"],
    "Nursing & Allied Health": ["Health", "Science"],
    "Cybersecurity & Information Security": ["IT", "Engineering"],
    "Supply Chain & Logistics Management": ["Business", "Logistics"],
    "Renewable Energy Engineering": ["Engineering", "Science"],
    "Psychology & Counselling": ["Health", "Psychology"],
    "International Business": ["Business", "Economics"],
    "Software Engineering": ["IT", "Engineering"],
    "Architecture & Urban Planning": ["Engineering", "Design", "Creative"],
}

SPECIFIC_PROGRAM_OPTIONS = list(PROGRAM_TAG_MAP.keys())
COUNTRY_OPTIONS = ["Malaysia", "Australia", "UK", "Singapore", "New Zealand", "Ireland", "Canada"]
PREFERRED_UNI_OPTIONS = [
    "Universiti Malaya",
    "UCSI University",
    "Taylor's University",
    "Monash University Malaysia",
    "RMIT University",
    "University of Leeds",
    "James Cook University Singapore",
    "Not sure yet",
]
SUBJECT_GRADE_OPTIONS = ["A+", "A", "A-", "B+", "B", "C+", "C", "D", "E", "G", "Not sure yet"]
DOC_CHECKLIST_OPTIONS = [
    "NRIC/Passport copy",
    "Latest transcript/result slip",
    "English test result (if any)",
    "CV/Resume draft",
    "Personal statement draft",
    "Portfolio/sample work",
    "Income/supporting docs",
    "2 shortlisted universities",
    "None yet",
]


def bootstrap() -> None:
    init_schema()
    with db_session() as db:
        seed_default_users_and_org(db)
        seed_content_snippets(db)
        seed_external_data_sources(db)
        seed_rules_if_empty(db)
        seed_university_programs(db)


@st.cache_data(ttl=30)
def get_content_snippets(language: str) -> dict[str, str]:
    with db_session() as db:
        snippets = db.scalars(select(ContentSnippet).where(ContentSnippet.language == language)).all()
        return {item.key: item.value for item in snippets}


def get_current_user() -> dict[str, Any] | None:
    auth_payload = st.session_state.get("auth_user")
    if not auth_payload:
        return None

    with db_session() as db:
        user = db.get(User, uuid.UUID(auth_payload["id"]))
        if not user:
            st.session_state.pop("auth_user", None)
            st.session_state.pop("auth_session_id", None)
            return None
        return {"id": str(user.id), "role": user.role, "email": user.email}


def _query_get(key: str, default: str | None = None) -> str | None:
    value = st.query_params.get(key, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value


def _query_set(**kwargs: str | None) -> None:
    for key, value in kwargs.items():
        current = _query_get(key)
        if value is None:
            if current is not None:
                if key in st.query_params:
                    del st.query_params[key]
        else:
            if current != value:
                st.query_params[key] = value


def _clear_auth_state() -> None:
    st.session_state.pop("auth_user", None)
    st.session_state.pop("auth_session_id", None)
    _query_set(auth_user_id=None, auth_role=None, auth_session_id=None)


def restore_auth_from_query() -> None:
    if st.session_state.get("auth_user"):
        if not st.session_state.get("auth_session_id"):
            st.session_state["auth_session_id"] = _query_get("auth_session_id") or str(uuid.uuid4())
        return

    auth_user_id = _query_get("auth_user_id")
    auth_role = _query_get("auth_role")
    auth_session_id = _query_get("auth_session_id")

    if not auth_user_id or auth_role not in {"counselor", "admin", "student"}:
        return

    try:
        user_uuid = uuid.UUID(auth_user_id)
    except (ValueError, TypeError):
        _clear_auth_state()
        return

    with db_session() as db:
        user = db.get(User, user_uuid)
        if not user or user.role != auth_role:
            _clear_auth_state()
            return

    st.session_state["auth_user"] = {"id": str(user.id), "role": user.role, "email": user.email}
    st.session_state["auth_session_id"] = auth_session_id or str(uuid.uuid4())
    _query_set(auth_session_id=st.session_state["auth_session_id"])


def restore_navigation_state() -> None:
    query_language = _query_get("language")
    query_access = _query_get("access")
    query_student_page = _query_get("student_page")
    query_chat_question = _query_get("chat_q")

    if query_language in {"en", "bm"}:
        st.session_state["language"] = query_language
    if query_access in {"Student", "Counselor", "Admin"}:
        st.session_state["access_mode"] = query_access
    if query_student_page == "student-pathway":
        query_student_page = "student-chat"
    if query_student_page in STUDENT_PAGES:
        st.session_state["student_page"] = query_student_page
    if query_chat_question:
        st.session_state["student_chat_edit_question"] = query_chat_question


def render_login(required_role: str, inline: bool = False) -> dict[str, Any] | None:
    host = st if inline else st.sidebar
    user = get_current_user()
    if user and user["role"] == required_role:
        host.success(f"Logged in as {user['email']} ({user['role']})")
        session_id = st.session_state.get("auth_session_id")
        if session_id:
            host.caption(f"Session ID: `{session_id}`")
        if host.button("Logout", key=f"logout_{required_role}_{'inline' if inline else 'sidebar'}"):
            _clear_auth_state()
            st.rerun()
        return user

    host.subheader(f"{required_role.title()} Login")
    with host.form(f"login_{required_role}_{'inline' if inline else 'sidebar'}"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        login_submitted = st.form_submit_button("Login")

    if login_submitted:
        with db_session() as db:
            found = authenticate_user(db, email, password)
            if not found or found.role != required_role:
                host.error("Invalid credentials or role")
            else:
                st.session_state["auth_user"] = {
                    "id": str(found.id),
                    "role": found.role,
                    "email": found.email,
                }
                st.session_state["auth_session_id"] = str(uuid.uuid4())
                _query_set(
                    auth_user_id=str(found.id),
                    auth_role=found.role,
                    auth_session_id=st.session_state["auth_session_id"],
                )
                st.rerun()
    return None


def get_user_organizations(user_id: str) -> list[dict[str, str]]:
    with db_session() as db:
        links = db.scalars(
            select(UserOrganization).where(UserOrganization.user_id == uuid.UUID(user_id))
        ).all()
        orgs = []
        for link in links:
            org = db.get(Organization, link.organization_id)
            if org:
                orgs.append({"id": str(org.id), "name": org.name, "role_in_org": link.role_in_org})
        return orgs


def fetch_rules(level: str) -> list[Rule]:
    with db_session() as db:
        return db.scalars(
            select(Rule)
            .where(Rule.active.is_(True), Rule.student_level == level)
            .order_by(Rule.priority_weight.desc())
        ).all()


def fetch_university_programs() -> list[UniversityProgram]:
    with db_session() as db:
        return db.scalars(
            select(UniversityProgram)
            .where(UniversityProgram.active.is_(True))
            .order_by(UniversityProgram.updated_at.desc())
        ).all()


def get_student_session_token() -> str:
    token = st.session_state.get("student_session_token")
    if not token:
        token = str(uuid.uuid4())
        st.session_state["student_session_token"] = token
    return token


def save_application_to_tracker(
    option: dict[str, Any],
    current_user: dict[str, Any] | None,
    source: str = "recommendation",
) -> str:
    with db_session() as db:
        user_id = uuid.UUID(current_user["id"]) if current_user else None
        app = StudentApplication(
            user_id=user_id,
            session_token=get_student_session_token(),
            university_name=option.get("university_name", "Unknown University"),
            program_name=option.get("program_name", "Unknown Program"),
            country=option.get("country", "Unknown"),
            intake_text=", ".join(option.get("intake_terms", [])) if isinstance(option.get("intake_terms"), list) else option.get("intake_terms"),
            deadline_text=option.get("application_deadline_text"),
            qs_rank=option.get("qs_overall_rank"),
            tuition_text=option.get("tuition_yearly_text"),
            application_url=option.get("application_url"),
            contact_email=option.get("contact_email"),
            status="saved",
            notes=f"Saved from {source}",
        )
        db.add(app)
        db.flush()
        db.add(
            AuditLog(
                user_id=user_id,
                action="application_saved",
                details_json={
                    "application_id": str(app.id),
                    "university_name": app.university_name,
                    "program_name": app.program_name,
                    "source": source,
                },
            )
        )
        return str(app.id)


def fetch_tracked_applications(current_user: dict[str, Any] | None) -> list[StudentApplication]:
    with db_session() as db:
        if current_user:
            user_uuid = uuid.UUID(current_user["id"])
            return db.scalars(
                select(StudentApplication)
                .where(StudentApplication.user_id == user_uuid)
                .order_by(StudentApplication.updated_at.desc())
            ).all()
        token = get_student_session_token()
        return db.scalars(
            select(StudentApplication)
            .where(StudentApplication.session_token == token)
            .order_by(StudentApplication.updated_at.desc())
        ).all()


def update_application_status(
    application_id: str,
    new_status: str,
    current_user: dict[str, Any] | None,
    notes: str | None = None,
) -> None:
    with db_session() as db:
        app = db.get(StudentApplication, uuid.UUID(application_id))
        if not app:
            return
        app.status = new_status
        if notes is not None:
            app.notes = notes
        db.add(
            AuditLog(
                user_id=uuid.UUID(current_user["id"]) if current_user else None,
                action="application_status_updated",
                details_json={"application_id": application_id, "status": new_status},
            )
        )


def log_action(user_id: str | None, action: str, details: dict[str, Any]) -> None:
    with db_session() as db:
        db.add(AuditLog(user_id=uuid.UUID(user_id) if user_id else None, action=action, details_json=details))


def persist_session(
    inputs: dict[str, Any],
    results: dict[str, Any],
    mode: str,
    language: str,
    user_id: str | None = None,
    organization_id: str | None = None,
) -> str:
    with db_session() as db:
        session_model = SessionModel(
            user_id=uuid.UUID(user_id) if user_id else None,
            organization_id=uuid.UUID(organization_id) if organization_id else None,
            mode=mode,
            language=language,
        )
        db.add(session_model)
        db.flush()

        db.add(SessionInput(session_id=session_model.id, inputs_json=inputs))
        db.add(Recommendation(session_id=session_model.id, results_json=results))
        db.add(
            AuditLog(
                user_id=uuid.UUID(user_id) if user_id else None,
                action="results_saved",
                details_json={"session_id": str(session_model.id), "mode": mode},
            )
        )
        return str(session_model.id)


def get_or_create_student_user(optional_email: str | None) -> str:
    with db_session() as db:
        if optional_email:
            existing = db.scalar(select(User).where(User.email == optional_email))
            if existing:
                return str(existing.id)
        user = User(role="student", email=optional_email if optional_email else None, password_hash=None)
        db.add(user)
        db.flush()
        return str(user.id)


def _wizard_state_key(prefix: str, field: str) -> str:
    return f"{prefix}_{field}"


def reset_wizard(prefix: str) -> None:
    for key in list(st.session_state.keys()):
        if key.startswith(prefix + "_"):
            st.session_state.pop(key, None)


def collect_inputs(prefix: str) -> dict[str, Any]:
    level_choice = st.session_state.get(_wizard_state_key(prefix, "student_level"), "SPM")
    level = "SPM" if level_choice == "I'm not sure" else level_choice

    subjects = {}
    if level == "SPM":
        for subject in ["bm", "english", "math", "add_math", "science"]:
            subjects[subject] = st.session_state.get(_wizard_state_key(prefix, f"subject_{subject}"), "C")

    destination_choice = st.session_state.get(_wizard_state_key(prefix, "destination_choice"), "Malaysia only")
    destination_preference = {
        "Malaysia only": "malaysia_only",
        "Open to overseas": "open_overseas",
        "I'm not sure": "malaysia_only",
    }.get(destination_choice, "malaysia_only")

    english_choice = st.session_state.get(_wizard_state_key(prefix, "english_self"), "Intermediate")
    if english_choice == "I'm not sure":
        english_choice = "Intermediate"
    english_test_raw = str(st.session_state.get(_wizard_state_key(prefix, "english_test_score"), "")).strip()
    english_test_score = int(english_test_raw) if english_test_raw.isdigit() else None
    if english_test_score is not None and not (0 <= english_test_score <= 100):
        english_test_score = None
    ielts_raw = str(st.session_state.get(_wizard_state_key(prefix, "ielts_score"), "")).strip()
    ielts_score = None
    try:
        if ielts_raw:
            ielts_score = float(ielts_raw)
    except ValueError:
        ielts_score = None
    if ielts_score is not None and not (0.0 <= ielts_score <= 9.0):
        ielts_score = None

    toefl_raw = str(st.session_state.get(_wizard_state_key(prefix, "toefl_score"), "")).strip()
    toefl_score = int(toefl_raw) if toefl_raw.isdigit() else None
    if toefl_score is not None and not (0 <= toefl_score <= 120):
        toefl_score = None

    interests = st.session_state.get(_wizard_state_key(prefix, "interest_tags"), [])
    if not interests:
        interests = ["Business", "IT"]

    destinations = st.session_state.get(_wizard_state_key(prefix, "destination_tags"), ["Malaysia"])
    if destinations and set(destinations) == {"Malaysia"}:
        destination_choice = "Malaysia only"
    elif destinations:
        destination_choice = "Open to overseas"
    destination_preference = "malaysia_only" if destination_choice == "Malaysia only" else "open_overseas"
    specific_program_interest = st.session_state.get(_wizard_state_key(prefix, "specific_program_interest"), "General")
    if not specific_program_interest:
        specific_program_interest = "General"
    intake_window = st.session_state.get(_wizard_state_key(prefix, "intake_window"), "next_6_12_months")
    preferred_universities = st.session_state.get(_wizard_state_key(prefix, "preferred_universities"), [])
    target_ranking_tier = st.session_state.get(_wizard_state_key(prefix, "target_ranking_tier"), "Any")
    target_intake_month = st.session_state.get(_wizard_state_key(prefix, "target_intake_month"), "")
    target_intake_year = st.session_state.get(_wizard_state_key(prefix, "target_intake_year"), "")
    support_constraints = st.session_state.get(_wizard_state_key(prefix, "support_constraints"), [])
    priority_factors = st.session_state.get(_wizard_state_key(prefix, "priority_factors"), [])
    institution_type_pref = st.session_state.get(_wizard_state_key(prefix, "institution_type_pref"), "Both")
    english_test_plan = st.session_state.get(_wizard_state_key(prefix, "english_test_plan"), "Already have score")

    return {
        "student_level": level,
        "spm_credits": st.session_state.get(_wizard_state_key(prefix, "spm_credits"), 5),
        "subjects": subjects,
        "cgpa": st.session_state.get(_wizard_state_key(prefix, "cgpa"), 2.8),
        "diploma_field": st.session_state.get(_wizard_state_key(prefix, "diploma_field"), "General"),
        "interest_tags": interests,
        "budget_range": st.session_state.get(_wizard_state_key(prefix, "budget_range"), "RM 800-2000"),
        "budget_monthly": st.session_state.get(_wizard_state_key(prefix, "budget_monthly"), 1200),
        "financing_mode": st.session_state.get(_wizard_state_key(prefix, "financing_mode"), "self_fund"),
        "need_work_part_time": st.session_state.get(_wizard_state_key(prefix, "need_work_part_time"), False),
        "english_self": english_choice,
        "english_test_score": english_test_score,
        "ielts_score": ielts_score,
        "toefl_score": toefl_score,
        "specific_program_interest": specific_program_interest,
        "preferred_universities": preferred_universities,
        "target_ranking_tier": target_ranking_tier,
        "destination_preference": destination_preference,
        "destination_tags": destinations,
        "intake_window": intake_window,
        "target_intake_month": target_intake_month,
        "target_intake_year": int(target_intake_year) if str(target_intake_year).isdigit() else target_intake_year,
        "english_test_plan": english_test_plan,
        "support_constraints": support_constraints,
        "priority_factors": priority_factors,
        "institution_type_pref": institution_type_pref,
        "scholarship_needed": st.session_state.get(_wizard_state_key(prefix, "scholarship_needed"), False),
        "timeline_urgency": st.session_state.get(_wizard_state_key(prefix, "timeline_urgency"), "normal"),
        "family_constraints": st.session_state.get(_wizard_state_key(prefix, "family_constraints"), "none"),
        "willing_relocate": st.session_state.get(_wizard_state_key(prefix, "willing_relocate"), True),
        "preparedness_checklist": st.session_state.get(_wizard_state_key(prefix, "preparedness_checklist"), []),
        "consent_to_save": st.session_state.get(_wizard_state_key(prefix, "consent_to_save"), False),
        "optional_email": st.session_state.get(_wizard_state_key(prefix, "optional_email"), "").strip() or None,
    }


def _render_profile_snapshot(prefix: str) -> None:
    chips: list[str] = []
    level = st.session_state.get(_wizard_state_key(prefix, "student_level"))
    if level:
        chips.append(f"Level: {level}")

    interests = st.session_state.get(_wizard_state_key(prefix, "interest_tags"), [])
    if interests:
        chips.append("Interests: " + ", ".join(interests[:2]))

    budget = st.session_state.get(_wizard_state_key(prefix, "budget_monthly"))
    if budget:
        chips.append(f"Budget: RM {budget}")

    english = st.session_state.get(_wizard_state_key(prefix, "english_self"))
    if english:
        chips.append(f"English: {english}")
    specific = st.session_state.get(_wizard_state_key(prefix, "specific_program_interest"))
    if specific:
        chips.append(f"Program: {specific}")
    intake_window = st.session_state.get(_wizard_state_key(prefix, "intake_window"))
    if intake_window:
        chips.append(f"Timeline: {intake_window}")

    if chips:
        chips_html = "".join([f"<span class='teman-chip'>{escape(item)}</span>" for item in chips])
        st.markdown(
            f"""
            <div class="teman-summary">
                <div class="teman-muted"><strong>Your profile so far</strong></div>
                <div style="margin-top: 0.35rem;">{chips_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _completion_percent(prefix: str) -> int:
    level = st.session_state.get(_wizard_state_key(prefix, "student_level"))
    academic_done = bool(
        st.session_state.get(_wizard_state_key(prefix, "spm_credits"))
        if level in ["SPM", "I'm not sure", None]
        else st.session_state.get(_wizard_state_key(prefix, "cgpa"))
    )
    checks = [
        bool(st.session_state.get(_wizard_state_key(prefix, "specific_program_interest"))),
        bool(level),
        academic_done,
        bool(st.session_state.get(_wizard_state_key(prefix, "destination_tags"))),
        bool(st.session_state.get(_wizard_state_key(prefix, "budget_monthly")) and st.session_state.get(_wizard_state_key(prefix, "financing_mode"))),
        bool(st.session_state.get(_wizard_state_key(prefix, "english_self"))),
        bool(st.session_state.get(_wizard_state_key(prefix, "target_intake_month"))),
        bool(st.session_state.get(_wizard_state_key(prefix, "support_constraints"))),
        bool(st.session_state.get(_wizard_state_key(prefix, "priority_factors"))),
        bool(st.session_state.get(_wizard_state_key(prefix, "preparedness_level"))),
    ]
    return int(round((sum(checks) / len(checks)) * 100))


def _privacy_reassurance(why: str) -> None:
    st.markdown(f"<div class='teman-privacy'>🔒 Why we ask: {escape(why)}</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='teman-privacy'>🔐 Your answer stays private unless you choose to save.</div>",
        unsafe_allow_html=True,
    )


def _choice_triplet(
    prefix: str,
    field: str,
    options: list[tuple[str, Any, str]],
) -> Any:
    state_key = _wizard_state_key(prefix, field)
    current_value = st.session_state.get(state_key)
    cols = st.columns(len(options))
    for idx, (label, value, tip) in enumerate(options):
        display_label = f"✓ {label}" if current_value == value else label
        with cols[idx]:
            if st.button(
                display_label,
                key=_wizard_state_key(prefix, f"{field}_opt_{idx}"),
                use_container_width=True,
                help=tip,
                type="primary" if current_value == value else "secondary",
            ):
                st.session_state[state_key] = value
                st.rerun()
    return st.session_state.get(state_key)


def _multi_select_bubbles(
    prefix: str,
    field: str,
    options: list[tuple[str, str]],
    columns: int = 2,
) -> list[str]:
    state_key = _wizard_state_key(prefix, field)
    selected_set = set(st.session_state.get(state_key, []))
    cols = st.columns(columns)

    for idx, (label, tip) in enumerate(options):
        with cols[idx % columns]:
            is_selected = label in selected_set
            display = f"✓ {label}" if is_selected else label
            if st.button(
                display,
                key=_wizard_state_key(prefix, f"{field}_multi_{idx}"),
                help=tip,
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                if is_selected:
                    selected_set.remove(label)
                else:
                    selected_set.add(label)
                st.session_state[state_key] = sorted(selected_set)
                st.rerun()

    st.session_state[state_key] = sorted(selected_set)
    return sorted(selected_set)


def _render_trust_phase(prefix: str, language: str) -> None:
    start_label = "Let's Begin" if language == "en" else "Jom Mula"
    st.markdown(
        """
        <div class="landing-centered">
        <section class="hero-section">
            <span class="hero-topline">Trusted by 10,000+ Malaysian Students</span>
            <h2 class="hero-headline"><span class="brand-teman">Teman</span><span class="brand-edu">EDU</span> turns uncertainty into a clear education plan.</h2>
            <p class="hero-subline">
                I am Aina, your pathway advisor. In under 3 minutes, we map your readiness, rank realistic SPM/Diploma pathways,
                and show your next 7-day and 30-day actions.
            </p>
            <div class="teman-trust-badges">
                <span class="teman-trust-badge">PDPA-ready</span>
                <span class="teman-trust-badge">Anonymous by default</span>
                <span class="teman-trust-badge">Explainable recommendations</span>
                <span class="teman-trust-badge">No scholarship or visa guarantees</span>
            </div>
        </section>

        <section class="problem-solution-section">
            <div class="section-heading">What you get in 3 minutes</div>
            <div class="steps-grid">
                <article class="step-card">
                    <span class="step-num">1</span>
                    <div>Share your stage and constraints.</div>
                </article>
                <article class="step-card">
                    <span class="step-num">2</span>
                    <div>See top pathways and specific universities.</div>
                </article>
                <article class="step-card">
                    <span class="step-num">3</span>
                    <div>Follow your 7-day and 30-day action plan.</div>
                </article>
            </div>
            <div class="privacy-box">
                🔒 Anonymous by default. We only save if you explicitly give consent.
            </div>
        </section>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1.4, 1.2, 1.4])
    with c2:
        if st.button(start_label, key=_wizard_state_key(prefix, "start_journey"), use_container_width=True, type="primary"):
            st.session_state[_wizard_state_key(prefix, "journey_started")] = True
            st.session_state[_wizard_state_key(prefix, "step")] = 1
            st.rerun()
    st.caption("No pressure. You can change answers anytime.")


def _set_spm_subject_profile(prefix: str, profile: str) -> None:
    profiles = {
        "strong": {"bm": "C", "english": "B", "math": "B", "add_math": "C", "science": "B"},
        "average": {"bm": "C", "english": "C", "math": "C", "add_math": "D", "science": "C"},
        "support": {"bm": "C", "english": "D", "math": "D", "add_math": "E", "science": "D"},
    }
    selected = profiles.get(profile, profiles["average"])
    for subject, grade in selected.items():
        st.session_state[_wizard_state_key(prefix, f"subject_{subject}")] = grade


def _set_preparedness_level(prefix: str, level: str) -> None:
    mapping = {
        "starter": ["Transcript ready"],
        "building": ["Transcript ready", "CV drafted", "Shortlisted institutions"],
        "ready": ["Transcript ready", "CV drafted", "Portfolio draft", "Shortlisted institutions", "Talked to counselor/mentor"],
    }
    st.session_state[_wizard_state_key(prefix, "preparedness_checklist")] = mapping.get(level, ["Transcript ready"])


def _student_profile_state_key(prefix: str) -> str:
    return _wizard_state_key(prefix, "profile")


# Chat refactor plan:
# 1) Keep a single canonical `student_profile` dict in session state.
# 2) Drive question rendering from an ordered map with simple branching.
# 3) Validate and persist each answer deterministically with `validate_answer` + `update_profile`.
# 4) Convert profile into the existing engine input schema via `_profile_to_engine_inputs`.
# 5) Reuse existing deterministic scoring/matching and persistence/export paths.
def _chat_question_map(profile: dict[str, Any]) -> list[dict[str, Any]]:
    level_choice = profile.get("student_level")
    level = "SPM" if level_choice in {None, "I'm not sure"} else level_choice
    current_year = pd.Timestamp.utcnow().year
    questions: list[dict[str, Any]] = [
        {
            "id": "specific_program_interest",
            "label": "Program",
            "prompt": "What programs are you interested in studying?",
            "type": "multiselect_programs",
            "required": True,
            "help_text": "Select up to 3 programs that interest you most. We will map these to real universities and program pages.",
            "options": SPECIFIC_PROGRAM_OPTIONS,
            "privacy_why": "Program specificity gives you real university matches, not vague clusters.",
            "max_selections": 3,
        },
        {
            "id": "student_level",
            "label": "Qualification",
            "prompt": "What qualification are you applying with now?",
            "type": "select",
            "required": True,
            "options": ["SPM", "Diploma", "I'm not sure"],
            "privacy_why": "Qualification stage determines admission route eligibility.",
            "help_text": "If unsure, choose 'I'm not sure'. We will use safe defaults.",
        },
    ]
    if level == "SPM":
        questions.append(
            {
                "id": "spm_academic",
                "label": "SPM Results",
                "prompt": "Share your SPM credits and key subject grades.",
                "type": "spm_academic",
                "required": True,
                "privacy_why": "Credits and subjects are required to check institution entry thresholds.",
                "help_text": "No pressure. If unsure on one subject, pick 'Not sure yet'.",
            }
        )
    else:
        questions.append(
            {
                "id": "diploma_academic",
                "label": "Diploma Results",
                "prompt": "Share your Diploma CGPA and field.",
                "type": "diploma_academic",
                "required": True,
                "privacy_why": "CGPA and diploma field affect progression to degree pathways.",
                "help_text": "This helps us avoid recommending programs outside entry range.",
            }
        )

    questions.extend(
        [
            {
                "id": "destination_targets",
                "label": "Countries",
                "prompt": "Which countries are realistic for your study plan? (up to 3)",
                "type": "countries",
                "required": True,
                "privacy_why": "Country preferences narrow down legal and cost-fit options.",
                "help_text": "Choose the places you can realistically consider right now.",
            },
            {
                "id": "preferred_universities",
                "label": "Universities",
                "prompt": "Any universities already on your radar?",
                "type": "preferred_unis",
                "required": False,
                "privacy_why": "This helps us prioritize institutions you already consider.",
                "help_text": "Optional. Leave blank if you are still exploring.",
            },
            {
                "id": "budget_financing",
                "label": "Budget",
                "prompt": "What budget and financing setup is realistic each month?",
                "type": "budget_financing",
                "required": True,
                "privacy_why": "Budget keeps recommendations financially feasible.",
                "help_text": "Set the amount your family can sustain monthly without stress.",
            },
            {
                "id": "english_evidence",
                "label": "English",
                "prompt": "What English readiness and test evidence do you have now?",
                "type": "english_evidence",
                "required": True,
                "privacy_why": "English evidence filters programs with IELTS/TOEFL requirements.",
                "help_text": "If you do not have scores yet, keep them at 0.",
            },
            {
                "id": "intake_timeline",
                "label": "Timeline",
                "prompt": "Which intake month and year are you targeting?",
                "type": "intake_timeline",
                "required": True,
                "year_options": [current_year, current_year + 1, current_year + 2],
                "privacy_why": "Intake timing helps shortlist institutions with compatible windows.",
                "help_text": "We use this to prioritize realistic application timing.",
            },
            {
                "id": "support_constraints",
                "label": "Constraints",
                "prompt": "What constraints should we protect for in your shortlist?",
                "type": "constraints",
                "required": True,
                "privacy_why": "Constraints prevent unrealistic recommendations.",
                "help_text": "Select all that truly apply to your situation.",
            },
            {
                "id": "priority_preferences",
                "label": "Priorities",
                "prompt": "What matters most in your final shortlist?",
                "type": "priorities",
                "required": True,
                "privacy_why": "Priority factors decide ranking order among matched options.",
                "help_text": "These priorities decide how results are sorted for you.",
            },
            {
                "id": "preparedness_docs",
                "label": "Documents",
                "prompt": "Tap what you already have so we can shape your readiness plan.",
                "type": "preparedness",
                "required": True,
                "privacy_why": "Document readiness tailors the 90-day action plan.",
                "help_text": "Select only what you already have today.",
            },
        ]
    )
    return questions


def _question_answered(question_id: str, profile: dict[str, Any]) -> bool:
    if question_id == "specific_program_interest":
        value = profile.get("specific_program_interest")
        if isinstance(value, list):
            return len(value) > 0
        return bool(value)
    if question_id == "student_level":
        return bool(profile.get("student_level"))
    if question_id == "spm_academic":
        subjects = profile.get("subjects") or {}
        required_subjects = {"bm", "english", "math", "science", "add_math"}
        return bool(profile.get("spm_credits") is not None and required_subjects.issubset(set(subjects.keys())))
    if question_id == "diploma_academic":
        return bool(profile.get("cgpa") is not None and profile.get("diploma_field"))
    if question_id == "destination_targets":
        return bool(profile.get("destination_tags"))
    if question_id == "preferred_universities":
        return True
    if question_id == "budget_financing":
        return bool(profile.get("budget_monthly") and profile.get("financing_mode"))
    if question_id == "english_evidence":
        return bool(profile.get("english_self"))
    if question_id == "intake_timeline":
        return bool(profile.get("target_intake_month") and profile.get("target_intake_year"))
    if question_id == "support_constraints":
        return bool(profile.get("support_constraints"))
    if question_id == "priority_preferences":
        return bool(profile.get("priority_factors") and profile.get("institution_type_pref"))
    if question_id == "preparedness_docs":
        return bool(profile.get("preparedness_checklist"))
    return False


def compute_progress(profile: dict[str, Any], question_map: list[dict[str, Any]]) -> int:
    required_questions = [item for item in question_map if item.get("required")]
    if not required_questions:
        return 0
    answered = sum(1 for item in required_questions if _question_answered(item["id"], profile))
    return int(round((answered / len(required_questions)) * 100))


def next_question(profile: dict[str, Any], question_map: list[dict[str, Any]]) -> str | None:
    for question in question_map:
        if not _question_answered(question["id"], profile):
            return question["id"]
    return None


def validate_answer(question: dict[str, Any], answer: Any) -> tuple[bool, str, Any]:
    question_id = question["id"]
    if question_id in {"specific_program_interest", "student_level", "english_evidence"}:
        if not isinstance(answer, dict):
            return False, "Please select an answer.", answer
    if question_id == "specific_program_interest":
        value = answer.get("specific_program_interest")
        if isinstance(value, list):
            if not value or len(value) == 0:
                return False, "Please select at least 1 program of interest.", answer
            if len(value) > 3:
                return False, "Please select maximum 3 programs only.", answer
            return True, "", answer
        else:
            # Handle legacy single selection
            value = str(value or "").strip()
            if not value:
                return False, "Please select at least 1 program of interest.", answer
            return True, "", answer
    if question_id == "student_level":
        value = str(answer.get("student_level") or "").strip()
        if value not in {"SPM", "Diploma", "I'm not sure"}:
            return False, "Please select SPM, Diploma, or I'm not sure.", answer
        return True, "", answer
    if question_id == "spm_academic":
        try:
            credits = int(answer.get("spm_credits"))
        except (TypeError, ValueError):
            return False, "Please provide your total SPM credits.", answer
        if credits < 0 or credits > 10:
            return False, "SPM credits must be between 0 and 10.", answer
        return True, "", answer
    if question_id == "diploma_academic":
        cgpa = answer.get("cgpa")
        if cgpa is None:
            return False, "Please provide your CGPA.", answer
        if float(cgpa) < 2.0 or float(cgpa) > 4.0:
            return False, "CGPA should be between 2.00 and 4.00.", answer
        if not str(answer.get("diploma_field") or "").strip():
            return False, "Please choose your diploma field.", answer
        return True, "", answer
    if question_id == "destination_targets":
        destinations = answer.get("destination_tags") or []
        if not destinations:
            return False, "Please select at least one country.", answer
        if len(destinations) > 3:
            return False, "Please choose up to 3 countries.", answer
        return True, "", answer
    if question_id == "budget_financing":
        budget = int(answer.get("budget_monthly") or 0)
        if budget <= 0:
            return False, "Please set a monthly budget.", answer
        if not answer.get("financing_mode"):
            return False, "Please choose your financing mode.", answer
        return True, "", answer
    if question_id == "english_evidence":
        if not answer.get("english_self"):
            return False, "Please choose your English readiness.", answer
        return True, "", answer
    if question_id == "intake_timeline":
        if not answer.get("target_intake_month") or not answer.get("target_intake_year"):
            return False, "Please choose intake month and year.", answer
        return True, "", answer
    if question_id == "support_constraints":
        if not (answer.get("support_constraints") or []):
            return False, "Please select at least one constraint option.", answer
        return True, "", answer
    if question_id == "priority_preferences":
        if not (answer.get("priority_factors") or []):
            return False, "Please choose at least one priority factor.", answer
        return True, "", answer
    if question_id == "preparedness_docs":
        if not (answer.get("preparedness_checklist") or []):
            return False, "Please select at least one document status option.", answer
        return True, "", answer
    return True, "", answer


def update_profile(profile: dict[str, Any], question_id: str, answer: Any) -> dict[str, Any]:
    updated = dict(profile)
    if question_id == "specific_program_interest":
        choice = answer.get("specific_program_interest")
        if isinstance(choice, list):
            # Handle multiple selections
            updated["specific_program_interest"] = choice
            # Merge all interest tags from selected programs
            all_tags = []
            for program in choice:
                all_tags.extend(PROGRAM_TAG_MAP.get(program, []))
            # Remove duplicates while preserving order
            updated["interest_tags"] = list(dict.fromkeys(all_tags))
        else:
            # Handle legacy single selection
            updated["specific_program_interest"] = choice
            updated["interest_tags"] = PROGRAM_TAG_MAP.get(choice, ["Business", "IT"])
        return updated
    if question_id == "student_level":
        updated["student_level"] = answer.get("student_level")
        return updated
    if question_id == "spm_academic":
        updated["spm_credits"] = int(answer.get("spm_credits"))
        updated["subjects"] = answer.get("subjects", {})
        return updated
    if question_id == "diploma_academic":
        updated["cgpa"] = round(float(answer.get("cgpa")), 2)
        updated["diploma_field"] = answer.get("diploma_field")
        return updated
    if question_id == "destination_targets":
        destination_tags = answer.get("destination_tags", [])
        updated["destination_tags"] = destination_tags[:3]
        updated["target_ranking_tier"] = answer.get("target_ranking_tier", "Any")
        updated["destination_choice"] = "Malaysia only" if set(updated["destination_tags"]) == {"Malaysia"} else "Open to overseas"
        return updated
    if question_id == "preferred_universities":
        updated["preferred_universities"] = [item for item in answer.get("preferred_universities", []) if item != "Not sure yet"]
        return updated
    if question_id == "budget_financing":
        budget = int(answer.get("budget_monthly"))
        updated["budget_monthly"] = budget
        if budget < 800:
            updated["budget_range"] = "< RM 800"
        elif budget <= 2000:
            updated["budget_range"] = "RM 800-2000"
        elif budget <= 5000:
            updated["budget_range"] = "RM 2000-5000"
        else:
            updated["budget_range"] = "RM 5000+"
        updated["financing_mode"] = answer.get("financing_mode")
        return updated
    if question_id == "english_evidence":
        updated["english_self"] = answer.get("english_self")
        updated["ielts_score"] = answer.get("ielts_score")
        updated["toefl_score"] = answer.get("toefl_score")
        updated["english_test_plan"] = answer.get("english_test_plan")
        proxy_score = None
        if answer.get("ielts_score"):
            proxy_score = int(round((float(answer["ielts_score"]) / 9.0) * 100))
        elif answer.get("toefl_score"):
            proxy_score = int(round((int(answer["toefl_score"]) / 120.0) * 100))
        updated["english_test_score"] = proxy_score
        return updated
    if question_id == "intake_timeline":
        updated["target_intake_month"] = answer.get("target_intake_month")
        updated["target_intake_year"] = int(answer.get("target_intake_year"))
        updated["timeline_urgency"] = answer.get("timeline_urgency", "normal")
        updated["intake_window"] = answer.get("intake_window", "next_6_12_months")
        return updated
    if question_id == "support_constraints":
        constraints = answer.get("support_constraints", [])
        updated["support_constraints"] = constraints
        updated["willing_relocate"] = not any("stay near" in item.lower() for item in constraints)
        updated["family_constraints"] = "location" if any("stay near" in item.lower() for item in constraints) else "none"
        return updated
    if question_id == "priority_preferences":
        updated["priority_factors"] = answer.get("priority_factors", [])
        updated["institution_type_pref"] = answer.get("institution_type_pref", "Both public and private")
        return updated
    if question_id == "preparedness_docs":
        docs = answer.get("preparedness_checklist", [])
        updated["preparedness_checklist"] = docs
        doc_count = len([item for item in docs if item != "None yet"])
        if doc_count >= 6:
            updated["preparedness_level"] = "ready"
        elif doc_count >= 3:
            updated["preparedness_level"] = "building"
        else:
            updated["preparedness_level"] = "starter"
        return updated
    return updated


def render_chat_message(role: str, content: str) -> None:
    """Render a chat message with smooth animation and modern styling"""
    css_class = "assistant-message" if role == "assistant" else "user-message"
    author = "Aina • TemanEDU" if role == "assistant" else "You"
    avatar = "🤖" if role == "assistant" else "👤"
    
    st.markdown(
        f"""
        <div class='message {css_class} fade-in'>
            <div class='message-avatar'>{avatar}</div>
            <div class='message-content'>
                <div class='message-author'>{escape(author)}</div>
                <div class='message-text'>{escape(content)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_transition_message(question_id: str, answer: str) -> str:
    """Get encouraging transition message based on question answered"""
    transitions = {
        "specific_program_interest": [
            f"Awesome choices! {answer} - fantastic fields with strong career prospects. 🚀",
            "Let me gather some details about your academic background next...",
        ],
        "student_level": [
            "Perfect! Got it. ✨",
            "Now let's talk about your academic achievements so far...",
        ],
        "spm_academic": [
            "Great! Your results look solid. 📚",
            "Next, let's explore which countries interest you...",
        ],
        "diploma_academic": [
            "Excellent progress! 🎓",
            "Now, where do you see yourself studying?",
        ],
        "destination_targets": [
            "Wonderful selections! 🌍",
            "Let's talk about budget and financing next...",
        ],
        "preferred_universities": [
            "Noted! Good choices on your radar. 👍",
            "Moving on to the practical side - budget and financing...",
        ],
        "budget_financing": [
            "Perfect! Financial planning is key. 💰",
            "Let's check your English readiness...",
        ],
        "english_evidence": [
            "Got it! Your English profile is clear. 📝",
            "Now for the timing - when are you planning to start?",
        ],
        "intake_timeline": [
            "Brilliant! Timeline locked in. ⏰",
            "Let's identify any constraints we should work around...",
        ],
        "support_constraints": [
            "Understood! We'll keep these in mind. 🎯",
            "Almost there! What matters most to you in your final choices?",
        ],
        "priority_preferences": [
            "Excellent priorities! These will guide your matches. ⭐",
            "Last question - let's check your document readiness...",
        ],
        "preparedness_docs": [
            "Fantastic! You're well-prepared! 🎉",
            "Ready to generate your personalized pathway recommendations!",
        ],
    }
    
    messages = transitions.get(question_id, ["Great!", "Moving to the next question..."])
    return "\n\n".join(messages)


def _format_answer_for_chat(question_id: str, profile: dict[str, Any]) -> str:
    if question_id == "specific_program_interest":
        programs = profile.get("specific_program_interest")
        if isinstance(programs, list):
            return ", ".join(programs) if programs else "-"
        return str(programs) if programs else "-"
    if question_id == "student_level":
        return str(profile.get("student_level"))
    if question_id == "spm_academic":
        subjects = profile.get("subjects", {})
        return (
            f"SPM credits: {profile.get('spm_credits', '-')}; "
            f"BM {subjects.get('bm', '-')}, English {subjects.get('english', '-')}, "
            f"Math {subjects.get('math', '-')}, Science {subjects.get('science', '-')}, Add Math {subjects.get('add_math', '-')}"
        )
    if question_id == "diploma_academic":
        return f"CGPA {profile.get('cgpa', '-')}, field {profile.get('diploma_field', '-')}"
    if question_id == "destination_targets":
        return f"Countries: {', '.join(profile.get('destination_tags', []))}; QS: {profile.get('target_ranking_tier', 'Any')}"
    if question_id == "preferred_universities":
        selected = profile.get("preferred_universities", [])
        return f"University preferences: {', '.join(selected) if selected else 'Not sure yet'}"
    if question_id == "budget_financing":
        return f"Budget RM {profile.get('budget_monthly', '-')}/month, financing: {profile.get('financing_mode', '-')}"
    if question_id == "english_evidence":
        parts = [f"Level: {profile.get('english_self', '-')}"]
        if profile.get("ielts_score"):
            parts.append(f"IELTS {profile['ielts_score']}")
        if profile.get("toefl_score"):
            parts.append(f"TOEFL {profile['toefl_score']}")
        parts.append(f"Plan: {profile.get('english_test_plan', '-')}")
        return "; ".join(parts)
    if question_id == "intake_timeline":
        return (
            f"Intake: {profile.get('target_intake_month', '-')} {profile.get('target_intake_year', '-')}; "
            f"Urgency: {profile.get('timeline_urgency', '-')}"
        )
    if question_id == "support_constraints":
        return ", ".join(profile.get("support_constraints", []))
    if question_id == "priority_preferences":
        return (
            f"Priorities: {', '.join(profile.get('priority_factors', []))}; "
            f"Institution type: {profile.get('institution_type_pref', '-')}"
        )
    if question_id == "preparedness_docs":
        docs = profile.get("preparedness_checklist", [])
        return f"Documents ready: {', '.join(docs)}"
    return "-"


def _clear_profile_answer(profile: dict[str, Any], question_id: str) -> dict[str, Any]:
    updated = dict(profile)
    if question_id == "specific_program_interest":
        updated.pop("specific_program_interest", None)
        updated.pop("interest_tags", None)
    elif question_id == "student_level":
        updated.pop("student_level", None)
    elif question_id == "spm_academic":
        updated.pop("spm_credits", None)
        updated.pop("subjects", None)
    elif question_id == "diploma_academic":
        updated.pop("cgpa", None)
        updated.pop("diploma_field", None)
    elif question_id == "destination_targets":
        updated.pop("destination_tags", None)
        updated.pop("target_ranking_tier", None)
    elif question_id == "preferred_universities":
        updated.pop("preferred_universities", None)
    elif question_id == "budget_financing":
        updated.pop("budget_monthly", None)
        updated.pop("budget_range", None)
        updated.pop("financing_mode", None)
    elif question_id == "english_evidence":
        updated.pop("english_self", None)
        updated.pop("ielts_score", None)
        updated.pop("toefl_score", None)
        updated.pop("english_test_plan", None)
        updated.pop("english_test_score", None)
    elif question_id == "intake_timeline":
        updated.pop("target_intake_month", None)
        updated.pop("target_intake_year", None)
        updated.pop("timeline_urgency", None)
        updated.pop("intake_window", None)
    elif question_id == "support_constraints":
        updated.pop("support_constraints", None)
    elif question_id == "priority_preferences":
        updated.pop("priority_factors", None)
        updated.pop("institution_type_pref", None)
    elif question_id == "preparedness_docs":
        updated.pop("preparedness_checklist", None)
        updated.pop("preparedness_level", None)
    return updated


def _profile_to_engine_inputs(profile: dict[str, Any]) -> dict[str, Any]:
    level_choice = profile.get("student_level", "SPM")
    level = "SPM" if level_choice == "I'm not sure" else level_choice
    subjects = profile.get("subjects", {})
    destinations = profile.get("destination_tags") or ["Malaysia"]
    destination_choice = "Malaysia only" if set(destinations) == {"Malaysia"} else "Open to overseas"
    destination_preference = "malaysia_only" if destination_choice == "Malaysia only" else "open_overseas"
    financing_mode = profile.get("financing_mode", "self_fund")
    support_constraints = profile.get("support_constraints") or []
    scholarship_needed = financing_mode == "scholarship" or any("scholarship" in item.lower() for item in support_constraints)
    need_work_part_time = financing_mode == "part_time" or any("part-time" in item.lower() for item in support_constraints)
    family_constraints = "location" if any("stay near" in item.lower() for item in support_constraints) else "none"
    willingness = not any("stay near" in item.lower() for item in support_constraints)

    return {
        "student_level": level,
        "spm_credits": int(profile.get("spm_credits") or 0),
        "subjects": {
            "bm": subjects.get("bm", "C"),
            "english": subjects.get("english", "C"),
            "math": subjects.get("math", "C"),
            "add_math": subjects.get("add_math", "C"),
            "science": subjects.get("science", "C"),
        },
        "cgpa": float(profile.get("cgpa") or 2.8),
        "diploma_field": profile.get("diploma_field", "General"),
        "interest_tags": profile.get("interest_tags") or PROGRAM_TAG_MAP.get(profile.get("specific_program_interest"), ["Business", "IT"]),
        "specific_program_interest": profile.get("specific_program_interest") if isinstance(profile.get("specific_program_interest"), list) else [profile.get("specific_program_interest", "General")],
        "budget_range": profile.get("budget_range", "RM 800-2000"),
        "budget_monthly": int(profile.get("budget_monthly") or 1200),
        "financing_mode": financing_mode,
        "need_work_part_time": need_work_part_time,
        "english_self": profile.get("english_self", "Intermediate"),
        "english_test_score": profile.get("english_test_score"),
        "ielts_score": profile.get("ielts_score"),
        "toefl_score": profile.get("toefl_score"),
        "english_test_plan": profile.get("english_test_plan", "Already have score"),
        "destination_preference": destination_preference,
        "destination_tags": destinations,
        "preferred_universities": profile.get("preferred_universities", []),
        "target_ranking_tier": profile.get("target_ranking_tier", "Any"),
        "target_intake_month": profile.get("target_intake_month", ""),
        "target_intake_year": int(profile.get("target_intake_year") or pd.Timestamp.utcnow().year),
        "intake_window": profile.get("intake_window", "next_6_12_months"),
        "support_constraints": support_constraints,
        "priority_factors": profile.get("priority_factors", []),
        "institution_type_pref": profile.get("institution_type_pref", "Both public and private"),
        "scholarship_needed": scholarship_needed,
        "timeline_urgency": profile.get("timeline_urgency", "normal"),
        "family_constraints": family_constraints,
        "willing_relocate": profile.get("willing_relocate", willingness),
        "preparedness_checklist": [item for item in profile.get("preparedness_checklist", []) if item != "None yet"],
        "preparedness_level": profile.get("preparedness_level", "starter"),
        "consent_to_save": bool(profile.get("consent_to_save", False)),
        "optional_email": (profile.get("optional_email") or "").strip() or None,
    }


def _render_profile_edit_chips(prefix: str, profile: dict[str, Any], question_map: list[dict[str, Any]]) -> None:
    answered = [question for question in question_map if _question_answered(question["id"], profile)]
    if not answered:
        return
    st.markdown("**Your answers so far (tap to edit):**")
    chip_cols = st.columns(3)
    for idx, question in enumerate(answered):
        with chip_cols[idx % 3]:
            if st.button(
                f"Edit: {question['label']}",
                key=_wizard_state_key(prefix, f"edit_{question['id']}"),
                use_container_width=True,
                type="secondary",
            ):
                st.session_state[_wizard_state_key(prefix, "chat_edit_question")] = question["id"]
                _query_set(chat_q=question["id"])
                st.rerun()


def render_chat(prefix: str, language: str) -> tuple[bool, dict[str, Any] | None]:
    profile_key = _student_profile_state_key(prefix)
    edit_key = _wizard_state_key(prefix, "chat_edit_question")
    if profile_key not in st.session_state:
        st.session_state[profile_key] = {}
    profile = dict(st.session_state.get(profile_key, {}))
    question_map = _chat_question_map(profile)
    current_question_id = st.session_state.get(edit_key) or next_question(profile, question_map)
    valid_question_ids = {item["id"] for item in question_map}
    if current_question_id == "done" or (current_question_id and current_question_id not in valid_question_ids):
        current_question_id = next_question(profile, question_map)
    progress = compute_progress(profile, question_map)
    
    # Modern progress indicator
    st.markdown(
        f"""
        <div class='chat-progress-container'>
            <div class='progress-bar-wrapper'>
                <div class='progress-bar' style='width: {progress}%'></div>
            </div>
            <div class='progress-text'>{progress}% Complete</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if current_question_id:
        ids = [item["id"] for item in question_map]
        current_idx = ids.index(current_question_id) + 1 if current_question_id in ids else len(ids)
        st.caption(f"✨ Question {current_idx} of {len(question_map)}")

    # Chat messages container
    st.markdown("<div class='chat-messages-container'>", unsafe_allow_html=True)
    
    # Render conversation history
    for idx, question in enumerate(question_map):
        question_id = question["id"]
        answered = _question_answered(question_id, profile)
        
        if answered and question_id != current_question_id:
            # Show previous Q&A
            render_chat_message("assistant", question["prompt"])
            render_chat_message("user", _format_answer_for_chat(question_id, profile))
            
            # Add transition message after answer
            transition = _get_transition_message(question_id, _format_answer_for_chat(question_id, profile))
            st.markdown(
                f"<div class='transition-message fade-in'>💬 {escape(transition)}</div>",
                unsafe_allow_html=True,
            )
            continue
        
        if question_id == current_question_id:
            # Current question being answered
            render_chat_message("assistant", question["prompt"])
            
            # Input panel
            st.markdown(
                f"""
                <div class='chat-input-panel fade-in'>
                    <div class='panel-header'>
                        <span class='panel-icon'>📋</span>
                        <strong>{escape(question.get('label', 'Question'))}</strong>
                    </div>
                    <div class='panel-help'>{escape(question.get('help_text', ''))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            st.markdown(
                f"<div class='privacy-note'>🔒 {escape(question.get('privacy_why', 'Your data stays private.'))}</div>",
                unsafe_allow_html=True,
            )
            break
    
    st.markdown("</div>", unsafe_allow_html=True)

    # Handle completion
    if current_question_id is None:
        st.markdown(
            """
            <div class='completion-banner fade-in'>
                🎉 Amazing! You've completed all questions!<br>
                <span class='banner-subtext'>Click below to see your personalized pathway recommendations</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        if st.button(
            "🚀 Generate My Recommendations",
            key=_wizard_state_key(prefix, "chat_generate"),
            type="primary",
            use_container_width=True,
        ):
            return True, _profile_to_engine_inputs(profile)
        return False, None

    # Render input based on question type
    current_question = next((item for item in question_map if item["id"] == current_question_id), None)
    if not current_question:
        return False, None
    _query_set(chat_q=current_question_id)

    answer_payload: dict[str, Any] = {}
    question_type = current_question["type"]

    # Input rendering (wrap in styled container)
    st.markdown("<div class='input-area fade-in'>", unsafe_allow_html=True)

    if question_type == "multiselect_programs":
        options = current_question["options"]
        max_selections = current_question.get("max_selections", 3)
        default_value = profile.get(current_question_id, [])
        if isinstance(default_value, str):
            default_value = [default_value] if default_value else []
        
        selected = st.multiselect(
            f"Choose up to {max_selections} programs",
            options,
            default=default_value,
            max_selections=max_selections,
            key=_wizard_state_key(prefix, f"chat_input_{current_question_id}"),
            help=f"Select {max_selections} programs maximum that align with your interests"
        )
        answer_payload[current_question_id] = selected
    elif question_type == "select":
        options = current_question["options"]
        default_value = profile.get(current_question_id, options[0])
        index = options.index(default_value) if default_value in options else 0
        selected = st.radio(
            "Choose one",
            options,
            index=index,
            key=_wizard_state_key(prefix, f"chat_input_{current_question_id}"),
        )
        answer_payload[current_question_id] = selected
    elif question_type == "spm_academic":
        credits = st.number_input(
            "Total SPM credits",
            min_value=0,
            max_value=10,
            value=int(profile.get("spm_credits", 5)),
            step=1,
            key=_wizard_state_key(prefix, "chat_spm_credits"),
        )
        s1, s2, s3, s4, s5 = st.columns(5)
        subject_defaults = profile.get("subjects", {})
        with s1:
            bm = st.selectbox("BM", SUBJECT_GRADE_OPTIONS, index=SUBJECT_GRADE_OPTIONS.index(subject_defaults.get("bm", "C")) if subject_defaults.get("bm", "C") in SUBJECT_GRADE_OPTIONS else 6, key=_wizard_state_key(prefix, "chat_sub_bm"))
        with s2:
            bi = st.selectbox("English", SUBJECT_GRADE_OPTIONS, index=SUBJECT_GRADE_OPTIONS.index(subject_defaults.get("english", "C")) if subject_defaults.get("english", "C") in SUBJECT_GRADE_OPTIONS else 6, key=_wizard_state_key(prefix, "chat_sub_english"))
        with s3:
            math = st.selectbox("Math", SUBJECT_GRADE_OPTIONS, index=SUBJECT_GRADE_OPTIONS.index(subject_defaults.get("math", "C")) if subject_defaults.get("math", "C") in SUBJECT_GRADE_OPTIONS else 6, key=_wizard_state_key(prefix, "chat_sub_math"))
        with s4:
            add_math = st.selectbox("Add Math", SUBJECT_GRADE_OPTIONS, index=SUBJECT_GRADE_OPTIONS.index(subject_defaults.get("add_math", "Not sure yet")) if subject_defaults.get("add_math", "Not sure yet") in SUBJECT_GRADE_OPTIONS else 10, key=_wizard_state_key(prefix, "chat_sub_add_math"))
        with s5:
            science = st.selectbox("Science", SUBJECT_GRADE_OPTIONS, index=SUBJECT_GRADE_OPTIONS.index(subject_defaults.get("science", "C")) if subject_defaults.get("science", "C") in SUBJECT_GRADE_OPTIONS else 6, key=_wizard_state_key(prefix, "chat_sub_science"))
        answer_payload = {
            "spm_credits": int(credits),
            "subjects": {
                "bm": "C" if bm == "Not sure yet" else bm,
                "english": "C" if bi == "Not sure yet" else bi,
                "math": "C" if math == "Not sure yet" else math,
                "add_math": "C" if add_math == "Not sure yet" else add_math,
                "science": "C" if science == "Not sure yet" else science,
            },
        }
    elif question_type == "diploma_academic":
        cgpa = st.slider("Diploma CGPA", 2.0, 4.0, float(profile.get("cgpa", 2.8)), 0.01, key=_wizard_state_key(prefix, "chat_cgpa"))
        diploma_field = st.selectbox(
            "Diploma field",
            ["IT / Computing", "Engineering", "Business", "Health Sciences", "Creative / Design", "Other"],
            index=0,
            key=_wizard_state_key(prefix, "chat_diploma_field"),
        )
        answer_payload = {"cgpa": round(float(cgpa), 2), "diploma_field": diploma_field}
    elif question_type == "countries":
        selected_countries = st.multiselect(
            "Target countries (up to 3)",
            COUNTRY_OPTIONS,
            default=profile.get("destination_tags", ["Malaysia"]),
            key=_wizard_state_key(prefix, "chat_destination_tags"),
        )
        ranking_tier = st.radio(
            "Preferred QS ranking tier",
            ["Any", "Top 100", "Top 300", "Top 500"],
            index=["Any", "Top 100", "Top 300", "Top 500"].index(profile.get("target_ranking_tier", "Any")) if profile.get("target_ranking_tier", "Any") in ["Any", "Top 100", "Top 300", "Top 500"] else 0,
            key=_wizard_state_key(prefix, "chat_target_ranking_tier"),
        )
        answer_payload = {"destination_tags": selected_countries, "target_ranking_tier": ranking_tier}
    elif question_type == "preferred_unis":
        selected = st.multiselect(
            "University names (optional)",
            PREFERRED_UNI_OPTIONS,
            default=profile.get("preferred_universities", []),
            key=_wizard_state_key(prefix, "chat_preferred_unis"),
        )
        answer_payload = {"preferred_universities": selected}
    elif question_type == "budget_financing":
        budget = st.slider(
            "Monthly affordability (RM)",
            400,
            8000,
            int(profile.get("budget_monthly", 1500)),
            step=100,
            key=_wizard_state_key(prefix, "chat_budget_monthly"),
        )
        financing = st.radio(
            "Main financing mode",
            ["scholarship", "part_time", "self_fund"],
            format_func=lambda item: {
                "scholarship": "Need scholarship support",
                "part_time": "Need part-time compatible route",
                "self_fund": "Self-funded / family-supported",
            }[item],
            index=["scholarship", "part_time", "self_fund"].index(profile.get("financing_mode", "self_fund")) if profile.get("financing_mode", "self_fund") in ["scholarship", "part_time", "self_fund"] else 2,
            key=_wizard_state_key(prefix, "chat_financing_mode"),
        )
        answer_payload = {"budget_monthly": int(budget), "financing_mode": financing}
    elif question_type == "english_evidence":
        english_self = st.radio(
            "English readiness",
            ["Beginner", "Intermediate", "Advanced"],
            index=["Beginner", "Intermediate", "Advanced"].index(profile.get("english_self", "Intermediate")) if profile.get("english_self", "Intermediate") in ["Beginner", "Intermediate", "Advanced"] else 1,
            key=_wizard_state_key(prefix, "chat_english_self"),
        )
        c1, c2 = st.columns(2)
        with c1:
            ielts = st.number_input("IELTS (0 if none)", 0.0, 9.0, float(profile.get("ielts_score") or 0.0), step=0.5, key=_wizard_state_key(prefix, "chat_ielts"))
        with c2:
            toefl = st.number_input("TOEFL (0 if none)", 0, 120, int(profile.get("toefl_score") or 0), step=1, key=_wizard_state_key(prefix, "chat_toefl"))
        english_plan = st.radio(
            "Test status",
            ["Already have score", "Plan to take test within 3 months", "Not planning yet"],
            index=["Already have score", "Plan to take test within 3 months", "Not planning yet"].index(profile.get("english_test_plan", "Already have score")) if profile.get("english_test_plan", "Already have score") in ["Already have score", "Plan to take test within 3 months", "Not planning yet"] else 0,
            key=_wizard_state_key(prefix, "chat_english_plan"),
        )
        answer_payload = {
            "english_self": english_self,
            "ielts_score": float(ielts) if ielts > 0 else None,
            "toefl_score": int(toefl) if toefl > 0 else None,
            "english_test_plan": english_plan,
        }
    elif question_type == "intake_timeline":
        intake_month = st.selectbox(
            "Target intake month",
            ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
            index=["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"].index(profile.get("target_intake_month", "September")) if profile.get("target_intake_month", "September") in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"] else 8,
            key=_wizard_state_key(prefix, "chat_intake_month"),
        )
        year_options = current_question.get("year_options", [pd.Timestamp.utcnow().year, pd.Timestamp.utcnow().year + 1])
        intake_year = st.selectbox(
            "Target intake year",
            year_options,
            index=0,
            key=_wizard_state_key(prefix, "chat_intake_year"),
        )
        urgency_mode = st.radio(
            "Application urgency",
            ["urgent", "normal", "flexible"],
            format_func=lambda item: {
                "urgent": "Need to apply in next 3 months",
                "normal": "Can plan over 6-12 months",
                "flexible": "Flexible timeline",
            }[item],
            index=["urgent", "normal", "flexible"].index(profile.get("timeline_urgency", "normal")) if profile.get("timeline_urgency", "normal") in ["urgent", "normal", "flexible"] else 1,
            key=_wizard_state_key(prefix, "chat_intake_urgency"),
        )
        intake_window = "next_3_months" if urgency_mode == "urgent" else "next_6_12_months" if urgency_mode == "normal" else "flexible_local"
        answer_payload = {
            "target_intake_month": intake_month,
            "target_intake_year": intake_year,
            "timeline_urgency": "normal" if urgency_mode == "flexible" else urgency_mode,
            "intake_window": intake_window,
        }
    elif question_type == "constraints":
        support_constraints = st.multiselect(
            "Select all that apply",
            [
                "No major constraints right now",
                "Need scholarship or PTPTN support",
                "Need part-time compatible study plan",
                "Need lower tuition options",
                "Family prefers I stay near home",
                "Prefer public universities",
            ],
            default=profile.get("support_constraints", ["No major constraints right now"]),
            key=_wizard_state_key(prefix, "chat_support_constraints"),
        )
        if "No major constraints right now" in support_constraints and len(support_constraints) > 1:
            support_constraints = ["No major constraints right now"]
        answer_payload = {"support_constraints": support_constraints}
    elif question_type == "priorities":
        priority_factors = st.multiselect(
            "Select your top priorities",
            [
                "Lower tuition cost",
                "Higher QS ranking",
                "Scholarship availability",
                "Strong employability outcome",
                "Multiple intakes per year",
                "Closer to home/family",
            ],
            default=profile.get("priority_factors", ["Lower tuition cost", "Strong employability outcome"]),
            key=_wizard_state_key(prefix, "chat_priority_factors"),
        )
        institution_type_pref = st.radio(
            "Institution type",
            ["Both public and private", "Public only", "Private only"],
            index=["Both public and private", "Public only", "Private only"].index(profile.get("institution_type_pref", "Both public and private")) if profile.get("institution_type_pref", "Both public and private") in ["Both public and private", "Public only", "Private only"] else 0,
            key=_wizard_state_key(prefix, "chat_institution_type"),
        )
        answer_payload = {"priority_factors": priority_factors, "institution_type_pref": institution_type_pref}
    elif question_type == "preparedness":
        selected_docs = st.multiselect(
            "Select all that you already have",
            DOC_CHECKLIST_OPTIONS,
            default=profile.get("preparedness_checklist", ["None yet"]),
            key=_wizard_state_key(prefix, "chat_preparedness_docs"),
        )
        if "None yet" in selected_docs and len(selected_docs) > 1:
            selected_docs = ["None yet"]
        answer_payload = {"preparedness_checklist": selected_docs}

    st.markdown("</div>", unsafe_allow_html=True)

    # Navigation buttons
    st.markdown("<div class='nav-buttons'>", unsafe_allow_html=True)
    nav_left, nav_right = st.columns(2)
    questions_order = [item["id"] for item in question_map]
    current_idx = questions_order.index(current_question_id)
    
    with nav_left:
        if st.button(
            "⬅️ Back",
            key=_wizard_state_key(prefix, "chat_back"),
            use_container_width=True,
            disabled=current_idx == 0,
            type="secondary",
        ):
            previous_question = questions_order[current_idx - 1]
            st.session_state[edit_key] = previous_question
            st.rerun()
    
    with nav_right:
        next_label = "✅ Save & Continue" if current_idx < len(questions_order) - 1 else "🎯 Complete & Review"
        if st.button(
            next_label,
            key=_wizard_state_key(prefix, "chat_continue"),
            use_container_width=True,
            type="primary",
        ):
            valid, error, normalized = validate_answer(current_question, answer_payload)
            if not valid:
                st.error(f"⚠️ {error}")
            else:
                updated_profile = update_profile(profile, current_question_id, normalized)
                st.session_state[profile_key] = updated_profile
                st.session_state[_wizard_state_key(prefix, "chat_edit_question")] = None
                
                # Show success message
                st.success("✨ Saved! Moving on...")
                
                next_question_id = next_question(updated_profile, _chat_question_map(updated_profile))
                _query_set(chat_q=next_question_id if next_question_id else "done")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

    # Edit option for current answer
    if _question_answered(current_question_id, profile):
        if st.button(
            "🔄 Clear & Re-answer",
            key=_wizard_state_key(prefix, f"chat_clear_{current_question_id}"),
            type="secondary",
        ):
            updated_profile = _clear_profile_answer(profile, current_question_id)
            st.session_state[profile_key] = updated_profile
            st.session_state[edit_key] = current_question_id
            st.rerun()

    return False, None


def _step_has_answer(prefix: str, step: int) -> bool:
    level = st.session_state.get(_wizard_state_key(prefix, "student_level"))
    checks = {
        1: bool(st.session_state.get(_wizard_state_key(prefix, "specific_program_interest"))),
        2: bool(level),
        3: bool(st.session_state.get(_wizard_state_key(prefix, "spm_credits"))) if level in ["SPM", "I'm not sure", None] else bool(st.session_state.get(_wizard_state_key(prefix, "cgpa"))),
        4: bool(st.session_state.get(_wizard_state_key(prefix, "destination_tags"))),
        5: bool(st.session_state.get(_wizard_state_key(prefix, "budget_monthly"))) and bool(st.session_state.get(_wizard_state_key(prefix, "financing_mode"))),
        6: bool(st.session_state.get(_wizard_state_key(prefix, "english_self"))),
        7: bool(st.session_state.get(_wizard_state_key(prefix, "target_intake_month"))) and bool(st.session_state.get(_wizard_state_key(prefix, "target_intake_year"))),
        8: bool(st.session_state.get(_wizard_state_key(prefix, "support_constraints"))),
        9: bool(st.session_state.get(_wizard_state_key(prefix, "priority_factors"))),
        10: bool(st.session_state.get(_wizard_state_key(prefix, "preparedness_level"))),
    }
    return checks.get(step, False)


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _apply_chat_response(prefix: str, step: int, message: str) -> bool:
    text = _normalize_text(message)
    if not text:
        return False

    if step == 1:
        if "diploma" in text:
            st.session_state[_wizard_state_key(prefix, "student_level")] = "Diploma"
            return True
        if "spm" in text:
            st.session_state[_wizard_state_key(prefix, "student_level")] = "SPM"
            return True
        if "not sure" in text or "unsure" in text:
            st.session_state[_wizard_state_key(prefix, "student_level")] = "I'm not sure"
            return True
        return False

    if step == 2:
        level_choice = st.session_state.get(_wizard_state_key(prefix, "student_level"), "SPM")
        level = "SPM" if level_choice == "I'm not sure" else level_choice
        if level == "SPM":
            if "7" in text or "high" in text:
                st.session_state[_wizard_state_key(prefix, "spm_credits_band")] = "band_7"
                st.session_state[_wizard_state_key(prefix, "spm_credits")] = 8
                return True
            if "5" in text or "6" in text or "mid" in text:
                st.session_state[_wizard_state_key(prefix, "spm_credits_band")] = "band_56"
                st.session_state[_wizard_state_key(prefix, "spm_credits")] = 6
                return True
            if "3" in text or "4" in text or "low" in text:
                st.session_state[_wizard_state_key(prefix, "spm_credits_band")] = "band_34"
                st.session_state[_wizard_state_key(prefix, "spm_credits")] = 4
                return True
        else:
            if "3.2" in text or "above" in text or "high" in text:
                st.session_state[_wizard_state_key(prefix, "cgpa_band")] = "cgpa_high"
                st.session_state[_wizard_state_key(prefix, "cgpa")] = 3.4
                return True
            if "2.5" in text or "3.2" in text or "mid" in text:
                st.session_state[_wizard_state_key(prefix, "cgpa_band")] = "cgpa_mid"
                st.session_state[_wizard_state_key(prefix, "cgpa")] = 2.8
                return True
            if "below" in text or "low" in text:
                st.session_state[_wizard_state_key(prefix, "cgpa_band")] = "cgpa_low"
                st.session_state[_wizard_state_key(prefix, "cgpa")] = 2.3
                return True
        return False

    if step == 3:
        level_choice = st.session_state.get(_wizard_state_key(prefix, "student_level"), "SPM")
        level = "SPM" if level_choice == "I'm not sure" else level_choice
        if level == "SPM":
            if "strong" in text:
                st.session_state[_wizard_state_key(prefix, "subject_profile")] = "strong"
                _set_spm_subject_profile(prefix, "strong")
                return True
            if "average" in text or "pass" in text:
                st.session_state[_wizard_state_key(prefix, "subject_profile")] = "average"
                _set_spm_subject_profile(prefix, "average")
                return True
            if "support" in text:
                st.session_state[_wizard_state_key(prefix, "subject_profile")] = "support"
                _set_spm_subject_profile(prefix, "support")
                return True
        else:
            if "it" in text or "engineering" in text:
                st.session_state[_wizard_state_key(prefix, "diploma_field")] = "IT"
                return True
            if "business" in text or "economic" in text:
                st.session_state[_wizard_state_key(prefix, "diploma_field")] = "Business"
                return True
            if "creative" in text or "other" in text:
                st.session_state[_wizard_state_key(prefix, "diploma_field")] = "General"
                return True
        return False

    if step == 4:
        if "business" in text or "finance" in text:
            st.session_state[_wizard_state_key(prefix, "interest_cluster")] = "biz"
            st.session_state[_wizard_state_key(prefix, "interest_tags")] = ["Business", "Economics"]
            return True
        if "tech" in text or "engineering" in text or "it" in text:
            st.session_state[_wizard_state_key(prefix, "interest_cluster")] = "tech"
            st.session_state[_wizard_state_key(prefix, "interest_tags")] = ["IT", "Engineering", "Data"]
            return True
        if "creative" in text or "health" in text:
            st.session_state[_wizard_state_key(prefix, "interest_cluster")] = "care"
            st.session_state[_wizard_state_key(prefix, "interest_tags")] = ["Creative", "Health"]
            return True
        return False

    if step == 5:
        if "below" in text or "800" in text or "low" in text:
            st.session_state[_wizard_state_key(prefix, "budget_band")] = "low"
            st.session_state[_wizard_state_key(prefix, "budget_range")] = "< RM 800"
            st.session_state[_wizard_state_key(prefix, "budget_monthly")] = 700
            return True
        if "2000" in text or "mid" in text:
            st.session_state[_wizard_state_key(prefix, "budget_band")] = "mid"
            st.session_state[_wizard_state_key(prefix, "budget_range")] = "RM 800-2000"
            st.session_state[_wizard_state_key(prefix, "budget_monthly")] = 1400
            return True
        if "above" in text or "high" in text:
            st.session_state[_wizard_state_key(prefix, "budget_band")] = "high"
            st.session_state[_wizard_state_key(prefix, "budget_range")] = "RM 2000-5000"
            st.session_state[_wizard_state_key(prefix, "budget_monthly")] = 3200
            return True
        return False

    if step == 6:
        if "beginner" in text:
            st.session_state[_wizard_state_key(prefix, "english_self")] = "Beginner"
            return True
        if "intermediate" in text:
            st.session_state[_wizard_state_key(prefix, "english_self")] = "Intermediate"
            return True
        if "advanced" in text:
            st.session_state[_wizard_state_key(prefix, "english_self")] = "Advanced"
            return True
        return False

    if step == 7:
        if "malaysia" in text and "only" in text:
            st.session_state[_wizard_state_key(prefix, "destination_choice")] = "Malaysia only"
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = ["Malaysia"]
            st.session_state[_wizard_state_key(prefix, "willing_relocate")] = False
            return True
        if "overseas" in text or "open" in text:
            st.session_state[_wizard_state_key(prefix, "destination_choice")] = "Open to overseas"
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = ["Malaysia", "Australia", "UK"]
            st.session_state[_wizard_state_key(prefix, "willing_relocate")] = True
            return True
        if "not sure" in text:
            st.session_state[_wizard_state_key(prefix, "destination_choice")] = "I'm not sure"
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = ["Malaysia"]
            st.session_state[_wizard_state_key(prefix, "willing_relocate")] = False
            return True
        return False

    if step == 8:
        if "scholar" in text:
            st.session_state[_wizard_state_key(prefix, "financing_mode")] = "scholarship"
            st.session_state[_wizard_state_key(prefix, "scholarship_needed")] = True
            st.session_state[_wizard_state_key(prefix, "need_work_part_time")] = False
            return True
        if "part" in text:
            st.session_state[_wizard_state_key(prefix, "financing_mode")] = "part_time"
            st.session_state[_wizard_state_key(prefix, "need_work_part_time")] = True
            st.session_state[_wizard_state_key(prefix, "scholarship_needed")] = False
            return True
        if "self" in text or "fund" in text:
            st.session_state[_wizard_state_key(prefix, "financing_mode")] = "self_fund"
            st.session_state[_wizard_state_key(prefix, "need_work_part_time")] = False
            st.session_state[_wizard_state_key(prefix, "scholarship_needed")] = False
            return True
        return False

    if step == 9:
        if "3 month" in text or "urgent" in text:
            st.session_state[_wizard_state_key(prefix, "pace_mode")] = "urgent"
            st.session_state[_wizard_state_key(prefix, "timeline_urgency")] = "urgent"
            st.session_state[_wizard_state_key(prefix, "family_constraints")] = "none"
            return True
        if "normal" in text:
            st.session_state[_wizard_state_key(prefix, "pace_mode")] = "normal"
            st.session_state[_wizard_state_key(prefix, "timeline_urgency")] = "normal"
            st.session_state[_wizard_state_key(prefix, "family_constraints")] = "none"
            return True
        if "home" in text or "near" in text:
            st.session_state[_wizard_state_key(prefix, "pace_mode")] = "near_home"
            st.session_state[_wizard_state_key(prefix, "timeline_urgency")] = "normal"
            st.session_state[_wizard_state_key(prefix, "family_constraints")] = "location"
            st.session_state[_wizard_state_key(prefix, "willing_relocate")] = False
            st.session_state[_wizard_state_key(prefix, "destination_choice")] = "Malaysia only"
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = ["Malaysia"]
            return True
        return False

    if step == 10:
        if "starting" in text or "starter" in text:
            st.session_state[_wizard_state_key(prefix, "preparedness_level")] = "starter"
            _set_preparedness_level(prefix, "starter")
            return True
        if "build" in text or "momentum" in text:
            st.session_state[_wizard_state_key(prefix, "preparedness_level")] = "building"
            _set_preparedness_level(prefix, "building")
            return True
        if "ready" in text:
            st.session_state[_wizard_state_key(prefix, "preparedness_level")] = "ready"
            _set_preparedness_level(prefix, "ready")
            return True
        return False

    return False


def render_wizard(prefix: str, language: str) -> tuple[bool, dict[str, Any] | None]:
    total_steps = 10
    step_key = _wizard_state_key(prefix, "step")
    journey_key = _wizard_state_key(prefix, "journey_started")
    if not st.session_state.get(journey_key):
        inject_interaction_js()
        _render_trust_phase(prefix, language)
        return False, None

    if step_key not in st.session_state:
        st.session_state[step_key] = 1

    step = st.session_state[step_key]
    inject_interaction_js()
    st.markdown(f"#### Guided Intake · Step {step}/{total_steps}")
    st.caption("Choose the option that best matches you. One short question at a time.")
    completion = _completion_percent(prefix) / 100
    render_meter("Profile completeness", completion, f"{int(round(completion * 100))}%")
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)

    if step == 1:
        st.chat_message("assistant").markdown("🎓 What specific program are you interested in?")
        st.caption("Choose the most specific option that matches your interest.")
        specific_programs = [
            "Digital Marketing & E-commerce",
            "Data Science & Analytics",
            "Artificial Intelligence & Machine Learning",
            "Biomedical Engineering",
            "Financial Technology (FinTech)",
            "Hospitality & Tourism Management",
            "Graphic Design & Multimedia",
            "Nursing & Allied Health",
            "Cybersecurity & Information Security",
            "Supply Chain & Logistics Management",
            "Renewable Energy Engineering",
            "Psychology & Counselling",
            "International Business",
            "Software Engineering",
            "Architecture & Urban Planning",
        ]
        selected_program = st.radio(
            "Select your specific program interest:",
            specific_programs,
            key=_wizard_state_key(prefix, "specific_program_interest"),
            help="This helps us match you with universities that offer this exact program.",
        )
        program_tags_map = {
            "Digital Marketing & E-commerce": ["Business", "Digital Marketing", "Creative"],
            "Data Science & Analytics": ["IT", "Data", "Engineering"],
            "Artificial Intelligence & Machine Learning": ["IT", "Data", "Engineering"],
            "Biomedical Engineering": ["Engineering", "Health", "Science"],
            "Financial Technology (FinTech)": ["Business", "IT", "Data"],
            "Hospitality & Tourism Management": ["Business", "Hospitality"],
            "Graphic Design & Multimedia": ["Creative", "Design", "Digital Marketing"],
            "Nursing & Allied Health": ["Health", "Science"],
            "Cybersecurity & Information Security": ["IT", "Engineering"],
            "Supply Chain & Logistics Management": ["Business", "Logistics"],
            "Renewable Energy Engineering": ["Engineering", "Science"],
            "Psychology & Counselling": ["Health", "Psychology"],
            "International Business": ["Business", "Economics"],
            "Software Engineering": ["IT", "Engineering"],
            "Architecture & Urban Planning": ["Engineering", "Design", "Creative"],
        }
        st.session_state[_wizard_state_key(prefix, "interest_tags")] = program_tags_map.get(selected_program, ["Business", "IT"])
        _privacy_reassurance("Specific program choice lets us return real universities and program pages, not generic pathways.")

    if step == 2:
        st.chat_message("assistant").markdown("📘 Which qualification do you currently have for university admission?")
        stage = _choice_triplet(
            prefix,
            "student_level",
            [
                ("SPM completed / results available", "SPM", "Use SPM entry requirements."),
                ("Diploma completed / CGPA available", "Diploma", "Use degree progression requirements."),
                ("Still waiting / not sure", "I'm not sure", "We apply safe defaults and recovery options."),
            ],
        )
        if stage == "I'm not sure":
            st.session_state[_wizard_state_key(prefix, "student_level")] = "SPM"
        _privacy_reassurance("Qualification stage determines valid entry routes for each university.")

    if step == 3:
        level_choice = st.session_state.get(_wizard_state_key(prefix, "student_level"), "SPM")
        level = "SPM" if level_choice == "I'm not sure" else level_choice
        st.chat_message("assistant").markdown("📊 Share your latest academic details so we can match entry requirements accurately.")

        if level == "SPM":
            credits = st.number_input(
                "Total SPM credits",
                min_value=0,
                max_value=10,
                value=int(st.session_state.get(_wizard_state_key(prefix, "spm_credits"), 5)),
                step=1,
                key=_wizard_state_key(prefix, "spm_credits_exact"),
            )
            st.session_state[_wizard_state_key(prefix, "spm_credits")] = int(credits)
            grade_options = ["A+", "A", "A-", "B+", "B", "C+", "C", "D", "E", "G", "Not sure yet"]
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                bm_grade = st.selectbox("BM grade", grade_options, index=6, key=_wizard_state_key(prefix, "subject_bm_input"))
            with g2:
                bi_grade = st.selectbox("English grade", grade_options, index=6, key=_wizard_state_key(prefix, "subject_english_input"))
            with g3:
                math_grade = st.selectbox("Math grade", grade_options, index=6, key=_wizard_state_key(prefix, "subject_math_input"))
            with g4:
                sci_grade = st.selectbox("Science grade", grade_options, index=6, key=_wizard_state_key(prefix, "subject_science_input"))
            add_math_grade = st.selectbox("Additional Math (if taken)", grade_options, index=10, key=_wizard_state_key(prefix, "subject_add_math_input"))
            subjects = {
                "bm": "C" if bm_grade == "Not sure yet" else bm_grade,
                "english": "C" if bi_grade == "Not sure yet" else bi_grade,
                "math": "C" if math_grade == "Not sure yet" else math_grade,
                "science": "C" if sci_grade == "Not sure yet" else sci_grade,
                "add_math": "C" if add_math_grade == "Not sure yet" else add_math_grade,
            }
            for subject, grade in subjects.items():
                st.session_state[_wizard_state_key(prefix, f"subject_{subject}")] = grade
        else:
            cgpa = st.slider(
                "Diploma CGPA",
                min_value=2.00,
                max_value=4.00,
                value=float(st.session_state.get(_wizard_state_key(prefix, "cgpa"), 2.8)),
                step=0.01,
                key=_wizard_state_key(prefix, "cgpa_exact"),
            )
            st.session_state[_wizard_state_key(prefix, "cgpa")] = round(float(cgpa), 2)
            diploma_field = st.selectbox(
                "Diploma field",
                ["IT / Computing", "Engineering", "Business", "Health Sciences", "Creative / Design", "Other"],
                key=_wizard_state_key(prefix, "diploma_field"),
            )
            st.session_state[_wizard_state_key(prefix, "diploma_field")] = diploma_field
        _privacy_reassurance("Exact grades/CGPA are used to check real university entry thresholds.")

    if step == 4:
        st.chat_message("assistant").markdown("🌍 Which countries and universities are you targeting?")
        country_options = ["Malaysia", "Australia", "UK", "Singapore", "New Zealand", "Ireland", "Canada"]
        if _wizard_state_key(prefix, "destination_tags") not in st.session_state:
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = ["Malaysia"]
        selected_countries = st.multiselect(
            "Target countries (select up to 3)",
            country_options,
            key=_wizard_state_key(prefix, "destination_tags"),
        )
        if len(selected_countries) > 3:
            selected_countries = selected_countries[:3]
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = selected_countries
            st.info("We kept your first 3 countries to keep recommendations focused.")
        if not selected_countries:
            selected_countries = ["Malaysia"]
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = selected_countries

        preferred_uni_options = [
            "Universiti Malaya",
            "UCSI University",
            "Taylor's University",
            "Monash University Malaysia",
            "RMIT University",
            "University of Leeds",
            "James Cook University Singapore",
            "Not sure yet",
        ]
        preferred_unis = st.multiselect(
            "Universities already on your mind (optional)",
            preferred_uni_options,
            key=_wizard_state_key(prefix, "preferred_universities"),
        )
        st.session_state[_wizard_state_key(prefix, "preferred_universities")] = [u for u in preferred_unis if u != "Not sure yet"]
        ranking_tier = st.radio(
            "Preferred QS ranking tier",
            ["Any", "Top 100", "Top 300", "Top 500"],
            key=_wizard_state_key(prefix, "target_ranking_tier"),
        )
        st.session_state[_wizard_state_key(prefix, "target_ranking_tier")] = ranking_tier
        st.session_state[_wizard_state_key(prefix, "destination_choice")] = "Malaysia only" if set(selected_countries) == {"Malaysia"} else "Open to overseas"
        st.session_state[_wizard_state_key(prefix, "willing_relocate")] = set(selected_countries) != {"Malaysia"}
        _privacy_reassurance("Country and QS targets narrow results to realistic institution options you can apply for.")

    if step == 5:
        st.chat_message("assistant").markdown("💸 What is your realistic study budget and financing plan?")
        monthly_budget = st.slider(
            "Monthly affordability (RM)",
            min_value=400,
            max_value=8000,
            value=int(st.session_state.get(_wizard_state_key(prefix, "budget_monthly"), 1400)),
            step=100,
            key=_wizard_state_key(prefix, "budget_monthly_slider"),
        )
        st.session_state[_wizard_state_key(prefix, "budget_monthly")] = monthly_budget
        if monthly_budget < 800:
            budget_range = "< RM 800"
        elif monthly_budget <= 2000:
            budget_range = "RM 800-2000"
        elif monthly_budget <= 5000:
            budget_range = "RM 2000-5000"
        else:
            budget_range = "RM 5000+"
        st.session_state[_wizard_state_key(prefix, "budget_range")] = budget_range

        financing_mode = st.radio(
            "Primary financing plan",
            ["Need scholarship", "Need part-time income", "Self-funded by family/savings"],
            key=_wizard_state_key(prefix, "financing_mode_radio"),
        )
        mode_map = {
            "Need scholarship": "scholarship",
            "Need part-time income": "part_time",
            "Self-funded by family/savings": "self_fund",
        }
        mode_value = mode_map.get(financing_mode, "self_fund")
        st.session_state[_wizard_state_key(prefix, "financing_mode")] = mode_value
        st.session_state[_wizard_state_key(prefix, "scholarship_needed")] = mode_value == "scholarship"
        st.session_state[_wizard_state_key(prefix, "need_work_part_time")] = mode_value == "part_time"
        _privacy_reassurance("Budget + financing keeps recommendations financially realistic.")

    if step == 6:
        st.chat_message("assistant").markdown("🗣️ What is your English evidence for admissions?")
        english_level = st.radio(
            "Current English readiness",
            ["Beginner", "Intermediate", "Advanced"],
            key=_wizard_state_key(prefix, "english_self"),
        )
        st.session_state[_wizard_state_key(prefix, "english_self")] = english_level
        i_col, t_col = st.columns(2)
        with i_col:
            ielts_value = st.number_input(
                "IELTS score (if available)",
                min_value=0.0,
                max_value=9.0,
                value=float(st.session_state.get(_wizard_state_key(prefix, "ielts_score"), 0.0) or 0.0),
                step=0.5,
                key=_wizard_state_key(prefix, "ielts_score_input"),
            )
        with t_col:
            toefl_value = st.number_input(
                "TOEFL score (if available)",
                min_value=0,
                max_value=120,
                value=int(st.session_state.get(_wizard_state_key(prefix, "toefl_score"), 0) or 0),
                step=1,
                key=_wizard_state_key(prefix, "toefl_score_input"),
            )
        st.session_state[_wizard_state_key(prefix, "ielts_score")] = float(ielts_value) if ielts_value > 0 else None
        st.session_state[_wizard_state_key(prefix, "toefl_score")] = int(toefl_value) if toefl_value > 0 else None
        proxy_score = None
        if ielts_value > 0:
            proxy_score = int(round((float(ielts_value) / 9.0) * 100))
        elif toefl_value > 0:
            proxy_score = int(round((int(toefl_value) / 120.0) * 100))
        st.session_state[_wizard_state_key(prefix, "english_test_score")] = proxy_score
        test_plan = st.radio(
            "English test status",
            ["Already have score", "Plan to take test within 3 months", "Not planning yet"],
            key=_wizard_state_key(prefix, "english_test_plan"),
        )
        st.session_state[_wizard_state_key(prefix, "english_test_plan")] = test_plan
        _privacy_reassurance("English evidence lets us filter programs by real IELTS/TOEFL entry requirements.")

    if step == 7:
        st.chat_message("assistant").markdown("📅 Which intake are you aiming for?")
        month_options = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        current_year = pd.Timestamp.utcnow().year
        intake_month = st.selectbox(
            "Target intake month",
            month_options,
            key=_wizard_state_key(prefix, "target_intake_month"),
        )
        intake_year = st.selectbox(
            "Target intake year",
            [current_year, current_year + 1, current_year + 2],
            key=_wizard_state_key(prefix, "target_intake_year"),
        )
        timeline_style = st.radio(
            "Application urgency",
            ["Need to apply in the next 3 months", "Can plan over 6-12 months", "Flexible timeline"],
            key=_wizard_state_key(prefix, "timeline_style"),
        )
        urgency_map = {
            "Need to apply in the next 3 months": ("urgent", "next_3_months"),
            "Can plan over 6-12 months": ("normal", "next_6_12_months"),
            "Flexible timeline": ("normal", "flexible_local"),
        }
        urgency, intake_window = urgency_map.get(timeline_style, ("normal", "next_6_12_months"))
        st.session_state[_wizard_state_key(prefix, "timeline_urgency")] = urgency
        st.session_state[_wizard_state_key(prefix, "intake_window")] = intake_window
        _privacy_reassurance("Intake target is used to prioritize programs with matching application windows.")

    if step == 8:
        st.chat_message("assistant").markdown("🏠 What constraints should we factor into your shortlist?")
        support_constraints = st.multiselect(
            "Select all that apply",
            [
                "No major constraints right now",
                "Need scholarship or PTPTN support",
                "Need part-time compatible study plan",
                "Need lower tuition options",
                "Family prefers I stay near home",
                "Prefer public universities",
            ],
            key=_wizard_state_key(prefix, "support_constraints"),
        )
        if "No major constraints right now" in support_constraints and len(support_constraints) > 1:
            support_constraints = ["No major constraints right now"]
            st.session_state[_wizard_state_key(prefix, "support_constraints")] = support_constraints
        relocate_pref = st.radio(
            "Relocation preference",
            ["Can relocate internationally", "Can relocate within Malaysia only", "Need to stay near current home area"],
            key=_wizard_state_key(prefix, "relocate_pref"),
        )
        st.session_state[_wizard_state_key(prefix, "scholarship_needed")] = "Need scholarship or PTPTN support" in support_constraints
        st.session_state[_wizard_state_key(prefix, "need_work_part_time")] = "Need part-time compatible study plan" in support_constraints
        if relocate_pref == "Can relocate internationally":
            st.session_state[_wizard_state_key(prefix, "willing_relocate")] = True
            st.session_state[_wizard_state_key(prefix, "family_constraints")] = "none"
        elif relocate_pref == "Can relocate within Malaysia only":
            st.session_state[_wizard_state_key(prefix, "willing_relocate")] = False
            st.session_state[_wizard_state_key(prefix, "family_constraints")] = "location"
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = ["Malaysia"]
        else:
            st.session_state[_wizard_state_key(prefix, "willing_relocate")] = False
            st.session_state[_wizard_state_key(prefix, "family_constraints")] = "location"
            st.session_state[_wizard_state_key(prefix, "destination_tags")] = ["Malaysia"]
        _privacy_reassurance("Constraints protect you from unrealistic recommendations.")

    if step == 9:
        st.chat_message("assistant").markdown("🎯 Final matching preferences before we generate recommendations.")
        priority_factors = st.multiselect(
            "What matters most to you?",
            [
                "Lower tuition cost",
                "Higher QS ranking",
                "Scholarship availability",
                "Strong employability outcome",
                "Multiple intakes per year",
                "Closer to home/family",
            ],
            default=st.session_state.get(_wizard_state_key(prefix, "priority_factors"), ["Lower tuition cost", "Strong employability outcome"]),
            key=_wizard_state_key(prefix, "priority_factors"),
        )
        institution_type = st.radio(
            "Institution type preference",
            ["Both public and private", "Public only", "Private only"],
            key=_wizard_state_key(prefix, "institution_type_pref"),
        )
        st.session_state[_wizard_state_key(prefix, "institution_type_pref")] = institution_type
        _privacy_reassurance("These priorities determine ranking order across matched university options.")

    if step == 10:
        st.chat_message("assistant").markdown("✅ Last step: tap the items you already have (choose all that apply).")
        st.caption("No stress. If you do not have an item yet, leave it unselected.")
        doc_options = [
            ("NRIC/Passport copy", "A basic ID document for application profiles."),
            ("Latest transcript/result slip", "Your SPM or Diploma transcript."),
            ("English test result (if any)", "IELTS/TOEFL report if available."),
            ("CV/Resume draft", "Useful for scholarship and admission support."),
            ("Personal statement draft", "Short motivation statement draft."),
            ("Portfolio/sample work", "Needed for creative/project-heavy programs."),
            ("Income/supporting docs", "Common for PTPTN/scholarship checks."),
            ("2 shortlisted universities", "Shows you are close to applying."),
        ]
        selected_docs = _multi_select_bubbles(prefix, "preparedness_checklist", doc_options, columns=2)
        ready_count = len(selected_docs)
        if ready_count >= 6:
            level, level_label = "ready", "Mostly ready"
        elif ready_count >= 3:
            level, level_label = "building", "Building momentum"
        else:
            level, level_label = "starter", "Just starting"
        st.session_state[_wizard_state_key(prefix, "preparedness_level")] = level
        st.markdown(
            f"<div class='teman-summary'><strong>Readiness check:</strong> {level_label} ({ready_count}/8 items ready)</div>",
            unsafe_allow_html=True,
        )
        _privacy_reassurance("These items help us personalize your 7-day and 30-day plan.")
    st.markdown("</div>", unsafe_allow_html=True)

    left, mid, right = st.columns([1, 1, 1])
    next_disabled = not _step_has_answer(prefix, step)
    with left:
        if st.button(
            t(language, "back"),
            disabled=step == 1,
            key=_wizard_state_key(prefix, "btn_back"),
            use_container_width=True,
            type="secondary",
        ):
            st.session_state[step_key] = max(1, step - 1)
            st.rerun()
    with mid:
        if step < total_steps:
            if st.button(
                t(language, "next"),
                key=_wizard_state_key(prefix, "btn_next"),
                disabled=next_disabled,
                use_container_width=True,
                type="primary",
            ):
                st.session_state[step_key] = min(total_steps, step + 1)
                st.rerun()
    with right:
        if step == total_steps:
            if st.button(
                "Generate Recommendations",
                key=_wizard_state_key(prefix, "btn_generate"),
                disabled=next_disabled,
                use_container_width=True,
                type="primary",
            ):
                return True, collect_inputs(prefix)

    if st.button(
        t(language, "reset"),
        key=_wizard_state_key(prefix, "btn_reset"),
        type="secondary",
    ):
        reset_wizard(prefix)
        st.rerun()

    return False, None


def _build_ninety_day_plan(results: dict[str, Any]) -> dict[str, list[str]]:
    seven_day = list(results.get("seven_day_actions", []))
    thirty_day = list(results.get("thirty_day_plan", []))
    combined = seven_day + thirty_day
    if not combined:
        combined = [
            "Clarify target course and shortlist 3 realistic institutions.",
            "Gather transcript, ID, and supporting records.",
            "Prepare English test and application timeline.",
            "Contact admissions teams and submit priority applications.",
        ]
    return {
        "Week 1-2": combined[:2],
        "Week 3-4": combined[2:4] if len(combined) > 2 else combined[:2],
        "Month 2": combined[4:6] if len(combined) > 4 else combined[:2],
        "Month 3": combined[6:8] if len(combined) > 6 else combined[:2],
    }


def _alumni_field_slug(tags: list[str]) -> str:
    normalized = " ".join(tags).lower()
    if "it" in normalized or "software" in normalized or "data" in normalized or "cyber" in normalized:
        return "it"
    if "engineering" in normalized:
        return "engineering"
    if "health" in normalized or "nursing" in normalized:
        return "health"
    if "creative" in normalized or "design" in normalized:
        return "creative"
    if "business" in normalized or "fintech" in normalized:
        return "business"
    return "general"


def _get_alumni_insights(snippets: dict[str, str], country: str, field_slug: str, limit: int = 3) -> list[dict[str, str]]:
    country_slug = country.lower().replace(" ", "")
    matches: list[dict[str, str]] = []
    for key, value in snippets.items():
        if not key.startswith("alumni_"):
            continue
        parts = key.split("_")
        if len(parts) < 4:
            continue
        _, key_country, key_field, _idx = parts[0], parts[1], parts[2], parts[3]
        if key_country not in {country_slug, "general"}:
            continue
        if key_field not in {field_slug, "general"}:
            continue
        source_type = "Alumni"
        insight_text = value
        if "::" in value:
            source_type, insight_text = value.split("::", 1)
        matches.append({"source_type": source_type.strip(), "text": insight_text.strip()})
    return matches[:limit]


def render_results_block(
    prefix: str,
    mode: str,
    inputs: dict[str, Any],
    results: dict[str, Any],
    language: str,
    current_user: dict[str, Any] | None = None,
    organization_id: str | None = None,
) -> None:
    snippets = get_content_snippets(language)
    disclaimers = [
        snippets.get("disclaimer_general", t(language, "disclaimer_general")),
        snippets.get("disclaimer_visa", t(language, "disclaimer_visa")),
        snippets.get("disclaimer_scholarship", t(language, "disclaimer_scholarship")),
    ]
    results["ninety_day_plan"] = _build_ninety_day_plan(results)

    st.markdown("### Readiness Snapshot")
    readiness = results.get("readiness", {})
    readiness_score = readiness.get("readiness_score", 0)
    breakdown = readiness.get("breakdown", {})
    st.markdown(f"**Overall readiness:** {readiness_score}/100")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.metric("Academic", f"{round(float(breakdown.get('academic', 0)), 1)}")
        st.caption("Baseline eligibility for entry requirements.")
    with p2:
        st.metric("English", f"{round(float(breakdown.get('english', 0)), 1)}")
        st.caption("Language readiness for admissions.")
    with p3:
        st.metric("Budget", f"{round(float(breakdown.get('budget', 0)), 1)}")
        st.caption("Affordability fit for selected options.")
    with p4:
        st.metric("Preparedness", f"{round(float(breakdown.get('preparedness', 0)), 1)}")
        st.caption("Documents and application readiness.")

    if results.get("no_match"):
        st.warning(t(language, "no_match"))
        recovery = results.get("recovery_plan", {})
        st.markdown("### Recovery Path")
        st.markdown("**Blocked inputs**")
        for item in recovery.get("blocked_inputs", []):
            st.write(f"- {item}")
        st.markdown("**Unlock steps**")
        for item in recovery.get("unlock_steps", []):
            st.write(f"- {item}")
        st.markdown("**Alternative local pathways**")
        for item in recovery.get("alternative_local_pathways", []):
            st.write(f"- {item['pathway_title']}: {item['summary']}")
    else:
        recommendations = results.get("recommendations", [])
        top_three = recommendations[:3]
        track_labels = [("Safe", "Low risk"), ("Target", "Balanced"), ("Aspirational", "Stretch")]
        st.markdown("### Top 3 Pathways")
        for idx, rec in enumerate(top_three):
            lane, risk = track_labels[idx] if idx < len(track_labels) else (f"Option {idx + 1}", "Balanced")
            with st.container(border=True):
                st.markdown(f"**{lane}: {rec.get('pathway_title')}**")
                st.markdown(
                    f"Fit score: **{rec.get('fit_score')}** | Cost: **{rec.get('cost_estimate_text')}** | Risk tag: **{risk}**"
                )
                st.caption(rec.get("pathway_summary", ""))

        st.markdown("### University Shortlist")
        top_universities = results.get("top_university_options", [])[:6]
        if not top_universities:
            st.info("No university shortlist generated yet.")
        for idx, option in enumerate(top_universities, start=1):
            with st.container(border=True):
                st.markdown(
                    f"**{idx}. {option.get('program_name')} @ {option.get('university_name')} ({option.get('country')})**"
                )
                st.write(
                    f"QS band: {_qs_tier_label(option.get('qs_overall_rank'))} | Tuition: {option.get('tuition_yearly_text', '-')}"
                )
                st.write(
                    f"Intake: {', '.join(option.get('intake_terms', [])) or '-'} | Timeline: {option.get('application_deadline_text') or '-'}"
                )
                if option.get("application_url"):
                    st.markdown(f"[Open application page]({option.get('application_url')})")
                if st.button(
                    "Save to Application Tracker",
                    key=_wizard_state_key(prefix, f"save_shortlist_{idx}_{option.get('program_code', 'program')}"),
                    type="secondary",
                ):
                    save_application_to_tracker(option, current_user, source="shortlist")
                    st.success("Saved to your application tracker.")

    st.markdown("### 90-day Action Plan")
    plan = results.get("ninety_day_plan", {})
    for phase, items in plan.items():
        with st.expander(phase, expanded=phase == "Week 1-2"):
            for item in items:
                st.write(f"- {item}")

    st.markdown("### Explainability")
    for rec in results.get("recommendations", [])[:3]:
        with st.expander(f"Pathway reasoning: {rec.get('pathway_title')}"):
            explain = rec.get("explanation", {})
            st.markdown("**Matched conditions**")
            for item in explain.get("matched_conditions", []):
                st.write(f"- {item}")
            st.markdown("**Borderline conditions**")
            for item in explain.get("borderline_conditions", []):
                st.write(f"- {item}")
            st.markdown("**Missing conditions**")
            for item in explain.get("missing_conditions", []):
                st.write(f"- {item}")
            st.caption(explain.get("ranking_reason", ""))
            for uni in rec.get("university_options", [])[:2]:
                st.markdown(f"**University match: {uni.get('program_name')} @ {uni.get('university_name')}**")
                for item in uni.get("fit_reasons", []):
                    st.write(f"- {item}")
                for item in uni.get("cautions", []):
                    st.write(f"- Caution: {item}")

    st.markdown("### Alumni Insight")
    destination = (inputs.get("destination_tags") or ["Malaysia"])[0]
    field_slug = _alumni_field_slug(inputs.get("interest_tags", []))
    insights = _get_alumni_insights(snippets, destination, field_slug, limit=3)
    if insights:
        for insight in insights:
            with st.container(border=True):
                st.caption(insight["source_type"])
                st.write(insight["text"])
    else:
        st.caption("No alumni snippet available for this combination yet.")

    st.markdown("### Consent, Save, and Export")
    render_disclaimers(language, snippets)
    st.caption("TemanEDU is guidance-only. Not a placement agency and no visa/scholarship guarantees.")

    pdf_bytes = build_pdf_report(profile=inputs, results=results, disclaimers=disclaimers)
    json_payload = {"inputs": inputs, "results": results, "meta": {"mode": mode, "language": language}}
    json_bytes = build_json_summary(json_payload)

    e1, e2 = st.columns(2)
    with e1:
        downloaded_pdf = st.download_button(
            label=t(language, "download_pdf"),
            data=pdf_bytes,
            file_name="temanedu_report.pdf",
            mime="application/pdf",
            key=_wizard_state_key(prefix, "download_pdf"),
            use_container_width=True,
        )
    with e2:
        downloaded_json = st.download_button(
            label=t(language, "download_json"),
            data=json_bytes,
            file_name="temanedu_session.json",
            mime="application/json",
            key=_wizard_state_key(prefix, "download_json"),
            use_container_width=True,
        )

    if downloaded_pdf:
        log_action(current_user["id"] if current_user else None, "report_downloaded", {"mode": mode})
    if downloaded_json:
        log_action(current_user["id"] if current_user else None, "json_export_downloaded", {"mode": mode})

    if mode == "student":
        consent_now = st.checkbox(
            t(language, "consent"),
            value=bool(inputs.get("consent_to_save")),
            key=_wizard_state_key(prefix, "consent_results"),
        )
        optional_email = st.text_input(
            "Optional email for saved access",
            value=inputs.get("optional_email") or "",
            key=_wizard_state_key(prefix, "optional_email_results"),
            placeholder="you@example.com",
        )
        inputs["consent_to_save"] = consent_now
        inputs["optional_email"] = optional_email.strip() or None
        st.session_state[_wizard_state_key(prefix, "inputs")] = inputs
        profile_key = _student_profile_state_key(prefix)
        profile = dict(st.session_state.get(profile_key, {}))
        profile["consent_to_save"] = consent_now
        profile["optional_email"] = optional_email.strip() or None
        st.session_state[profile_key] = profile

        if st.button(t(language, "save"), key=_wizard_state_key(prefix, "save_results")):
            if not inputs.get("consent_to_save"):
                st.error("Consent is required before saving.")
            else:
                user_id = current_user["id"] if current_user and current_user["role"] == "student" else None
                if not user_id:
                    user_id = get_or_create_student_user(inputs.get("optional_email"))
                session_id = persist_session(
                    inputs=inputs,
                    results=results,
                    mode="student",
                    language=language,
                    user_id=user_id,
                    organization_id=None,
                )
                log_action(user_id, "student_saved_results", {"session_id": session_id})
                st.success("Results saved.")

    if mode == "counselor" and organization_id and current_user:
        if not st.session_state.get(_wizard_state_key(prefix, "saved_once")):
            session_id = persist_session(
                inputs=inputs,
                results=results,
                mode="counselor",
                language=language,
                user_id=current_user["id"],
                organization_id=organization_id,
            )
            st.session_state[_wizard_state_key(prefix, "saved_once")] = True
            st.info(f"Counselor session saved: {session_id}")

def _qs_tier_label(rank: int | None) -> str:
    if not rank:
        return "Unranked"
    if rank <= 100:
        return "Top 100"
    if rank <= 300:
        return "Top 300"
    if rank <= 500:
        return "Top 500"
    return "Ranked 500+"


def _filter_program_catalog(programs: list[UniversityProgram], filters: dict[str, Any]) -> list[UniversityProgram]:
    query = str(filters.get("query") or "").strip().lower()
    countries = {c.lower() for c in filters.get("countries", [])}
    fields = {f.lower() for f in filters.get("fields", [])}
    qs_tier = filters.get("qs_tier", "All")
    tuition_cap = int(filters.get("tuition_cap") or 250000)
    scholarship_only = bool(filters.get("scholarship_only"))
    ielts_cap = filters.get("ielts_cap")

    output: list[UniversityProgram] = []
    for p in programs:
        if query:
            hay = " ".join(
                [p.university_name or "", p.program_name or "", p.country or "", " ".join(p.field_tags or [])]
            ).lower()
            if query not in hay:
                continue
        if countries and p.country.lower() not in countries:
            continue
        if fields:
            program_fields = {item.lower() for item in (p.field_tags or [])}
            if not (fields & program_fields):
                continue
        rank = p.qs_overall_rank
        if qs_tier == "Top 100" and (not rank or rank > 100):
            continue
        if qs_tier == "Top 300" and (not rank or rank > 300):
            continue
        if qs_tier == "Top 500" and (not rank or rank > 500):
            continue
        if qs_tier == "Ranked only" and not rank:
            continue
        if qs_tier == "Unranked only" and rank:
            continue
        if p.tuition_yearly_min_myr and p.tuition_yearly_min_myr > tuition_cap:
            continue
        if scholarship_only and not p.ptptn_eligible:
            continue
        if ielts_cap is not None and p.ielts_min and float(p.ielts_min) > float(ielts_cap):
            continue
        output.append(p)

    output.sort(key=lambda item: ((item.qs_overall_rank or 9999), item.university_name))
    return output


def _render_profile_section(prefix: str, user: dict[str, Any] | None) -> None:
    st.markdown("### Student Profile")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Full name", key=_wizard_state_key(prefix, "profile_name"))
        st.text_input(
            "Email",
            value=(user.get("email") if user and user.get("email") else st.session_state.get(_wizard_state_key(prefix, "profile_email"), "")),
            key=_wizard_state_key(prefix, "profile_email"),
        )
    with col2:
        st.text_input("Contact number", key=_wizard_state_key(prefix, "profile_contact"))
        st.selectbox("Target ranking tier", ["Any", "Top 100", "Top 300", "Top 500"], key=_wizard_state_key(prefix, "profile_ranking_tier"))

    saved_inputs = st.session_state.get(_wizard_state_key(prefix, "inputs"), {})
    if saved_inputs:
        st.markdown("#### Academic snapshot from latest pathway session")
        st.write(
            f"- Level: {saved_inputs.get('student_level', '-')}\n"
            f"- Interests: {', '.join(saved_inputs.get('interest_tags', [])) or '-'}\n"
            f"- Specific program: {saved_inputs.get('specific_program_interest', '-')}\n"
            f"- Budget (monthly): RM {saved_inputs.get('budget_monthly', '-')}\n"
            f"- Timeline window: {saved_inputs.get('intake_window', '-')}"
        )


def _render_course_finder(prefix: str, current_user: dict[str, Any] | None) -> None:
    st.markdown("### Course & University Finder")
    programs = fetch_university_programs()
    if not programs:
        st.warning("No university catalog entries found.")
        return

    all_countries = sorted({p.country for p in programs if p.country})
    all_fields = sorted({tag for p in programs for tag in (p.field_tags or [])})
    budget_default = int(st.session_state.get(_wizard_state_key(prefix, "budget_monthly")) or 5000) * 12
    max_cap = max([p.tuition_yearly_max_myr or p.tuition_yearly_min_myr or 0 for p in programs] + [120000])
    tuition_default = min(max_cap, max(25000, budget_default))

    q_col, c_col, f_col = st.columns([2.4, 1.4, 1.4])
    with q_col:
        query = st.text_input("Search university or program", key=_wizard_state_key(prefix, "finder_query"), placeholder="e.g., Data Science, University of Leeds")
    with c_col:
        countries = st.multiselect("Country", all_countries, key=_wizard_state_key(prefix, "finder_countries"))
    with f_col:
        fields = st.multiselect("Program field", all_fields, key=_wizard_state_key(prefix, "finder_fields"))

    a_col, b_col, d_col, e_col = st.columns([1.2, 1.6, 1.4, 1.4])
    with a_col:
        qs_tier = st.selectbox("QS filter", ["All", "Top 100", "Top 300", "Top 500", "Ranked only", "Unranked only"], key=_wizard_state_key(prefix, "finder_qs"))
    with b_col:
        tuition_cap = st.slider("Max yearly tuition (MYR)", 10000, max_cap, tuition_default, step=1000, key=_wizard_state_key(prefix, "finder_tuition_cap"))
    with d_col:
        scholarship_only = st.checkbox("PTPTN/scholarship-friendly", key=_wizard_state_key(prefix, "finder_scholarship_only"))
    with e_col:
        ielts_cap = st.selectbox("IELTS requirement", ["Any", "<= 6.0", "<= 6.5", "<= 7.0"], key=_wizard_state_key(prefix, "finder_ielts_cap"))

    ielts_value = None
    if ielts_cap != "Any":
        ielts_value = float(ielts_cap.replace("<= ", ""))

    filtered = _filter_program_catalog(
        programs,
        {
            "query": query,
            "countries": countries,
            "fields": fields,
            "qs_tier": qs_tier,
            "tuition_cap": tuition_cap,
            "scholarship_only": scholarship_only,
            "ielts_cap": ielts_value,
        },
    )

    st.caption(f"{len(filtered)} program(s) matched your filters.")
    preview_rows = []
    for item in filtered[:40]:
        preview_rows.append(
            {
                "University": item.university_name,
                "Program": item.program_name,
                "Country": item.country,
                "QS": item.qs_overall_rank or "-",
                "Tier": _qs_tier_label(item.qs_overall_rank),
                "Tuition (MYR/year)": f"{item.tuition_yearly_min_myr or '-'} - {item.tuition_yearly_max_myr or '-'}",
                "PTPTN": "Yes" if item.ptptn_eligible else "No",
            }
        )
    if preview_rows:
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)

    st.markdown("#### Actionable options")
    for idx, p in enumerate(filtered[:12], start=1):
        exp_title = f"{idx}. {p.program_name} @ {p.university_name} ({p.country})"
        with st.expander(exp_title):
            st.write(f"QS rank tier: {_qs_tier_label(p.qs_overall_rank)} (rank: {p.qs_overall_rank or 'N/A'})")
            st.write(f"Intakes: {', '.join(p.intake_terms or []) or '-'}")
            st.write(f"Application timing: {p.application_deadline_text or '-'}")
            st.write(f"Tuition: RM {p.tuition_yearly_min_myr or '-'} - {p.tuition_yearly_max_myr or '-'} per year")
            st.write(f"PTPTN eligible: {'Yes' if p.ptptn_eligible else 'No'}")
            if p.application_url:
                st.markdown(f"[Apply / Program page]({p.application_url})")
            if p.contact_email:
                st.write(f"Admissions contact: {p.contact_email}")
            option = {
                "university_name": p.university_name,
                "program_name": p.program_name,
                "country": p.country,
                "intake_terms": p.intake_terms or [],
                "application_deadline_text": p.application_deadline_text,
                "qs_overall_rank": p.qs_overall_rank,
                "tuition_yearly_text": f"RM {p.tuition_yearly_min_myr or '-'} - {p.tuition_yearly_max_myr or '-'} per year",
                "application_url": p.application_url,
                "contact_email": p.contact_email,
            }
            if st.button("Save to Application Tracker", key=_wizard_state_key(prefix, f"finder_save_{p.program_code}"), type="secondary"):
                save_application_to_tracker(option, current_user, source="course_finder")
                st.success("Saved to tracker.")


def _render_recommendation_section(prefix: str, current_user: dict[str, Any] | None) -> None:
    st.markdown("### Personalized Matches")
    saved_results = st.session_state.get(_wizard_state_key(prefix, "results"), {})
    top_universities = saved_results.get("top_university_options", []) if saved_results else []
    if top_universities:
        for idx, option in enumerate(top_universities[:6], start=1):
            st.markdown(
                f"**{idx}. {option.get('program_name')} @ {option.get('university_name')} ({option.get('country')})**  \n"
                f"Match score: {option.get('match_score', 0)} | Tuition: {option.get('tuition_yearly_text', '-')}"
            )
            if option.get("application_url"):
                st.markdown(f"[Application link]({option.get('application_url')})")
            if st.button("Save match", key=_wizard_state_key(prefix, f"rec_save_{idx}_{option.get('program_code', 'x')}"), type="secondary"):
                save_application_to_tracker(option, current_user, source="personalized_match")
                st.success("Saved to tracker.")
    else:
        st.info("Complete Student Pathway once to unlock personalized matches.")

    programs = fetch_university_programs()
    if programs:
        tag_counter: Counter[str] = Counter()
        for p in programs:
            for tag in (p.field_tags or []):
                tag_counter[tag] += 1
        top_tags = ", ".join([f"{name} ({count})" for name, count in tag_counter.most_common(5)])
        st.markdown("### Trending Program Areas")
        st.write(top_tags or "No trend data.")

        st.markdown("### Scholarship-Friendly Opportunities")
        scholarship_rows = [p for p in programs if p.ptptn_eligible][:8]
        for p in scholarship_rows:
            st.write(f"- {p.program_name} @ {p.university_name} ({p.country})")


def _render_application_tracker(prefix: str, current_user: dict[str, Any] | None) -> None:
    st.markdown("### Application Tracker")
    tracked = fetch_tracked_applications(current_user)
    if not tracked:
        st.info("No tracked applications yet. Save options from recommendations or course finder.")
        return

    deadline_rows = [item for item in tracked if item.deadline_text]
    if deadline_rows:
        st.markdown("#### Upcoming Application Deadlines")
        for item in deadline_rows[:5]:
            st.write(f"- {item.program_name} @ {item.university_name}: {item.deadline_text}")

    for item in tracked:
        title = f"{item.program_name} @ {item.university_name} ({item.country})"
        with st.expander(title):
            st.write(f"Status: {item.status}")
            st.write(f"Intake: {item.intake_text or '-'}")
            st.write(f"Deadline: {item.deadline_text or '-'}")
            st.write(f"QS rank: {item.qs_rank or 'N/A'}")
            st.write(f"Tuition: {item.tuition_text or '-'}")
            if item.application_url:
                st.markdown(f"[Open application page]({item.application_url})")
            if item.contact_email:
                st.write(f"Admissions contact: {item.contact_email}")

            status_key = _wizard_state_key(prefix, f"tracker_status_{item.id}")
            note_key = _wizard_state_key(prefix, f"tracker_notes_{item.id}")
            new_status = st.selectbox(
                "Update status",
                ["saved", "in_progress", "submitted", "accepted", "rejected"],
                index=["saved", "in_progress", "submitted", "accepted", "rejected"].index(item.status),
                key=status_key,
            )
            notes = st.text_area("Notes", value=item.notes or "", key=note_key, height=80)
            if st.button("Save status", key=_wizard_state_key(prefix, f"tracker_update_{item.id}"), type="secondary"):
                update_application_status(str(item.id), new_status, current_user, notes=notes)
                st.success("Application tracker updated.")
                st.rerun()


def render_student_dashboard_page(language: str, user: dict[str, Any] | None) -> None:
    st.markdown(
        "<div class='chat-page-card'><h3>IDP-Style Student Dashboard</h3><p>Track profile, search universities, and manage applications in one place.</p></div>",
        unsafe_allow_html=True,
    )
    if st.button("Start / Continue Pathway Assessment", key=_wizard_state_key("student", "goto_pathway"), type="primary"):
        _navigate(language=language, access="Student", student_page="student-pathway")
    tabs = st.tabs(["Profile", "Course Finder", "Recommendations", "Application Tracker"])
    with tabs[0]:
        _render_profile_section(prefix="student", user=user)
    with tabs[1]:
        _render_course_finder(prefix="student", current_user=user)
    with tabs[2]:
        _render_recommendation_section(prefix="student", current_user=user)
    with tabs[3]:
        _render_application_tracker(prefix="student", current_user=user)


def _sync_student_profile_to_state(prefix: str, profile: dict[str, Any]) -> None:
    sync_fields = [
        "budget_monthly",
        "interest_tags",
        "destination_tags",
        "specific_program_interest",
        "target_ranking_tier",
        "student_level",
    ]
    for field in sync_fields:
        st.session_state[_wizard_state_key(prefix, field)] = profile.get(field)


def render_student_chat_page(language: str, user: dict[str, Any] | None) -> None:
    inject_interaction_js()
    st.markdown(
        """
        <div class="chat-page-card">
            <h3>Student Chat</h3>
            <p>Answer one question at a time. TemanEDU will generate deterministic, explainable pathways and university options.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    generated, intake = render_chat(prefix="student", language=language)
    if generated and intake:
        rules = fetch_rules(intake["student_level"])
        university_programs = fetch_university_programs()
        results = evaluate_rules(rules, intake, top_n=5, university_programs=university_programs)
        st.session_state[_wizard_state_key("student", "results")] = results
        st.session_state[_wizard_state_key("student", "inputs")] = intake
        _sync_student_profile_to_state("student", st.session_state.get(_student_profile_state_key("student"), {}))
        _navigate(language=language, access="Student", student_page="results")

    if st.session_state.get(_wizard_state_key("student", "results")):
        if st.button("View latest results", key=_wizard_state_key("student", "view_results"), type="secondary"):
            _navigate(language=language, access="Student", student_page="results")


def render_student_results_page(language: str, user: dict[str, Any] | None) -> None:
    results = st.session_state.get(_wizard_state_key("student", "results"))
    inputs = st.session_state.get(_wizard_state_key("student", "inputs"))
    if not results or not inputs:
        st.info("No results yet. Complete the student chat first.")
        if st.button("Go to Student Chat", key="goto_student_chat_from_results", type="primary"):
            _navigate(language=language, access="Student", student_page="student-chat")
        return
    render_results_block(
        prefix="student",
        mode="student",
        inputs=inputs,
        results=results,
        language=language,
        current_user=user,
        organization_id=None,
    )
    if st.button("Refine my answers", key="refine_answers_from_results", type="secondary"):
        _navigate(language=language, access="Student", student_page="student-chat")


def run_assessment(prefix: str, mode: str, language: str, user: dict[str, Any] | None = None, organization_id: str | None = None) -> None:
    generated, intake = render_wizard(prefix, language)

    if generated and intake:
        rules = fetch_rules(intake["student_level"])
        university_programs = fetch_university_programs()
        results = evaluate_rules(rules, intake, top_n=5, university_programs=university_programs)
        st.session_state[_wizard_state_key(prefix, "results")] = results
        st.session_state[_wizard_state_key(prefix, "inputs")] = intake
        st.session_state.pop(_wizard_state_key(prefix, "saved_once"), None)
        st.session_state[_wizard_state_key(prefix, "show_more_options")] = False

    saved_results = st.session_state.get(_wizard_state_key(prefix, "results"))
    saved_inputs = st.session_state.get(_wizard_state_key(prefix, "inputs"))

    if saved_results and saved_inputs:
        render_results_block(
            prefix=prefix,
            mode=mode,
            inputs=saved_inputs,
            results=saved_results,
            language=language,
            current_user=user,
            organization_id=organization_id,
        )


def counselor_past_sessions(org_id: str) -> pd.DataFrame:
    with db_session() as db:
        sessions = db.scalars(
            select(SessionModel)
            .where(SessionModel.organization_id == uuid.UUID(org_id), SessionModel.mode == "counselor")
            .order_by(SessionModel.created_at.desc())
        ).all()

        rows = []
        for sess in sessions:
            rec = db.scalar(
                select(Recommendation)
                .where(Recommendation.session_id == sess.id)
                .order_by(Recommendation.created_at.desc())
            )
            top_pathway = "Recovery Plan"
            readiness = None
            if rec and rec.results_json:
                if not rec.results_json.get("no_match") and rec.results_json.get("recommendations"):
                    top_pathway = rec.results_json["recommendations"][0]["pathway_title"]
                readiness = rec.results_json.get("readiness", {}).get("readiness_score")
            rows.append(
                {
                    "session_id": str(sess.id),
                    "created_at": sess.created_at,
                    "language": sess.language,
                    "top_pathway": top_pathway,
                    "readiness_score": readiness,
                }
            )

        return pd.DataFrame(rows)


def _counter_chart(values: list[str], top_n: int = 10) -> pd.Series:
    count = Counter(values)
    return pd.Series(dict(count.most_common(top_n)))


def counselor_analytics(org_id: str) -> dict[str, pd.Series]:
    interests: list[str] = []
    gaps: list[str] = []
    budgets: list[str] = []
    pathways: list[str] = []

    with db_session() as db:
        sessions = db.scalars(
            select(SessionModel)
            .where(SessionModel.organization_id == uuid.UUID(org_id), SessionModel.mode == "counselor")
        ).all()

        for sess in sessions:
            session_input = db.get(SessionInput, sess.id)
            recommendation = db.scalar(select(Recommendation).where(Recommendation.session_id == sess.id))

            if session_input and session_input.inputs_json:
                payload = session_input.inputs_json
                interests.extend(payload.get("interest_tags", []))
                budget = int(payload.get("budget_monthly") or 0)
                if budget < 800:
                    budgets.append("<RM800")
                elif budget <= 2000:
                    budgets.append("RM800-2000")
                elif budget <= 5000:
                    budgets.append("RM2000-5000")
                else:
                    budgets.append(">RM5000")

            if recommendation and recommendation.results_json:
                rs = recommendation.results_json
                if rs.get("no_match"):
                    gaps.extend(rs.get("recovery_plan", {}).get("blocked_inputs", []))
                    pathways.append("Recovery Plan")
                for rec in rs.get("recommendations", []):
                    gaps.extend(rec.get("readiness_gaps", []))
                    pathways.append(rec.get("pathway_title", "Unknown"))

    return {
        "common_interests": _counter_chart(interests),
        "common_gaps": _counter_chart(gaps),
        "budget_distribution": _counter_chart(budgets),
        "pathway_distribution": _counter_chart(pathways),
    }


def render_counselor_dashboard(language: str, inline_login: bool = False) -> None:
    user = render_login("counselor", inline=inline_login)
    if not user:
        st.info("Counselor login required.")
        return

    orgs = get_user_organizations(user["id"])
    if not orgs:
        st.error("No organizations linked to this counselor account.")
        return

    org_map = {f"{item['name']} ({item['role_in_org']})": item["id"] for item in orgs}
    selected_label = st.selectbox("Organization", list(org_map.keys()))
    selected_org_id = org_map[selected_label]

    tab1, tab2, tab3 = st.tabs(["Run Session", "Past Sessions", "Analytics"])

    with tab1:
        st.subheader("Counselor Mode Intake")
        run_assessment(prefix="counselor", mode="counselor", language=language, user=user, organization_id=selected_org_id)

    with tab2:
        st.subheader("Past Sessions")
        df = counselor_past_sessions(selected_org_id)
        if df.empty:
            st.write("No sessions yet.")
        else:
            st.dataframe(df, use_container_width=True)
            session_id = st.selectbox("Select session to export", df["session_id"].tolist())
            with db_session() as db:
                rec = db.scalar(select(Recommendation).where(Recommendation.session_id == uuid.UUID(session_id)))
                inp = db.get(SessionInput, uuid.UUID(session_id))
            if rec and inp:
                snippets = get_content_snippets(language)
                disclaimers = [
                    snippets.get("disclaimer_general", t(language, "disclaimer_general")),
                    snippets.get("disclaimer_visa", t(language, "disclaimer_visa")),
                    snippets.get("disclaimer_scholarship", t(language, "disclaimer_scholarship")),
                ]
                st.download_button(
                    "Export Session PDF",
                    data=build_pdf_report(inp.inputs_json, rec.results_json, disclaimers),
                    file_name=f"counselor_session_{session_id}.pdf",
                    mime="application/pdf",
                )
                st.download_button(
                    "Export Session JSON",
                    data=build_json_summary({"inputs": inp.inputs_json, "results": rec.results_json}),
                    file_name=f"counselor_session_{session_id}.json",
                    mime="application/json",
                )

    with tab3:
        st.subheader("Organization Analytics")
        charts = counselor_analytics(selected_org_id)
        for title, series in charts.items():
            st.markdown(f"**{title.replace('_', ' ').title()}**")
            if series.empty:
                st.write("No data yet.")
            else:
                st.bar_chart(series)


def admin_rule_management(user: dict[str, Any]) -> None:
    with db_session() as db:
        rules = db.scalars(select(Rule).order_by(Rule.updated_at.desc())).all()

    if not rules:
        st.warning("No rules found.")
        return

    df = pd.DataFrame(
        [
            {
                "rule_id": r.rule_id,
                "active": r.active,
                "student_level": r.student_level,
                "priority": r.priority_weight,
                "pathway_title": r.pathway_title,
            }
            for r in rules
        ]
    )
    st.dataframe(df, use_container_width=True)

    target_rule_id = st.selectbox("Select rule", df["rule_id"].tolist(), key="admin_edit_rule_id")
    target_rule = next(r for r in rules if r.rule_id == target_rule_id)

    with st.form("admin_update_rule"):
        active = st.checkbox("Active", value=target_rule.active)
        title = st.text_input("Pathway title", value=target_rule.pathway_title)
        summary = st.text_area("Pathway summary", value=target_rule.pathway_summary)
        priority = st.number_input("Priority weight", value=int(target_rule.priority_weight), step=1)
        submit_update = st.form_submit_button("Update Rule")

    if submit_update:
        with db_session() as db:
            rule = db.scalar(select(Rule).where(Rule.rule_id == target_rule_id))
            if rule:
                rule.active = active
                rule.pathway_title = title
                rule.pathway_summary = summary
                rule.priority_weight = int(priority)
                db.add(
                    AuditLog(
                        user_id=uuid.UUID(user["id"]),
                        action="rule_updated",
                        details_json={"rule_id": target_rule_id},
                    )
                )
        st.success("Rule updated.")
        st.rerun()

    st.markdown("### Create New Rule")
    with st.form("admin_create_rule"):
        new_rule_id = st.text_input("Rule ID")
        new_level = st.selectbox("Student level", ["SPM", "Diploma"])
        new_interests = st.text_input("Interest tags (pipe-separated)", value="Business|IT")
        new_destinations = st.text_input("Destination tags (pipe-separated)", value="Malaysia")
        new_title = st.text_input("Pathway title", key="new_rule_title")
        new_summary = st.text_area("Pathway summary", key="new_rule_summary")
        submit_create = st.form_submit_button("Create Rule")

    if submit_create:
        payload = {
            "rule_id": new_rule_id,
            "active": True,
            "student_level": new_level,
            "interest_tags": [x.strip() for x in new_interests.split("|") if x.strip()],
            "destination_tags": [x.strip() for x in new_destinations.split("|") if x.strip()],
            "min_spm_credits": 5 if new_level == "SPM" else None,
            "required_subjects_json": {"english": "C"} if new_level == "SPM" else {},
            "min_cgpa": 2.8 if new_level == "Diploma" else None,
            "budget_min": 800,
            "budget_max": 5000,
            "english_min": "Intermediate",
            "constraints_json": {"work_part_time_ok": True},
            "pathway_title": new_title,
            "pathway_summary": new_summary,
            "cost_estimate_text": "RM 800-5000/month",
            "visa_note": "General note: verify latest official visa/work requirements.",
            "scholarship_likelihood": "Medium",
            "readiness_gaps": ["English improvement", "CV preparation"],
            "next_steps": "Shortlist institutions and prepare documents.",
            "priority_weight": 1,
        }
        with db_session() as db:
            existing = db.scalar(select(Rule).where(Rule.rule_id == new_rule_id))
            if existing:
                st.error("Rule ID already exists.")
            else:
                db.add(Rule(**payload))
                db.add(
                    AuditLog(
                        user_id=uuid.UUID(user["id"]),
                        action="rule_created",
                        details_json={"rule_id": new_rule_id},
                    )
                )
                st.success("Rule created.")
                st.rerun()


def admin_csv_import(user: dict[str, Any]) -> None:
    st.markdown("Upload `logic_table.csv` and preview diff before upsert.")
    file = st.file_uploader("CSV file", type=["csv"], key="admin_csv_file")

    if file is not None:
        csv_text = file.getvalue().decode("utf-8")
        try:
            rows = load_rules_from_csv(csv_text)
            st.session_state["admin_csv_rows"] = rows
            with db_session() as db:
                diff = preview_diff(db, rows)
            st.write(f"Preview diff: {diff['insert']} insert(s), {diff['update']} update(s)")
            st.dataframe(pd.DataFrame(rows).head(20), use_container_width=True)
        except Exception as exc:
            st.error(f"CSV validation failed: {exc}")
            st.session_state.pop("admin_csv_rows", None)

    if st.button("Upsert CSV into rules"):
        rows = st.session_state.get("admin_csv_rows")
        if not rows:
            st.warning("No validated rows ready for upsert.")
            return
        with db_session() as db:
            result = upsert_rules(db, rows, actor_user_id=user["id"], source="admin_csv")
        st.success(f"Upsert complete. Inserted: {result['inserted']}, Updated: {result['updated']}")
        st.rerun()


def admin_content_management(user: dict[str, Any]) -> None:
    with db_session() as db:
        rows = db.scalars(select(ContentSnippet).order_by(ContentSnippet.key, ContentSnippet.language)).all()

    if rows:
        st.dataframe(
            pd.DataFrame(
                [{"key": r.key, "language": r.language, "value": r.value} for r in rows]
            ),
            use_container_width=True,
        )

    with st.form("content_form"):
        key = st.text_input("Key", value="disclaimer_general")
        language = st.selectbox("Language", ["en", "bm"])
        value = st.text_area("Value")
        submit = st.form_submit_button("Save Snippet")

    if submit:
        with db_session() as db:
            existing = db.scalar(
                select(ContentSnippet).where(ContentSnippet.key == key, ContentSnippet.language == language)
            )
            if existing:
                existing.value = value
            else:
                db.add(ContentSnippet(key=key, language=language, value=value))
            db.add(
                AuditLog(
                    user_id=uuid.UUID(user["id"]),
                    action="content_snippet_upsert",
                    details_json={"key": key, "language": language},
                )
            )
        get_content_snippets.clear()
        st.success("Content snippet saved.")
        st.rerun()


def admin_system_analytics() -> None:
    with db_session() as db:
        total_sessions = db.scalar(select(func.count()).select_from(SessionModel)) or 0
        total_recommendations = db.scalar(select(func.count()).select_from(Recommendation)) or 0
        download_count = db.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == "report_downloaded")
        ) or 0
        save_count = db.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action.in_(["results_saved", "student_saved_results"]))
        ) or 0

        rec_rows = db.scalars(select(Recommendation)).all()

    pathway_counter: Counter[str] = Counter()
    no_match = 0
    for rec in rec_rows:
        payload = rec.results_json
        if payload.get("no_match"):
            no_match += 1
            pathway_counter["Recovery Plan"] += 1
        else:
            for item in payload.get("recommendations", []):
                pathway_counter[item.get("pathway_title", "Unknown")] += 1

    st.metric("Total sessions", int(total_sessions))
    st.metric("Recommendation records", int(total_recommendations))
    st.metric("Report downloads", int(download_count))
    st.metric("Save events (proxy conversion)", int(save_count))

    no_match_rate = (no_match / len(rec_rows) * 100.0) if rec_rows else 0.0
    st.metric("No-match rate", f"{no_match_rate:.1f}%")

    if pathway_counter:
        st.markdown("**Top pathways served**")
        st.bar_chart(pd.Series(dict(pathway_counter.most_common(10))))


def admin_university_catalog() -> None:
    with db_session() as db:
        programs = db.scalars(select(UniversityProgram).order_by(UniversityProgram.country, UniversityProgram.university_name)).all()
        sources = db.scalars(select(ExternalDataSource).where(ExternalDataSource.active.is_(True)).order_by(ExternalDataSource.source_code)).all()

    st.markdown("#### Integrated data sources")
    for src in sources:
        st.write(f"- {src.source_code}: {src.base_url} ({src.update_frequency})")

    if not programs:
        st.warning("No university programs in catalog.")
        return

    df = pd.DataFrame(
        [
            {
                "program_code": p.program_code,
                "university_name": p.university_name,
                "country": p.country,
                "program_name": p.program_name,
                "program_level": p.program_level,
                "ptptn_eligible": p.ptptn_eligible,
                "application_url": p.application_url,
            }
            for p in programs
        ]
    )
    st.metric("Total actionable programs", len(df))
    st.dataframe(df, use_container_width=True)


def render_admin_dashboard(language: str, inline_login: bool = False) -> None:
    user = render_login("admin", inline=inline_login)
    if not user:
        st.info("Admin login required.")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Rule Management", "CSV Upload", "Content", "System Analytics", "University Catalog"])

    with tab1:
        admin_rule_management(user)

    with tab2:
        admin_csv_import(user)

    with tab3:
        admin_content_management(user)

    with tab4:
        admin_system_analytics()

    with tab5:
        admin_university_catalog()


def _navigate(language: str, access: str = "Student", student_page: str | None = None) -> None:
    st.session_state["language"] = language
    st.session_state["access_mode"] = access
    if student_page == "student-pathway":
        student_page = "student-chat"
    if access == "Student" and student_page in STUDENT_PAGES:
        st.session_state["student_page"] = student_page
    _query_set(
        language=language,
        access=access,
        student_page=student_page if access == "Student" and student_page else None,
        chat_q=st.session_state.get("student_chat_edit_question") if access == "Student" and student_page == "student-chat" else None,
    )
    st.rerun()


@st.cache_data(show_spinner=False)
def _logo_data_uri() -> str | None:
    logo_path = Path(__file__).resolve().parent / "assets" / "temanedu_logo.png"
    if not logo_path.exists():
        return None
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _inject_base_page_css() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display: none !important;}
        .block-container {max-width: min(1380px, 95vw) !important; padding-top: 0.45rem !important; padding-bottom: 2rem !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_top_nav(language: str, active_page: str | None, active_access: str = "Student") -> None:
    links = [
        ("student-chat", "Student Chat", "Student"),
        ("results", "Results", "Student"),
        ("course-finder", "Course Finder", "Student"),
        ("application-tracker", "Tracker", "Student"),
        ("about", "About Us", "Student"),
    ]

    home_href = f"?language={language}&access=Student&student_page=student-chat"
    logo_uri = _logo_data_uri()
    if logo_uri:
        logo_html = (
            f"<div class='nav-logo-box'>"
            f"<a href='{home_href}' class='nav-brand nav-logo-link'>"
            f"<img src='{logo_uri}' alt='TemanEDU logo' class='top-logo-img' />"
            f"<span class='top-logo-wordmark'><span class='brand-teman'>Teman</span><span class='brand-edu'>EDU</span></span>"
            f"</a>"
            f"</div>"
        )
    else:
        logo_html = (
            f"<div class='nav-logo-box'>"
            f"<a href='{home_href}' class='nav-brand nav-logo-link'>"
            f"<span class='top-logo-wordmark'><span class='brand-teman'>Teman</span><span class='brand-edu'>EDU</span></span>"
            f"</a>"
            f"</div>"
        )

    nav_shell = st.container(border=True)
    with nav_shell:
        left, right = st.columns([1.45, 5.4], gap="small")
        with left:
            st.markdown(logo_html, unsafe_allow_html=True)
        with right:
            nav_cols = st.columns(len(links), gap="small")
            for idx, (page, label, access) in enumerate(links):
                is_active = access == active_access and page == active_page
                with nav_cols[idx]:
                    if st.button(
                        label,
                        key=f"top_nav_btn_{idx}_{access}_{page or 'root'}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                    ):
                        _navigate(language=language, access=access, student_page=page)


def _render_left_sidebar(language: str, active_page: str, user: dict[str, Any] | None) -> None:
    status = f"{user['email']} • logged in" if user else "Anonymous • Not logged in"
    menu = [
        ("dashboard", "Student Dashboard", "Student"),
        ("student-pathway", "Student Pathway", "Student"),
        ("course-finder", "Course Finder", "Student"),
        ("application-tracker", "Application Tracker", "Student"),
        ("reports", "Reports", "Student"),
    ]
    side_shell = st.container(border=True)
    with side_shell:
        st.markdown("<div class='sidebar-header'>TemanEDU</div>", unsafe_allow_html=True)
        for idx, (page, label, access) in enumerate(menu):
            is_active = access == "Student" and page == active_page
            if st.button(
                label,
                key=f"side_nav_btn_{idx}_{access}_{page or 'root'}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                _navigate(language=language, access=access, student_page=page)
        st.caption(status)


def _render_subtle_role_links(language: str) -> None:
    st.markdown("<div class='teman-role-footer'>", unsafe_allow_html=True)
    st.caption("Need counselor or admin tools?")
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        if st.button("Counselor Login", key="footer_counselor_link", use_container_width=True, type="secondary"):
            _navigate(language=language, access="Counselor")
    with c2:
        if st.button("Admin Login", key="footer_admin_link", use_container_width=True, type="secondary"):
            _navigate(language=language, access="Admin")
    with c3:
        st.caption("Student mode stays focused on conversational guidance.")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_student_subpage(page: str) -> None:
    user = get_current_user()
    if page in {"student-chat", "student-pathway"}:
        render_student_chat_page(st.session_state.get("language", "en"), user)
        return

    if page == "results":
        render_student_results_page(st.session_state.get("language", "en"), user)
        return

    if page == "course-finder":
        _render_course_finder(prefix="student", current_user=user)
        return

    if page == "application-tracker":
        _render_application_tracker(prefix="student", current_user=user)
        return

    if page == "about":
        st.markdown(
            """
            <div class="chat-page-card">
                <h3>About TemanEDU</h3>
                <p>TemanEDU helps Malaysian SPM and Diploma students match specific universities and programs, compare readiness, and plan applications with actionable next steps.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

def render_student_view(language: str) -> None:
    _inject_base_page_css()

    if "student_page" not in st.session_state:
        st.session_state["student_page"] = "student-chat"

    active_page = st.session_state.get("student_page", "student-chat")
    if active_page == "student-pathway":
        active_page = "student-chat"
        st.session_state["student_page"] = "student-chat"
    if active_page not in STUDENT_PAGES:
        active_page = "student-chat"
        st.session_state["student_page"] = "student-chat"
    _query_set(
        student_page=active_page,
        chat_q=st.session_state.get("student_chat_edit_question") if active_page == "student-chat" else None,
    )
    user = get_current_user()
    _render_top_nav(language, active_page, active_access="Student")
    shell = st.container(border=True)
    with shell:
        st.markdown("<div class='chat-shell-header'>TemanEDU Student Advisor</div>", unsafe_allow_html=True)
        _render_student_subpage(active_page)
    _render_subtle_role_links(language)


def render_counselor_view(language: str) -> None:
    _inject_base_page_css()
    _render_top_nav(language, active_page=None, active_access="Counselor")
    shell = st.container(border=True)
    with shell:
        st.markdown("<div class='chat-shell-header'>Counselor Workspace</div>", unsafe_allow_html=True)
        lang_col, _ = st.columns([1.2, 5.8])
        with lang_col:
            selected_language = st.selectbox("Language", ["en", "bm"], index=0 if language == "en" else 1, key="counselor_language")
            if selected_language != language:
                st.session_state["language"] = selected_language
                _query_set(language=selected_language, access="Counselor")
                st.rerun()
        render_counselor_dashboard(selected_language, inline_login=True)


def render_admin_view(language: str) -> None:
    _inject_base_page_css()
    _render_top_nav(language, active_page=None, active_access="Admin")
    shell = st.container(border=True)
    with shell:
        st.markdown("<div class='chat-shell-header'>Admin Workspace</div>", unsafe_allow_html=True)
        lang_col, _ = st.columns([1.2, 5.8])
        with lang_col:
            selected_language = st.selectbox("Language", ["en", "bm"], index=0 if language == "en" else 1, key="admin_language")
            if selected_language != language:
                st.session_state["language"] = selected_language
                _query_set(language=selected_language, access="Admin")
                st.rerun()
        render_admin_dashboard(selected_language, inline_login=True)


def main() -> None:
    bootstrap()
    restore_auth_from_query()
    restore_navigation_state()
    if "language" not in st.session_state:
        st.session_state["language"] = _query_get("language", "en") if _query_get("language", "en") in {"en", "bm"} else "en"
    if "access_mode" not in st.session_state:
        st.session_state["access_mode"] = _query_get("access", "Student") if _query_get("access", "Student") in {"Student", "Counselor", "Admin"} else "Student"

    language = st.session_state["language"]
    mode = st.session_state["access_mode"]

    if mode == "Student":
        _query_set(language=language, access="Student")
        render_student_view(language)
    elif mode == "Counselor":
        _query_set(language=language, access="Counselor")
        render_counselor_view(language)
    else:
        _query_set(language=language, access="Admin")
        render_admin_view(language)


if __name__ == "__main__":
    main()
