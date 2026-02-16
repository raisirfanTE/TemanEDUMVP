from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


GRADE_SCALE = {
    "G": 0,
    "E": 1,
    "D": 2,
    "C": 3,
    "C+": 4,
    "B": 5,
    "B+": 6,
    "A-": 7,
    "A": 8,
    "A+": 9,
}

ENGLISH_LEVELS = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
MONTH_TO_NUM = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass
class ScoreDetail:
    score: float
    matched: list[str]
    borderline: list[str]
    missing: list[str]


def _field(rule: Any, name: str, default: Any = None) -> Any:
    if isinstance(rule, dict):
        return rule.get(name, default)
    return getattr(rule, name, default)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _norm_set(values: list[str] | None) -> set[str]:
    return {v.strip().lower() for v in (values or []) if str(v).strip()}


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def grade_meets_requirement(student_grade: str, required_grade: str) -> bool:
    return GRADE_SCALE.get((student_grade or "").upper(), -1) >= GRADE_SCALE.get((required_grade or "").upper(), 99)


def english_meets_requirement(student_level: str, required_level: str) -> bool:
    return ENGLISH_LEVELS.get(student_level, -1) >= ENGLISH_LEVELS.get(required_level, 99)


def evaluate_rule_gate(rule: Any, student_input: dict[str, Any]) -> tuple[bool, list[str], list[str], list[str]]:
    matched: list[str] = []
    borderline: list[str] = []
    missing: list[str] = []

    if not _field(rule, "active", True):
        missing.append("Rule inactive")
        return False, matched, borderline, missing

    student_level = student_input.get("student_level")
    if _field(rule, "student_level") != student_level:
        missing.append("Student level mismatch")
        return False, matched, borderline, missing
    matched.append("Student level")

    if student_level == "SPM":
        min_credits = _field(rule, "min_spm_credits")
        if min_credits is not None:
            credits = int(student_input.get("spm_credits") or 0)
            if credits < int(min_credits):
                missing.append(f"SPM credits {credits} < {min_credits}")
                return False, matched, borderline, missing
            if credits == int(min_credits):
                borderline.append("SPM credits at threshold")
            else:
                matched.append("SPM credits")

        required_subjects = _field(rule, "required_subjects_json") or {}
        student_subjects = {k.lower(): v for k, v in (student_input.get("subjects") or {}).items()}
        for subject, needed_grade in required_subjects.items():
            student_grade = student_subjects.get(subject.lower())
            if not student_grade:
                missing.append(f"Missing subject grade for {subject}")
                return False, matched, borderline, missing
            if not grade_meets_requirement(student_grade, str(needed_grade)):
                missing.append(f"{subject} below {needed_grade}")
                return False, matched, borderline, missing
            if student_grade.upper() == str(needed_grade).upper():
                borderline.append(f"{subject} at threshold {needed_grade}")
            else:
                matched.append(f"{subject} requirement")

    if student_level == "Diploma":
        min_cgpa = _field(rule, "min_cgpa")
        if min_cgpa is not None:
            cgpa = _to_float(student_input.get("cgpa"), 0.0)
            min_cgpa_value = _to_float(min_cgpa)
            if cgpa < min_cgpa_value:
                missing.append(f"CGPA {cgpa:.2f} < {min_cgpa_value:.2f}")
                return False, matched, borderline, missing
            if abs(cgpa - min_cgpa_value) < 0.05:
                borderline.append("CGPA at threshold")
            else:
                matched.append("CGPA requirement")

    budget_monthly = int(student_input.get("budget_monthly") or 0)
    budget_min = _field(rule, "budget_min")
    if budget_min:
        if budget_monthly < int(budget_min):
            if budget_monthly >= int(budget_min) * 0.8:
                borderline.append("Budget slightly below pathway minimum")
            else:
                missing.append("Budget below pathway minimum")
                return False, matched, borderline, missing
        else:
            matched.append("Budget minimum")

    required_english = _field(rule, "english_min")
    if required_english:
        student_english = student_input.get("english_self", "Beginner")
        student_level_int = ENGLISH_LEVELS.get(student_english, 0)
        required_level_int = ENGLISH_LEVELS.get(required_english, 2)
        if student_level_int < required_level_int - 1:
            missing.append("English level significantly below requirement")
            return False, matched, borderline, missing
        if student_level_int < required_level_int:
            borderline.append("English one level below requirement")
        elif student_level_int == required_level_int:
            borderline.append("English at threshold")
        else:
            matched.append("English readiness")

    destinations = _norm_set(_field(rule, "destination_tags") or ["malaysia"])
    preference = student_input.get("destination_preference", "malaysia_only")
    selected_destinations = _norm_set(student_input.get("destination_tags") or ["malaysia"])
    if preference == "malaysia_only" and "malaysia" not in destinations:
        missing.append("Overseas-only pathway while student chose Malaysia only")
        return False, matched, borderline, missing

    if preference == "open_overseas" and selected_destinations:
        if destinations and not (destinations & selected_destinations) and "malaysia" not in destinations:
            borderline.append("Destination preference not directly matched")
        else:
            matched.append("Destination preference")

    if not student_input.get("willing_relocate", True) and "malaysia" not in destinations:
        missing.append("Relocation not preferred")
        return False, matched, borderline, missing

    return True, matched, borderline, missing


