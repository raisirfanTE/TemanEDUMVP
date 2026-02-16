from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import db_session
from logic import evaluate_rules
from models import Rule


def fetch_rules(level: str) -> list[Rule]:
    with db_session() as db:
        return db.scalars(
            select(Rule).where(Rule.active.is_(True), Rule.student_level == level).order_by(Rule.priority_weight.desc())
        ).all()


def scenario_inputs() -> list[dict[str, Any]]:
    return [
        {
            "name": "SPM low budget beginner local",
            "student_level": "SPM",
            "spm_credits": 3,
            "subjects": {"bm": "C", "english": "D", "math": "D", "add_math": "E", "science": "D"},
            "interest_tags": ["Business"],
            "budget_monthly": 700,
            "need_work_part_time": True,
            "english_self": "Beginner",
            "destination_preference": "malaysia_only",
            "destination_tags": ["Malaysia"],
            "scholarship_needed": True,
            "timeline_urgency": "normal",
            "family_constraints": "financial",
            "willing_relocate": False,
            "preparedness_checklist": [],
        },
        {
            "name": "SPM strong STEM local",
            "student_level": "SPM",
            "spm_credits": 8,
            "subjects": {"bm": "B", "english": "B", "math": "A", "add_math": "B", "science": "A"},
            "interest_tags": ["Engineering", "IT"],
            "budget_monthly": 2800,
            "need_work_part_time": False,
            "english_self": "Intermediate",
            "destination_preference": "malaysia_only",
            "destination_tags": ["Malaysia"],
            "scholarship_needed": False,
            "timeline_urgency": "urgent",
            "family_constraints": "none",
            "willing_relocate": True,
            "preparedness_checklist": ["Transcript ready", "CV drafted"],
        },
        {
            "name": "SPM overseas business ambitious",
            "student_level": "SPM",
            "spm_credits": 7,
            "subjects": {"bm": "B", "english": "A", "math": "B", "add_math": "C", "science": "B"},
            "interest_tags": ["Business", "Economics"],
            "budget_monthly": 5200,
            "need_work_part_time": True,
            "english_self": "Advanced",
            "destination_preference": "open_overseas",
            "destination_tags": ["Australia", "UK"],
            "scholarship_needed": False,
            "timeline_urgency": "normal",
            "family_constraints": "none",
            "willing_relocate": True,
            "preparedness_checklist": ["Transcript ready", "CV drafted", "Shortlisted institutions"],
        },
        {
            "name": "Diploma IT local topup",
            "student_level": "Diploma",
            "cgpa": 3.05,
            "diploma_field": "IT",
            "interest_tags": ["IT", "Data"],
            "budget_monthly": 2500,
            "need_work_part_time": True,
            "english_self": "Intermediate",
            "destination_preference": "malaysia_only",
            "destination_tags": ["Malaysia"],
            "scholarship_needed": True,
            "timeline_urgency": "normal",
            "family_constraints": "none",
            "willing_relocate": False,
            "preparedness_checklist": ["CV drafted", "Transcript ready"],
        },
        {
            "name": "Diploma engineering overseas strict",
            "student_level": "Diploma",
            "cgpa": 3.2,
            "diploma_field": "Engineering",
            "interest_tags": ["Engineering"],
            "budget_monthly": 7000,
            "need_work_part_time": False,
            "english_self": "Advanced",
            "destination_preference": "open_overseas",
            "destination_tags": ["Germany", "Australia"],
            "scholarship_needed": False,
            "timeline_urgency": "normal",
            "family_constraints": "none",
            "willing_relocate": True,
            "preparedness_checklist": ["CV drafted", "Portfolio draft", "Transcript ready"],
        },
        {
            "name": "Diploma health low budget impossible",
            "student_level": "Diploma",
            "cgpa": 2.4,
            "diploma_field": "Health",
            "interest_tags": ["Health"],
            "budget_monthly": 600,
            "need_work_part_time": True,
            "english_self": "Beginner",
            "destination_preference": "open_overseas",
            "destination_tags": ["UK"],
            "scholarship_needed": True,
            "timeline_urgency": "urgent",
            "family_constraints": "financial",
            "willing_relocate": False,
            "preparedness_checklist": [],
        },
    ]


def main() -> None:
    scenarios = scenario_inputs()
    for scenario in scenarios:
        level = scenario["student_level"]
        rules = fetch_rules(level)
        result = evaluate_rules(rules, scenario)

        print(f"\n=== {scenario['name']} ===")
        if result["no_match"]:
            print("Outcome: NO MATCH -> Recovery Plan")
            blocked = result.get("recovery_plan", {}).get("blocked_inputs", [])
            if blocked:
                print("Blocked by:", "; ".join(blocked[:4]))
        else:
            top = result["recommendations"][:3]
            print("Outcome: MATCH")
            for idx, rec in enumerate(top, start=1):
                print(f"{idx}. {rec['pathway_title']} (fit={rec['fit_score']}, readiness={rec['readiness_score']})")


if __name__ == "__main__":
    main()
