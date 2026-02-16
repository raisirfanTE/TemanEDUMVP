from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _safe_text(value: Any) -> str:
    if value is None:
        return "-"
    return str(value)


def build_pdf_report(
    profile: dict[str, Any],
    results: dict[str, Any],
    disclaimers: list[str],
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="TemanEDU Report")
    styles = getSampleStyleSheet()
    normal = styles["BodyText"]
    heading = styles["Heading2"]

    story = []
    story.append(Paragraph("TemanEDU Readiness Report", styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()} UTC", normal))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Student Profile Summary", heading))
    for key in [
        "student_level",
        "interest_tags",
        "budget_monthly",
        "english_self",
        "destination_preference",
    ]:
        story.append(Paragraph(f"{key}: {_safe_text(profile.get(key))}", normal))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Readiness Snapshot", heading))
    readiness = results.get("readiness", {})
    story.append(Paragraph(f"Readiness score: {_safe_text(readiness.get('readiness_score'))}/100", normal))
    breakdown = readiness.get("breakdown", {})
    story.append(Paragraph(f"Academic: {_safe_text(breakdown.get('academic'))}", normal))
    story.append(Paragraph(f"English: {_safe_text(breakdown.get('english'))}", normal))
    story.append(Paragraph(f"Budget: {_safe_text(breakdown.get('budget'))}", normal))
    story.append(Paragraph(f"Preparedness: {_safe_text(breakdown.get('preparedness'))}", normal))
    story.append(Spacer(1, 8))

    recommendations = results.get("recommendations", [])
    top_universities = results.get("top_university_options", [])
    if top_universities:
        story.append(Paragraph("Apply-Ready University Shortlist", heading))
        for idx, option in enumerate(top_universities[:5], start=1):
            story.append(
                Paragraph(
                    f"{idx}. {_safe_text(option.get('program_name'))} @ {_safe_text(option.get('university_name'))} ({_safe_text(option.get('country'))})",
                    styles["Heading3"],
                )
            )
            story.append(Paragraph(f"Match score: {_safe_text(option.get('match_score'))}", normal))
            story.append(Paragraph(f"Tuition: {_safe_text(option.get('tuition_yearly_text'))}", normal))
            story.append(Paragraph(f"Intakes: {', '.join(option.get('intake_terms', [])) or '-'}", normal))
            story.append(Paragraph(f"Application timeline: {_safe_text(option.get('application_deadline_text'))}", normal))
            story.append(Paragraph(f"Application URL: {_safe_text(option.get('application_url'))}", normal))
            story.append(Paragraph(f"Admissions contact: {_safe_text(option.get('contact_email'))}", normal))
            story.append(Spacer(1, 8))

    if recommendations:
        story.append(Paragraph("Top Pathways (Safe / Target / Aspirational)", heading))
        labels = ["Safe", "Target", "Aspirational"]
        for idx, rec in enumerate(recommendations[:3], start=1):
            label = labels[idx - 1] if idx <= len(labels) else f"Option {idx}"
            story.append(Paragraph(f"{idx}. [{label}] {_safe_text(rec.get('pathway_title'))}", styles["Heading3"]))
            story.append(Paragraph(f"Fit score: {_safe_text(rec.get('fit_score'))}", normal))
            story.append(Paragraph(_safe_text(rec.get("pathway_summary")), normal))
            story.append(Paragraph(f"Cost: {_safe_text(rec.get('cost_estimate_text'))}", normal))
            story.append(Paragraph(f"Scholarship likelihood: {_safe_text(rec.get('scholarship_likelihood'))}", normal))

            exp = rec.get("explanation", {})
            matched = ", ".join(exp.get("matched_conditions", [])[:5])
            borderline = ", ".join(exp.get("borderline_conditions", [])[:4])
            missing = ", ".join(exp.get("missing_conditions", [])[:4])
            story.append(Paragraph(f"Why it fits: {matched or '-'}", normal))
            story.append(Paragraph(f"Borderline: {borderline or '-'}", normal))
            story.append(Paragraph(f"Missing: {missing or '-'}", normal))
            story.append(Paragraph(f"Readiness gaps: {', '.join(rec.get('readiness_gaps', [])) or '-'}", normal))
            story.append(Paragraph(f"Next steps: {_safe_text(rec.get('next_steps'))}", normal))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("Readiness Recovery Plan", heading))
        recovery = results.get("recovery_plan", {})
        blocked = ", ".join(recovery.get("blocked_inputs", []))
        story.append(Paragraph(f"Blocked inputs: {blocked or '-'}", normal))
        for step in recovery.get("unlock_steps", []):
            story.append(Paragraph(f"- {step}", normal))
        story.append(Spacer(1, 8))

    ninety_day_plan = results.get("ninety_day_plan", {})
    if ninety_day_plan:
        story.append(Paragraph("90-Day Action Plan", heading))
        for phase, items in ninety_day_plan.items():
            story.append(Paragraph(phase, styles["Heading3"]))
            for action in items:
                story.append(Paragraph(f"- {action}", normal))
    else:
        story.append(Paragraph("7-Day Actions", heading))
        for action in results.get("seven_day_actions", []):
            story.append(Paragraph(f"- {action}", normal))
        story.append(Paragraph("30-Day Plan", heading))
        for action in results.get("thirty_day_plan", []):
            story.append(Paragraph(f"- {action}", normal))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Disclaimers", heading))
    for text in disclaimers:
        story.append(Paragraph(f"- {_safe_text(text)}", normal))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def build_json_summary(session_payload: dict[str, Any]) -> bytes:
    return json.dumps(session_payload, indent=2, ensure_ascii=True).encode("utf-8")