def score_interest(rule: Any, student_input: dict[str, Any]) -> ScoreDetail:
    rule_tags = _norm_set(_field(rule, "interest_tags"))
    student_tags = _norm_set(student_input.get("interest_tags") or [])
    if not rule_tags:
        return ScoreDetail(15.0, ["Flexible interest tags"], [], [])
    overlap = rule_tags & student_tags
    ratio = len(overlap) / len(rule_tags)
    score = 30 * ratio
    matched = [f"Interest match: {', '.join(sorted(overlap))}"] if overlap else []
    missing_tags = list(sorted(rule_tags - student_tags))
    borderline = ["Partial interest overlap"] if 0 < ratio < 1 else []
    missing = [f"Interest tags missing: {', '.join(missing_tags)}"] if missing_tags else []
    return ScoreDetail(score, matched, borderline, missing)


def score_academic(rule: Any, student_input: dict[str, Any]) -> ScoreDetail:
    matched: list[str] = []
    borderline: list[str] = []
    missing: list[str] = []
    score = 0.0

    level = student_input.get("student_level")
    if level == "SPM":
        min_credits = _field(rule, "min_spm_credits")
        credits = int(student_input.get("spm_credits") or 0)
        if min_credits:
            ratio = min(1.2, credits / float(min_credits))
            score += min(15.0, ratio * 12.5)
            if credits > min_credits:
                matched.append("Credits above baseline")
            elif credits == min_credits:
                borderline.append("Credits at baseline")

        required_subjects = _field(rule, "required_subjects_json") or {}
        if required_subjects:
            student_subjects = {k.lower(): v for k, v in (student_input.get("subjects") or {}).items()}
            satisfied = 0
            for subject, needed in required_subjects.items():
                got = student_subjects.get(subject.lower())
                if got and grade_meets_requirement(got, str(needed)):
                    satisfied += 1
                else:
                    missing.append(f"Subject strengthen needed: {subject}")
            score += 10 * (satisfied / max(1, len(required_subjects)))
            if satisfied == len(required_subjects):
                matched.append("All key subjects met")

    if level == "Diploma":
        min_cgpa = _field(rule, "min_cgpa")
        cgpa = _to_float(student_input.get("cgpa"), 0.0)
        if min_cgpa:
            min_cgpa_value = _to_float(min_cgpa)
            ratio = min(1.25, cgpa / min_cgpa_value if min_cgpa_value > 0 else 1)
            score = min(25.0, ratio * 20)
            if cgpa > min_cgpa_value + 0.1:
                matched.append("CGPA above baseline")
            elif cgpa >= min_cgpa_value:
                borderline.append("CGPA near baseline")
            else:
                missing.append("CGPA below desired range")
        else:
            score = 18.0

    return ScoreDetail(min(score, 25.0), matched, borderline, missing)


