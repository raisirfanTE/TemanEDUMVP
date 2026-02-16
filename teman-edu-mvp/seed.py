from __future__ import annotations

import csv
import json
import os
import uuid
import ast
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from auth import hash_password
from models import (
    AuditLog,
    ContentSnippet,
    ExternalDataSource,
    Organization,
    Rule,
    UniversityProgram,
    User,
    UserOrganization,
)


REQUIRED_RULE_COLUMNS = {
    "rule_id",
    "active",
    "student_level",
    "interest_tags",
    "destination_tags",
    "min_spm_credits",
    "required_subjects_json",
    "min_cgpa",
    "budget_min",
    "budget_max",
    "english_min",
    "constraints_json",
    "pathway_title",
    "pathway_summary",
    "cost_estimate_text",
    "visa_note",
    "scholarship_likelihood",
    "readiness_gaps",
    "next_steps",
    "priority_weight",
}


def _parse_json_or_empty(value: str) -> dict:
    raw = (value or "").strip()
    if not raw:
        return {}
    if raw == "{}":
        return {}

    # Accept both proper JSON and common CSV-escaped variants like {\"k\":\"v\"}.
    for candidate in (
        raw,
        raw.replace('\\"', '"'),
        raw.replace("'", '"'),
    ):
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            continue

    # Last fallback for Python-dict-like payloads.
    try:
        parsed = ast.literal_eval(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (SyntaxError, ValueError):
        raise ValueError(f"Invalid JSON object field: {raw}")


def _parse_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def _parse_int(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value else None


def _parse_float(value: str) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def validate_csv_columns(columns: list[str]) -> tuple[bool, list[str]]:
    missing = sorted(REQUIRED_RULE_COLUMNS - set(columns))
    return len(missing) == 0, missing


def load_rules_from_csv(csv_text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(csv_text.splitlines())
    valid, missing = validate_csv_columns(reader.fieldnames or [])
    if not valid:
        raise ValueError(f"Missing required columns: {missing}")

    rows: list[dict[str, Any]] = []
    for row in reader:
        rows.append(
            {
                "rule_id": row["rule_id"],
                "active": _parse_bool(row["active"]),
                "student_level": row["student_level"],
                "interest_tags": _parse_list(row["interest_tags"]),
                "destination_tags": _parse_list(row["destination_tags"]),
                "min_spm_credits": _parse_int(row["min_spm_credits"]),
                "required_subjects_json": _parse_json_or_empty(row["required_subjects_json"]),
                "min_cgpa": _parse_float(row["min_cgpa"]),
                "budget_min": _parse_int(row["budget_min"]),
                "budget_max": _parse_int(row["budget_max"]),
                "english_min": row["english_min"] or None,
                "constraints_json": _parse_json_or_empty(row["constraints_json"]),
                "pathway_title": row["pathway_title"],
                "pathway_summary": row["pathway_summary"],
                "cost_estimate_text": row["cost_estimate_text"],
                "visa_note": row["visa_note"],
                "scholarship_likelihood": row["scholarship_likelihood"],
                "readiness_gaps": _parse_list(row["readiness_gaps"]),
                "next_steps": row["next_steps"],
                "priority_weight": int(row["priority_weight"] or 0),
            }
        )
    return rows


def preview_diff(db: Session, rows: list[dict[str, Any]]) -> dict[str, int]:
    existing = {
        r.rule_id: r
        for r in db.scalars(select(Rule).where(Rule.rule_id.in_([row["rule_id"] for row in rows]))).all()
    }
    to_insert = 0
    to_update = 0
    for row in rows:
        if row["rule_id"] in existing:
            to_update += 1
        else:
            to_insert += 1
    return {"insert": to_insert, "update": to_update}


def upsert_rules(db: Session, rows: list[dict[str, Any]], actor_user_id: str | None = None, source: str = "csv") -> dict[str, int]:
    existing_map = {
        r.rule_id: r
        for r in db.scalars(select(Rule).where(Rule.rule_id.in_([row["rule_id"] for row in rows]))).all()
    }

    inserted = 0
    updated = 0
    for row in rows:
        existing = existing_map.get(row["rule_id"])
        if existing:
            for key, value in row.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(Rule(**row))
            inserted += 1

    db.add(
        AuditLog(
            user_id=uuid.UUID(actor_user_id) if actor_user_id else None,
            action="rules_upsert",
            details_json={
                "source": source,
                "inserted": inserted,
                "updated": updated,
                "rule_ids": [r["rule_id"] for r in rows],
            },
        )
    )
    return {"inserted": inserted, "updated": updated}


def seed_content_snippets(db: Session) -> None:
    base_content = [
        {
            "key": "disclaimer_general",
            "language": "en",
            "value": "TemanEDU provides readiness guidance only, not guaranteed placements.",
        },
        {
            "key": "disclaimer_visa",
            "language": "en",
            "value": "Visa/work notes are general information, not legal advice.",
        },
        {
            "key": "disclaimer_scholarship",
            "language": "en",
            "value": "Scholarship likelihood bands are indicative, not guarantees.",
        },
        {
            "key": "disclaimer_general",
            "language": "bm",
            "value": "TemanEDU memberi panduan kesiapsiagaan sahaja, bukan jaminan penempatan.",
        },
        {
            "key": "disclaimer_visa",
            "language": "bm",
            "value": "Nota visa/kerja ialah maklumat umum, bukan nasihat undang-undang.",
        },
        {
            "key": "disclaimer_scholarship",
            "language": "bm",
            "value": "Kebarangkalian biasiswa hanya indikatif, bukan jaminan.",
        },
        {
            "key": "alumni_malaysia_it_1",
            "language": "en",
            "value": "Counselor insight::Students targeting IT in Malaysia usually move faster when they prepare a basic GitHub portfolio before applications.",
        },
        {
            "key": "alumni_malaysia_business_1",
            "language": "en",
            "value": "Alumni note::Business applicants improved interview confidence after joining one short case competition and documenting outcomes.",
        },
        {
            "key": "alumni_uk_engineering_1",
            "language": "en",
            "value": "Education fair note::Engineering applicants to the UK often need earlier personal statement drafts because review cycles are longer.",
        },
        {
            "key": "alumni_general_general_1",
            "language": "en",
            "value": "Mentor tip::Students who shortlist 3 realistic universities and 1 stretch option tend to submit on time with better fit.",
        },
        {
            "key": "alumni_malaysia_it_1",
            "language": "bm",
            "value": "Pandangan kaunselor::Pelajar IT di Malaysia biasanya bergerak lebih cepat jika sediakan portfolio GitHub ringkas sebelum memohon.",
        },
        {
            "key": "alumni_general_general_1",
            "language": "bm",
            "value": "Tip mentor::Pelajar yang senarai 3 universiti realistik dan 1 pilihan cabaran biasanya lebih teratur dan sempat hantar permohonan.",
        },
    ]

    for item in base_content:
        exists = db.scalar(
            select(ContentSnippet).where(
                ContentSnippet.key == item["key"],
                ContentSnippet.language == item["language"],
            )
        )
        if not exists:
            db.add(ContentSnippet(**item))


def seed_default_users_and_org(db: Session) -> None:
    org = db.scalar(select(Organization).where(Organization.name == "Demo School"))
    if not org:
        org = Organization(name="Demo School", type="school")
        db.add(org)
        db.flush()

    admin_email = os.getenv("TEMANEDU_ADMIN_EMAIL", "admin@temanedu.local")
    admin_pass = os.getenv("TEMANEDU_ADMIN_PASSWORD", "Admin123!")
    counselor_email = os.getenv("TEMANEDU_COUNSELOR_EMAIL", "counselor@temanedu.local")
    counselor_pass = os.getenv("TEMANEDU_COUNSELOR_PASSWORD", "Counselor123!")

    admin = db.scalar(select(User).where(User.email == admin_email))
    if not admin:
        admin = User(role="admin", email=admin_email, password_hash=hash_password(admin_pass))
        db.add(admin)
        db.flush()

    counselor = db.scalar(select(User).where(User.email == counselor_email))
    if not counselor:
        counselor = User(role="counselor", email=counselor_email, password_hash=hash_password(counselor_pass))
        db.add(counselor)
        db.flush()

    for user, role_in_org in [(admin, "admin"), (counselor, "counselor")]:
        link = db.scalar(
            select(UserOrganization).where(
                UserOrganization.user_id == user.id,
                UserOrganization.organization_id == org.id,
            )
        )
        if not link:
            db.add(UserOrganization(user_id=user.id, organization_id=org.id, role_in_org=role_in_org))


def seed_rules_if_empty(db: Session, sample_csv_path: str = "data/logic_table.sample.csv") -> dict[str, int]:
    total = db.scalar(select(func.count()).select_from(Rule))
    if total and total > 0:
        return {"inserted": 0, "updated": 0}

    path = Path(sample_csv_path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_default_sample_csv(), encoding="utf-8")

    rows = load_rules_from_csv(path.read_text(encoding="utf-8"))
    return upsert_rules(db, rows, source="seed")


def seed_external_data_sources(db: Session) -> None:
    sources = [
        {
            "source_code": "QS_RANKINGS",
            "name": "QS World University Rankings",
            "base_url": "https://www.topuniversities.com/university-rankings",
            "update_frequency": "quarterly",
            "fields_json": {"fields": ["university_name", "country", "subject_rank", "overall_rank", "program_details"]},
            "notes": "Ranking values are snapshots and should be revalidated against latest QS release.",
        },
        {
            "source_code": "MOHE_OFFICIAL",
            "name": "Malaysia Ministry of Higher Education (MOHE)",
            "base_url": "https://www.mohe.gov.my/en/universities",
            "update_frequency": "monthly",
            "fields_json": {"fields": ["university_name", "program_list", "admission_requirements", "fees"]},
            "notes": "Used for institution legitimacy and Malaysia-based program listing references.",
        },
        {
            "source_code": "IDP_EDUCATION",
            "name": "IDP Malaysia",
            "base_url": "https://www.idp.com/malaysia/",
            "update_frequency": "weekly",
            "fields_json": {"fields": ["university_name", "program_details", "application_dates", "entry_requirements"]},
            "notes": "Used for indicative overseas intakes and admissions planning references.",
        },
        {
            "source_code": "PTPTN_ELIGIBLE",
            "name": "PTPTN Program Eligibility",
            "base_url": "https://www.ptptn.gov.my/program-terpilih",
            "update_frequency": "monthly",
            "fields_json": {"fields": ["university_name", "program_eligibility", "loan_amount"]},
            "notes": "Used to flag indicative PTPTN-eligible local program options.",
        },
    ]
    for src in sources:
        existing = db.scalar(select(ExternalDataSource).where(ExternalDataSource.source_code == src["source_code"]))
        if existing:
            existing.name = src["name"]
            existing.base_url = src["base_url"]
            existing.update_frequency = src["update_frequency"]
            existing.fields_json = src["fields_json"]
            existing.active = True
            existing.notes = src["notes"]
        else:
            db.add(ExternalDataSource(**src, active=True))


def seed_university_programs(db: Session) -> None:
    count = db.scalar(select(func.count()).select_from(UniversityProgram)) or 0
    if count > 0:
        return

    programs = [
        {
            "program_code": "MY_UM_FND_COMP_01",
            "university_name": "Universiti Malaya",
            "country": "Malaysia",
            "program_name": "Foundation in Science (Computer Science Pathway)",
            "program_level": "Foundation",
            "field_tags": ["IT", "Engineering", "Data"],
            "intake_terms": ["May", "September"],
            "application_deadline_text": "Apply 8-10 weeks before intake.",
            "admission_requirements_json": {"student_level": "SPM", "min_spm_credits": 6, "required_subjects": {"math": "B", "english": "C"}, "english_min_level": "Intermediate"},
            "tuition_yearly_min_myr": 18000,
            "tuition_yearly_max_myr": 24000,
            "ielts_min": None,
            "toefl_min": None,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": True,
            "ptptn_eligible": True,
            "source_codes": ["MOHE_OFFICIAL", "PTPTN_ELIGIBLE"],
            "source_urls_json": {
                "MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities",
                "PTPTN_ELIGIBLE": "https://www.ptptn.gov.my/program-terpilih",
            },
            "application_url": "https://study.um.edu.my/",
            "contact_email": "admission@um.edu.my",
            "notes": "Strong route for SPM students targeting CS/engineering progression.",
        },
        {
            "program_code": "MY_APU_DIP_IT_01",
            "university_name": "Asia Pacific University of Technology & Innovation",
            "country": "Malaysia",
            "program_name": "Diploma in Information Technology",
            "program_level": "Diploma",
            "field_tags": ["IT", "Data"],
            "intake_terms": ["March", "July", "November"],
            "application_deadline_text": "Apply 6-8 weeks before intake.",
            "admission_requirements_json": {"student_level": "SPM", "min_spm_credits": 3, "required_subjects": {"math": "C", "english": "C"}, "english_min_level": "Intermediate"},
            "tuition_yearly_min_myr": 23000,
            "tuition_yearly_max_myr": 29000,
            "ielts_min": None,
            "toefl_min": None,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": True,
            "ptptn_eligible": True,
            "source_codes": ["MOHE_OFFICIAL", "PTPTN_ELIGIBLE"],
            "source_urls_json": {
                "MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities",
                "PTPTN_ELIGIBLE": "https://www.ptptn.gov.my/program-terpilih",
            },
            "application_url": "https://www.apu.edu.my/study-with-us",
            "contact_email": "info@apu.edu.my",
            "notes": "Good option for applied IT route with part-time feasibility.",
        },
        {
            "program_code": "MY_TAYLORS_DIP_BUS_01",
            "university_name": "Taylor's University",
            "country": "Malaysia",
            "program_name": "Diploma in Business",
            "program_level": "Diploma",
            "field_tags": ["Business", "Economics", "Digital Marketing"],
            "intake_terms": ["April", "August"],
            "application_deadline_text": "Apply 6-10 weeks before intake.",
            "admission_requirements_json": {"student_level": "SPM", "min_spm_credits": 3, "required_subjects": {"english": "C"}, "english_min_level": "Intermediate"},
            "tuition_yearly_min_myr": 27000,
            "tuition_yearly_max_myr": 33000,
            "ielts_min": None,
            "toefl_min": None,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": True,
            "ptptn_eligible": False,
            "source_codes": ["MOHE_OFFICIAL", "IDP_EDUCATION"],
            "source_urls_json": {
                "MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities",
                "IDP_EDUCATION": "https://www.idp.com/malaysia/",
            },
            "application_url": "https://university.taylors.edu.my/en/study/undergraduate-and-diploma.html",
            "contact_email": "admissions@taylors.edu.my",
            "notes": "Business to degree progression route with strong industry exposure.",
        },
        {
            "program_code": "MY_INTI_DIP_DM_01",
            "university_name": "INTI International University",
            "country": "Malaysia",
            "program_name": "Diploma in Digital Business and Marketing",
            "program_level": "Diploma",
            "field_tags": ["Business", "Digital Marketing", "Creative"],
            "intake_terms": ["January", "May", "September"],
            "application_deadline_text": "Apply 4-8 weeks before intake.",
            "admission_requirements_json": {"student_level": "SPM", "min_spm_credits": 3, "required_subjects": {"english": "C"}, "english_min_level": "Intermediate"},
            "tuition_yearly_min_myr": 19000,
            "tuition_yearly_max_myr": 24000,
            "ielts_min": None,
            "toefl_min": None,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": True,
            "ptptn_eligible": True,
            "source_codes": ["MOHE_OFFICIAL", "PTPTN_ELIGIBLE"],
            "source_urls_json": {
                "MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities",
                "PTPTN_ELIGIBLE": "https://www.ptptn.gov.my/program-terpilih",
            },
            "application_url": "https://newinti.edu.my/programmes/",
            "contact_email": "admissions@newinti.edu.my",
            "notes": "Useful for students who want specific digital marketing starting route.",
        },
        {
            "program_code": "MY_UCSI_BSC_CS_01",
            "university_name": "UCSI University",
            "country": "Malaysia",
            "program_name": "Bachelor of Computer Science",
            "program_level": "Bachelor",
            "field_tags": ["IT", "Data", "Engineering"],
            "intake_terms": ["January", "May", "September"],
            "application_deadline_text": "Apply 8 weeks before intake.",
            "admission_requirements_json": {"student_level": "Diploma", "min_cgpa": 2.5, "english_min_level": "Intermediate", "ielts_min": 5.0},
            "tuition_yearly_min_myr": 29000,
            "tuition_yearly_max_myr": 36000,
            "ielts_min": 5.0,
            "toefl_min": 42,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": True,
            "ptptn_eligible": True,
            "source_codes": ["MOHE_OFFICIAL", "PTPTN_ELIGIBLE"],
            "source_urls_json": {
                "MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities",
                "PTPTN_ELIGIBLE": "https://www.ptptn.gov.my/program-terpilih",
            },
            "application_url": "https://www.ucsiuniversity.edu.my/programmes",
            "contact_email": "admissions@ucsiuniversity.edu.my",
            "notes": "Degree progression option for diploma holders with CGPA 2.5+.",
        },
        {
            "program_code": "MY_MONASH_BCOM_01",
            "university_name": "Monash University Malaysia",
            "country": "Malaysia",
            "program_name": "Bachelor of Business and Commerce",
            "program_level": "Bachelor",
            "field_tags": ["Business", "Economics", "Accounting", "Digital Marketing"],
            "intake_terms": ["February", "July", "October"],
            "application_deadline_text": "Apply 10-12 weeks before intake.",
            "admission_requirements_json": {"student_level": "Diploma", "min_cgpa": 2.7, "english_min_level": "Advanced", "ielts_min": 6.0},
            "tuition_yearly_min_myr": 52000,
            "tuition_yearly_max_myr": 68000,
            "ielts_min": 6.0,
            "toefl_min": 79,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": True,
            "ptptn_eligible": False,
            "source_codes": ["MOHE_OFFICIAL", "IDP_EDUCATION", "QS_RANKINGS"],
            "source_urls_json": {
                "MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities",
                "IDP_EDUCATION": "https://www.idp.com/malaysia/",
                "QS_RANKINGS": "https://www.topuniversities.com/university-rankings",
            },
            "application_url": "https://www.monash.edu.my/study",
            "contact_email": "future@monash.edu",
            "notes": "Higher-budget pathway; strong overseas articulation alignment.",
        },
        {
            "program_code": "MY_MAHSA_DIP_NURS_01",
            "university_name": "MAHSA University",
            "country": "Malaysia",
            "program_name": "Diploma in Nursing",
            "program_level": "Diploma",
            "field_tags": ["Health", "Science"],
            "intake_terms": ["March", "September"],
            "application_deadline_text": "Apply 6-10 weeks before intake.",
            "admission_requirements_json": {"student_level": "SPM", "min_spm_credits": 5, "required_subjects": {"science": "C", "english": "C"}, "english_min_level": "Intermediate"},
            "tuition_yearly_min_myr": 22000,
            "tuition_yearly_max_myr": 30000,
            "ielts_min": None,
            "toefl_min": None,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": True,
            "ptptn_eligible": True,
            "source_codes": ["MOHE_OFFICIAL", "PTPTN_ELIGIBLE"],
            "source_urls_json": {
                "MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities",
                "PTPTN_ELIGIBLE": "https://www.ptptn.gov.my/program-terpilih",
            },
            "application_url": "https://mahsa.edu.my/programmes/",
            "contact_email": "admissions@mahsa.edu.my",
            "notes": "Health-focused local route with strong employability orientation.",
        },
        {
            "program_code": "MY_LIMKOKWING_DIP_DES_01",
            "university_name": "Limkokwing University",
            "country": "Malaysia",
            "program_name": "Diploma in Creative Multimedia",
            "program_level": "Diploma",
            "field_tags": ["Creative", "Design", "Digital Marketing"],
            "intake_terms": ["March", "July", "November"],
            "application_deadline_text": "Apply 4-6 weeks before intake.",
            "admission_requirements_json": {"student_level": "SPM", "min_spm_credits": 3, "required_subjects": {"english": "C"}, "english_min_level": "Intermediate"},
            "tuition_yearly_min_myr": 20000,
            "tuition_yearly_max_myr": 26000,
            "ielts_min": None,
            "toefl_min": None,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": True,
            "ptptn_eligible": False,
            "source_codes": ["MOHE_OFFICIAL"],
            "source_urls_json": {"MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities"},
            "application_url": "https://www.limkokwing.net/malaysia/programmes/",
            "contact_email": "admissions@limkokwing.edu.my",
            "notes": "Creative route for portfolio-driven progression.",
        },
        {
            "program_code": "AU_RMIT_BBUS_01",
            "university_name": "RMIT University",
            "country": "Australia",
            "program_name": "Bachelor of Business",
            "program_level": "Bachelor",
            "field_tags": ["Business", "Economics", "Digital Marketing"],
            "intake_terms": ["February", "July"],
            "application_deadline_text": "Apply 3-4 months before intake.",
            "admission_requirements_json": {"student_level": "Diploma", "min_cgpa": 2.8, "english_min_level": "Advanced", "ielts_min": 6.5},
            "tuition_yearly_min_myr": 98000,
            "tuition_yearly_max_myr": 120000,
            "ielts_min": 6.5,
            "toefl_min": 79,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": False,
            "ptptn_eligible": False,
            "source_codes": ["QS_RANKINGS", "IDP_EDUCATION"],
            "source_urls_json": {
                "QS_RANKINGS": "https://www.topuniversities.com/university-rankings",
                "IDP_EDUCATION": "https://www.idp.com/malaysia/",
            },
            "application_url": "https://www.rmit.edu.au/study-with-us/international-students",
            "contact_email": "international.admissions@rmit.edu.au",
            "notes": "Overseas business option requiring stronger English readiness.",
        },
        {
            "program_code": "AU_QUT_BSC_IT_01",
            "university_name": "Queensland University of Technology",
            "country": "Australia",
            "program_name": "Bachelor of Information Technology",
            "program_level": "Bachelor",
            "field_tags": ["IT", "Data", "Engineering"],
            "intake_terms": ["February", "July"],
            "application_deadline_text": "Apply 3-4 months before intake.",
            "admission_requirements_json": {"student_level": "Diploma", "min_cgpa": 2.7, "english_min_level": "Advanced", "ielts_min": 6.5},
            "tuition_yearly_min_myr": 96000,
            "tuition_yearly_max_myr": 118000,
            "ielts_min": 6.5,
            "toefl_min": 79,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": False,
            "ptptn_eligible": False,
            "source_codes": ["QS_RANKINGS", "IDP_EDUCATION"],
            "source_urls_json": {
                "QS_RANKINGS": "https://www.topuniversities.com/university-rankings",
                "IDP_EDUCATION": "https://www.idp.com/malaysia/",
            },
            "application_url": "https://www.qut.edu.au/study/international-students",
            "contact_email": "askqut@qut.edu.au",
            "notes": "Target for diploma IT students looking for applied tech degree.",
        },
        {
            "program_code": "UK_LEEDS_BSC_BUS_01",
            "university_name": "University of Leeds",
            "country": "UK",
            "program_name": "BSc International Business",
            "program_level": "Bachelor",
            "field_tags": ["Business", "Economics"],
            "intake_terms": ["September"],
            "application_deadline_text": "UCAS timeline usually closes around January for September entry.",
            "admission_requirements_json": {"student_level": "Diploma", "min_cgpa": 3.0, "english_min_level": "Advanced", "ielts_min": 6.5},
            "tuition_yearly_min_myr": 130000,
            "tuition_yearly_max_myr": 155000,
            "ielts_min": 6.5,
            "toefl_min": 88,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": False,
            "ptptn_eligible": False,
            "source_codes": ["QS_RANKINGS", "IDP_EDUCATION"],
            "source_urls_json": {
                "QS_RANKINGS": "https://www.topuniversities.com/university-rankings",
                "IDP_EDUCATION": "https://www.idp.com/malaysia/",
            },
            "application_url": "https://www.leeds.ac.uk/international",
            "contact_email": "study@leeds.ac.uk",
            "notes": "Best for strong academic and English profiles planning UK intake.",
        },
        {
            "program_code": "UK_PORTSMOUTH_TOPUP_IT_01",
            "university_name": "University of Portsmouth",
            "country": "UK",
            "program_name": "BSc (Hons) Computing (Top-up)",
            "program_level": "Top-up",
            "field_tags": ["IT", "Data"],
            "intake_terms": ["September", "January"],
            "application_deadline_text": "Apply 3-4 months before intake.",
            "admission_requirements_json": {"student_level": "Diploma", "min_cgpa": 2.6, "english_min_level": "Advanced", "ielts_min": 6.0},
            "tuition_yearly_min_myr": 96000,
            "tuition_yearly_max_myr": 118000,
            "ielts_min": 6.0,
            "toefl_min": 79,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": False,
            "ptptn_eligible": False,
            "source_codes": ["IDP_EDUCATION"],
            "source_urls_json": {"IDP_EDUCATION": "https://www.idp.com/malaysia/"},
            "application_url": "https://www.port.ac.uk/study/international-students",
            "contact_email": "international.office@port.ac.uk",
            "notes": "Useful top-up route for diploma students seeking 1-year progression.",
        },
        {
            "program_code": "SG_JCU_BBUS_01",
            "university_name": "James Cook University Singapore",
            "country": "Singapore",
            "program_name": "Bachelor of Business",
            "program_level": "Bachelor",
            "field_tags": ["Business", "Digital Marketing"],
            "intake_terms": ["March", "July", "November"],
            "application_deadline_text": "Apply 2-3 months before intake.",
            "admission_requirements_json": {"student_level": "Diploma", "min_cgpa": 2.5, "english_min_level": "Intermediate", "ielts_min": 6.0},
            "tuition_yearly_min_myr": 73000,
            "tuition_yearly_max_myr": 90000,
            "ielts_min": 6.0,
            "toefl_min": 79,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": False,
            "ptptn_eligible": False,
            "source_codes": ["IDP_EDUCATION"],
            "source_urls_json": {"IDP_EDUCATION": "https://www.idp.com/malaysia/"},
            "application_url": "https://www.jcu.edu.sg/courses-and-study",
            "contact_email": "admissions-singapore@jcu.edu.au",
            "notes": "Regional overseas option with multiple intakes each year.",
        },
        {
            "program_code": "NZ_MASSEY_BENG_01",
            "university_name": "Massey University",
            "country": "New Zealand",
            "program_name": "Bachelor of Engineering with Honours",
            "program_level": "Bachelor",
            "field_tags": ["Engineering", "IT"],
            "intake_terms": ["February", "July"],
            "application_deadline_text": "Apply 3-4 months before intake.",
            "admission_requirements_json": {"student_level": "Diploma", "min_cgpa": 2.8, "english_min_level": "Advanced", "ielts_min": 6.0},
            "tuition_yearly_min_myr": 85000,
            "tuition_yearly_max_myr": 106000,
            "ielts_min": 6.0,
            "toefl_min": 80,
            "qs_overall_rank": None,
            "qs_subject_rank": None,
            "mohe_listed": False,
            "ptptn_eligible": False,
            "source_codes": ["QS_RANKINGS", "IDP_EDUCATION"],
            "source_urls_json": {
                "QS_RANKINGS": "https://www.topuniversities.com/university-rankings",
                "IDP_EDUCATION": "https://www.idp.com/malaysia/",
            },
            "application_url": "https://www.massey.ac.nz/study/",
            "contact_email": "international@massey.ac.nz",
            "notes": "Engineering overseas option for stronger CGPA profiles.",
        },
    ]

    qs_rank_snapshot = {
        "MY_MONASH_BCOM_01": 37,
        "AU_RMIT_BBUS_01": 140,
        "AU_QUT_BSC_IT_01": 189,
        "UK_LEEDS_BSC_BUS_01": 75,
        "UK_PORTSMOUTH_TOPUP_IT_01": 502,
        "SG_JCU_BBUS_01": 415,
        "NZ_MASSEY_BENG_01": 239,
    }
    for row in programs:
        if row["program_code"] in qs_rank_snapshot:
            row["qs_overall_rank"] = qs_rank_snapshot[row["program_code"]]
            row["source_codes"] = sorted(set(row["source_codes"] + ["QS_RANKINGS"]))
            row["source_urls_json"]["QS_RANKINGS"] = "https://www.topuniversities.com/university-rankings"

    for row in programs:
        db.add(UniversityProgram(active=True, **row))


def reset_and_seed(db: Session) -> None:
    db.execute(delete(Rule))
    rows = load_rules_from_csv(_default_sample_csv())
    upsert_rules(db, rows, source="reset")


def _default_sample_csv() -> str:
    sample_path = Path("data/logic_table.sample.csv")
    if sample_path.exists():
        return sample_path.read_text(encoding="utf-8")

    return """rule_id,active,student_level,interest_tags,destination_tags,min_spm_credits,required_subjects_json,min_cgpa,budget_min,budget_max,english_min,constraints_json,pathway_title,pathway_summary,cost_estimate_text,visa_note,scholarship_likelihood,readiness_gaps,next_steps,priority_weight
SPM_IT_LOCAL_01,true,SPM,IT|Engineering,Malaysia,5,"{""math"":""C"",""english"":""C""}",,800,3000,Intermediate,"{""work_part_time_ok"":true,""timeline_fast_track"":true}",Foundation in IT (Local),Start with a local foundation before degree progression,"RM 800-3000/month","General note: verify latest study and work rules with official channels.",Medium,"English speaking practice|Portfolio mini-project|CV preparation","Apply to 2 local institutions and prepare portfolio in 30 days",9
"""