def score_budget(rule: Any, student_input: dict[str, Any]) -> ScoreDetail:
    budget_monthly = int(student_input.get("budget_monthly") or 0)
    budget_min = _field(rule, "budget_min")
    budget_max = _field(rule, "budget_max")

    matched: list[str] = []
    borderline: list[str] = []
    missing: list[str] = []

    if not budget_min and not budget_max:
        return ScoreDetail(15.0, ["Budget flexible"], [], [])

    if budget_min and budget_monthly < int(budget_min):
        gap_ratio = budget_monthly / float(budget_min)
        if gap_ratio >= 0.85:
            return ScoreDetail(10.0, [], ["Budget slightly tight"], ["Consider scholarship or part-time support"])
        return ScoreDetail(2.0, [], [], ["Budget significantly below pathway cost"])

    if budget_max and budget_monthly > int(budget_max):
        return ScoreDetail(14.0, ["Budget exceeds expected cost range"], [], [])

    return ScoreDetail(20.0, ["Budget aligned with pathway"], [], [])


def score_english(rule: Any, student_input: dict[str, Any]) -> ScoreDetail:
    required = _field(rule, "english_min")
    actual = student_input.get("english_self", "Beginner")
    test_score = student_input.get("english_test_score")

    if not required:
        base = 10.0
        if isinstance(test_score, (int, float)) and test_score >= 75:
            base += 3.0
        return ScoreDetail(base, ["No strict English minimum"], [], [])

    req = ENGLISH_LEVELS.get(required, 2)
    got = ENGLISH_LEVELS.get(actual, 0)

    if got >= req:
        bonus = 3.0 if isinstance(test_score, (int, float)) and test_score >= 75 else 0.0
        label = "English above minimum" if got > req else "English meets minimum"
        return ScoreDetail(min(15.0, 12.0 + bonus), [label], [], [])

    if got == req - 1:
        return ScoreDetail(7.0, [], ["English one level below requirement"], ["Strengthen English proficiency"])

    return ScoreDetail(2.0, [], [], ["English below pathway baseline"])


def score_constraints(rule: Any, student_input: dict[str, Any]) -> ScoreDetail:
    constraints = _field(rule, "constraints_json") or {}
    matched: list[str] = []
    borderline: list[str] = []
    missing: list[str] = []

    score = 10.0

    needs_scholarship = bool(student_input.get("scholarship_needed", False))
    scholarship_band = (_field(rule, "scholarship_likelihood") or "Medium").lower()
    if needs_scholarship:
        if scholarship_band == "high":
            matched.append("Scholarship-friendly pathway")
        elif scholarship_band == "medium":
            borderline.append("Scholarship possible but competitive")
            score -= 2.5
        else:
            missing.append("Low scholarship likelihood")
            score -= 5.0

    needs_part_time = bool(student_input.get("need_work_part_time", False))
    rule_allows_part_time = constraints.get("work_part_time_ok", True)
    if needs_part_time and not rule_allows_part_time:
        missing.append("Part-time work not recommended for this pathway")
        score -= 4.0
    elif needs_part_time and rule_allows_part_time:
        matched.append("Part-time compatible")

    urgency = student_input.get("timeline_urgency", "normal")
    if urgency == "urgent" and constraints.get("timeline_fast_track", False):
        matched.append("Fast-track timeline fit")
    elif urgency == "urgent":
        borderline.append("Timeline may require bridging steps")
        score -= 1.5

    if student_input.get("family_constraints", "none") != "none":
        borderline.append("Family constraints require planning")
        score -= 1.0

    return ScoreDetail(max(score, 0.0), matched, borderline, missing)


def compute_fit_score(rule: Any, student_input: dict[str, Any]) -> dict[str, Any]:
    interest = score_interest(rule, student_input)
    academic = score_academic(rule, student_input)
    budget = score_budget(rule, student_input)
    english = score_english(rule, student_input)
    constraints = score_constraints(rule, student_input)

    fit_score = round(
        interest.score + academic.score + budget.score + english.score + constraints.score,
        2,
    )

    matched = interest.matched + academic.matched + budget.matched + english.matched + constraints.matched
    borderline = interest.borderline + academic.borderline + budget.borderline + english.borderline + constraints.borderline
    missing = interest.missing + academic.missing + budget.missing + english.missing + constraints.missing

    ranking_reason = (
        f"Priority {int(_field(rule, 'priority_weight', 0))}; "
        f"interest {interest.score:.1f}, academic {academic.score:.1f}, "
        f"budget {budget.score:.1f}, english {english.score:.1f}, constraints {constraints.score:.1f}."
    )

    return {
        "fit_score": fit_score,
        "component_scores": {
            "interest": round(interest.score, 2),
            "academic": round(academic.score, 2),
            "budget": round(budget.score, 2),
            "english": round(english.score, 2),
            "constraints": round(constraints.score, 2),
        },
        "explanation": {
            "matched_conditions": matched,
            "borderline_conditions": borderline,
            "missing_conditions": missing,
            "ranking_reason": ranking_reason,
        },
    }


def compute_readiness_score(student_input: dict[str, Any]) -> dict[str, Any]:
    academic_score = 0.0
    level = student_input.get("student_level")
    if level == "SPM":
        credits = int(student_input.get("spm_credits") or 0)
        academic_score = min(40.0, (credits / 8.0) * 40.0)
    if level == "Diploma":
        cgpa = _to_float(student_input.get("cgpa"), 0.0)
        academic_score = min(40.0, (cgpa / 4.0) * 40.0)

    english_level = ENGLISH_LEVELS.get(student_input.get("english_self", "Beginner"), 0)
    english_score = {0: 10.0, 1: 18.0, 2: 25.0}.get(english_level, 10.0)
    test_score = student_input.get("english_test_score")
    if isinstance(test_score, (int, float)):
        if test_score >= 75:
            english_score = min(25.0, english_score + 3.0)
        elif test_score < 50:
            english_score -= 2.0

    budget_monthly = int(student_input.get("budget_monthly") or 0)
    budget_score = 20.0 if budget_monthly >= 1500 else 12.0 if budget_monthly >= 800 else 6.0

    checklist = student_input.get("preparedness_checklist") or []
    checklist_score = min(15.0, (len(checklist) / 5.0) * 15.0)

    total = int(round(min(100.0, academic_score + english_score + budget_score + checklist_score)))

    return {
        "readiness_score": total,
        "breakdown": {
            "academic": round(academic_score, 2),
            "english": round(english_score, 2),
            "budget": round(budget_score, 2),
            "preparedness": round(checklist_score, 2),
        },
    }


def build_action_plan(student_input: dict[str, Any], missing_items: list[str]) -> dict[str, list[str]]:
    seven_day = [
        "Shortlist two realistic pathways and discuss with a counselor/mentor.",
        "Collect latest academic transcript and supporting documents.",
        "Draft a simple CV and personal statement outline.",
    ]

    thirty_day = [
        "Follow a weekly English improvement routine (speaking + writing).",
        "Build one portfolio artifact relevant to your target field.",
        "Contact at least 3 institutions for entry and cost clarification.",
        "Track scholarship deadlines and required documents.",
    ]

    if any("English" in item for item in missing_items):
        seven_day.append("Take a free English placement test and set a target score.")

    if student_input.get("scholarship_needed"):
        thirty_day.append("Prepare scholarship narrative and referee contact list.")

    if student_input.get("need_work_part_time"):
        thirty_day.append("Map study schedule with legal and institution work limits.")

    return {
        "seven_day_actions": seven_day[:5],
        "thirty_day_plan": thirty_day[:6],
    }


def build_recovery_plan(student_input: dict[str, Any], rejection_reasons: list[str], fallback_rules: list[Any]) -> dict[str, Any]:
    blocked_inputs = sorted(set(rejection_reasons))[:6]
    steps = [
        "Improve the weakest academic prerequisite for your target pathway.",
        "Increase budget flexibility via scholarships, grants, or part-time planning.",
        "Strengthen English readiness with measurable weekly targets.",
        "Prioritize local pathways first, then reassess overseas options.",
        "Review constraints with a counselor to widen feasible options.",
    ]

    alternatives = []
    for rule in fallback_rules[:3]:
        alternatives.append(
            {
                "pathway_title": _field(rule, "pathway_title"),
                "summary": _field(rule, "pathway_summary"),
                "cost_estimate_text": _field(rule, "cost_estimate_text"),
            }
        )

    return {
        "blocked_inputs": blocked_inputs,
        "unlock_steps": steps,
        "alternative_local_pathways": alternatives,
    }


def _best_intake_delta(intake_terms: list[str]) -> int | None:
    current_month = datetime.utcnow().month
    deltas: list[int] = []
    for term in intake_terms:
        month_num = MONTH_TO_NUM.get(str(term).strip().lower())
        if not month_num:
            continue
        delta = (month_num - current_month) % 12
        deltas.append(delta)
    if not deltas:
        return None
    return min(deltas)


def _intake_window_fit(intake_window: str, intake_terms: list[str]) -> tuple[float, str]:
    delta = _best_intake_delta(intake_terms)
    if delta is None:
        return 6.0, "Intake timing available on request"

    if intake_window == "next_3_months":
        if delta <= 3:
            return 15.0, "Intake aligns with your 0-3 month timeline"
        return 4.0, "Intake may be later than your preferred immediate timeline"
    if intake_window == "next_6_12_months":
        if 4 <= delta <= 12:
            return 15.0, "Intake fits your 6-12 month planning window"
        return 10.0, "Intake available earlier than planned"
    if intake_window == "flexible_local":
        return 12.0, "Timeline is flexible with local-first focus"
    return 10.0, "Intake timing is generally compatible"


def _score_university_option(program: Any, student_input: dict[str, Any], pathway_tags: set[str]) -> dict[str, Any] | None:
    if not _field(program, "active", True):
        return None

    level = student_input.get("student_level")
    program_level = str(_field(program, "program_level", "") or "")
    if level == "SPM" and program_level not in {"Foundation", "Diploma"}:
        return None
    if level == "Diploma" and program_level not in {"Bachelor", "Top-up"}:
        return None

    country = str(_field(program, "country", "Malaysia") or "Malaysia")
    preference = student_input.get("destination_preference", "malaysia_only")
    selected_destinations = _norm_set(student_input.get("destination_tags") or ["Malaysia"])
    if preference == "malaysia_only" and country.lower() != "malaysia":
        return None
    if preference == "open_overseas" and selected_destinations and country.lower() not in selected_destinations and country.lower() != "malaysia":
        return None

    reasons: list[str] = []
    cautions: list[str] = []
    score = 0.0

    program_tags = _norm_set(_as_list(_field(program, "field_tags", [])))
    student_interest = _norm_set(_as_list(student_input.get("interest_tags", [])))
    specific_interest = str(student_input.get("specific_program_interest") or "").strip().lower()
    if specific_interest and specific_interest != "general":
        student_interest.add(specific_interest)
    if pathway_tags:
        student_interest |= pathway_tags

    overlap = program_tags & student_interest
    if overlap:
        score += min(30.0, 12.0 + (len(overlap) * 7.0))
        reasons.append(f"Program fit: {', '.join(sorted(overlap))}")
    else:
        score += 6.0
        cautions.append("Program specialization may not fully match stated interests")

    req = _as_dict(_field(program, "admission_requirements_json", {}))
    if level == "SPM":
        credits = int(student_input.get("spm_credits") or 0)
        required = int(req.get("min_spm_credits") or 0)
        if required and credits < required:
            return None
        if required:
            score += 18.0 if credits >= required + 1 else 14.0
            reasons.append(f"SPM credits meet baseline ({credits}/{required}+)")
    if level == "Diploma":
        cgpa = _to_float(student_input.get("cgpa"), 0.0)
        required_cgpa = _to_float(req.get("min_cgpa"), 0.0)
        if required_cgpa and cgpa < required_cgpa:
            return None
        if required_cgpa:
            score += 18.0 if cgpa >= required_cgpa + 0.2 else 14.0
            reasons.append(f"CGPA meets baseline ({cgpa:.2f}/{required_cgpa:.2f}+)")

    english_self = student_input.get("english_self", "Beginner")
    required_english = str(req.get("english_min_level") or "Intermediate")
    if english_meets_requirement(english_self, required_english):
        score += 10.0
        reasons.append("English level matches entry expectation")
    else:
        if ENGLISH_LEVELS.get(english_self, 0) + 1 < ENGLISH_LEVELS.get(required_english, 1):
            return None
        score += 5.0
        cautions.append("English readiness is close to threshold")

    ielts_min = _to_float(_field(program, "ielts_min") or req.get("ielts_min"), 0.0)
    toefl_min = int(_field(program, "toefl_min") or req.get("toefl_min") or 0)
    ielts_score = _to_float(student_input.get("ielts_score"), 0.0)
    toefl_score = int(student_input.get("toefl_score") or 0)
    if ielts_min > 0:
        if ielts_score and ielts_score >= ielts_min:
            score += 6.0
            reasons.append(f"IELTS aligns ({ielts_score:.1f}/{ielts_min:.1f})")
        elif not ielts_score:
            cautions.append(f"IELTS {ielts_min:.1f} may be required")
    if toefl_min > 0:
        if toefl_score and toefl_score >= toefl_min:
            score += 4.0
            reasons.append(f"TOEFL aligns ({toefl_score}/{toefl_min})")
        elif not toefl_score:
            cautions.append(f"TOEFL {toefl_min} may be required")

    budget_yearly = int(student_input.get("budget_monthly") or 0) * 12
    tuition_min = _field(program, "tuition_yearly_min_myr")
    tuition_max = _field(program, "tuition_yearly_max_myr")
    if tuition_min:
        tuition_min = int(tuition_min)
        if budget_yearly >= tuition_min:
            score += 15.0
            reasons.append("Budget aligns with estimated tuition")
        elif budget_yearly >= int(tuition_min * 0.8):
            score += 9.0
            cautions.append("Budget slightly tight; scholarship/loan planning needed")
        else:
            return None
    elif tuition_max:
        score += 10.0

    intake_score, intake_reason = _intake_window_fit(student_input.get("intake_window", ""), _as_list(_field(program, "intake_terms", [])))
    score += intake_score
    reasons.append(intake_reason)

    scholarship_needed = bool(student_input.get("scholarship_needed"))
    if scholarship_needed and _field(program, "ptptn_eligible", False):
        score += 5.0
        reasons.append("PTPTN-eligible indicator supports financing pathway")

    match_score = round(min(100.0, score), 2)
    tuition_text = "Tuition on request"
    if tuition_min and tuition_max:
        tuition_text = f"RM {int(tuition_min):,} - RM {int(tuition_max):,} per year"
    elif tuition_min:
        tuition_text = f"From RM {int(tuition_min):,} per year"
    elif tuition_max:
        tuition_text = f"Up to RM {int(tuition_max):,} per year"

    sources = _as_list(_field(program, "source_codes", []))
    source_urls = _as_dict(_field(program, "source_urls_json", {}))
    source_trace = [{"source": code, "url": source_urls.get(code, "")} for code in sources]

    return {
        "program_code": _field(program, "program_code"),
        "university_name": _field(program, "university_name"),
        "program_name": _field(program, "program_name"),
        "program_level": program_level,
        "country": country,
        "intake_terms": _as_list(_field(program, "intake_terms", [])),
        "application_deadline_text": _field(program, "application_deadline_text"),
        "application_url": _field(program, "application_url"),
        "contact_email": _field(program, "contact_email"),
        "ptptn_eligible": bool(_field(program, "ptptn_eligible", False)),
        "mohe_listed": bool(_field(program, "mohe_listed", False)),
        "qs_overall_rank": _field(program, "qs_overall_rank"),
        "tuition_yearly_text": tuition_text,
        "match_score": match_score,
        "fit_reasons": reasons[:5],
        "cautions": cautions[:4],
        "source_trace": source_trace,
    }


def build_university_matches(recommendations: list[dict[str, Any]], student_input: dict[str, Any], university_programs: list[Any]) -> list[dict[str, Any]]:
    aggregate: list[dict[str, Any]] = []
    for rec in recommendations:
        pathway_tags = _norm_set(_as_list(rec.get("_rule_interest_tags") or []))
        options: list[dict[str, Any]] = []
        for program in university_programs:
            scored = _score_university_option(program, student_input, pathway_tags)
            if scored:
                options.append(scored)
        options.sort(key=lambda item: item["match_score"], reverse=True)
        top_options = options[:3]
        rec["university_options"] = top_options
        aggregate.extend(top_options[:2])

    dedup: dict[str, dict[str, Any]] = {}
    for item in aggregate:
        key = f"{item.get('university_name')}::{item.get('program_name')}"
        existing = dedup.get(key)
        if not existing or item["match_score"] > existing["match_score"]:
            dedup[key] = item

    top_global = sorted(dedup.values(), key=lambda item: item["match_score"], reverse=True)[:8]
    return top_global


def evaluate_rules(
    rules: list[Any],
    student_input: dict[str, Any],
    top_n: int = 5,
    university_programs: list[Any] | None = None,
) -> dict[str, Any]:
    eligible: list[dict[str, Any]] = []
    rejection_reasons: list[str] = []

    for rule in rules:
        passed, matched, borderline, missing = evaluate_rule_gate(rule, student_input)
        if not passed:
            rejection_reasons.extend(missing)
            continue

        scored = compute_fit_score(rule, student_input)
        scored["explanation"]["matched_conditions"] = matched + scored["explanation"]["matched_conditions"]
        scored["explanation"]["borderline_conditions"] = borderline + scored["explanation"]["borderline_conditions"]
        scored["explanation"]["missing_conditions"] = missing + scored["explanation"]["missing_conditions"]

        eligible.append(
            {
                "rule_id": _field(rule, "rule_id"),
                "pathway_title": _field(rule, "pathway_title"),
                "pathway_summary": _field(rule, "pathway_summary"),
                "cost_estimate_text": _field(rule, "cost_estimate_text"),
                "visa_note": _field(rule, "visa_note"),
                "scholarship_likelihood": _field(rule, "scholarship_likelihood"),
                "readiness_gaps": _field(rule, "readiness_gaps", []),
                "next_steps": _field(rule, "next_steps"),
                "priority_weight": int(_field(rule, "priority_weight", 0)),
                "_rule_interest_tags": _field(rule, "interest_tags", []),
                **scored,
            }
        )

    eligible.sort(key=lambda x: (x["fit_score"], x["priority_weight"]), reverse=True)

    readiness = compute_readiness_score(student_input)

    if not eligible:
        fallback_local = [
            r for r in rules if _field(r, "student_level") == student_input.get("student_level") and "malaysia" in _norm_set(_field(r, "destination_tags"))
        ]
        fallback_local.sort(key=lambda r: int(_field(r, "priority_weight", 0)), reverse=True)

        recovery = build_recovery_plan(student_input, rejection_reasons, fallback_local)
        action_plan = build_action_plan(student_input, rejection_reasons)
        top_universities: list[dict[str, Any]] = []
        if university_programs:
            seeded = [{"_rule_interest_tags": student_input.get("interest_tags", [])}]
            top_universities = build_university_matches(seeded, student_input, university_programs)[:5]

        return {
            "no_match": True,
            "readiness": readiness,
            "recommendations": [],
            "top_university_options": top_universities,
            "recovery_plan": recovery,
            **action_plan,
        }

    recommendations = eligible[: max(3, min(top_n, len(eligible)))]
    aggregate_missing = []
    for item in recommendations:
        aggregate_missing.extend(item["explanation"]["missing_conditions"])
    action_plan = build_action_plan(student_input, aggregate_missing)

    for item in recommendations:
        item["readiness_score"] = readiness["readiness_score"]

    top_universities: list[dict[str, Any]] = []
    if university_programs:
        top_universities = build_university_matches(recommendations, student_input, university_programs)
        if top_universities:
            uni_names = [item.get("university_name", "") for item in top_universities[:3] if item.get("university_name")]
            if uni_names:
                shortlist = ", ".join(uni_names)
                action_plan["seven_day_actions"] = [
                    f"Shortlist these universities for action: {shortlist}.",
                    "Open each official application page and record required documents.",
                    "Email admissions teams to confirm latest intake and entry requirements.",
                ] + action_plan["seven_day_actions"][:2]
                action_plan["thirty_day_plan"] = [
                    "Complete a personal statement draft tailored to your top 3 programs.",
                    "Prepare certified academic transcripts and English test evidence.",
                    "Submit at least 2 applications before the earliest deadline shown.",
                ] + action_plan["thirty_day_plan"][:3]

    return {
        "no_match": False,
        "readiness": readiness,
        "recommendations": recommendations,
        "top_university_options": top_universities,
        "recovery_plan": None,
        **action_plan,
    }
