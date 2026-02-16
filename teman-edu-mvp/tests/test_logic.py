from logic import evaluate_rules


def base_spm_input() -> dict:
    return {
        "student_level": "SPM",
        "spm_credits": 6,
        "subjects": {"math": "B", "english": "B", "bm": "C", "science": "B"},
        "interest_tags": ["IT", "Engineering"],
        "budget_monthly": 1500,
        "english_self": "Intermediate",
        "english_test_score": 70,
        "destination_preference": "malaysia_only",
        "destination_tags": ["Malaysia"],
        "scholarship_needed": False,
        "need_work_part_time": True,
        "timeline_urgency": "normal",
        "family_constraints": "none",
        "willing_relocate": True,
        "preparedness_checklist": ["CV drafted"],
    }


def test_evaluate_rules_returns_ranked_recommendations() -> None:
    rules = [
        {
            "rule_id": "R1",
            "active": True,
            "student_level": "SPM",
            "interest_tags": ["IT", "Engineering"],
            "destination_tags": ["Malaysia"],
            "min_spm_credits": 5,
            "required_subjects_json": {"math": "C", "english": "C"},
            "min_cgpa": None,
            "budget_min": 800,
            "budget_max": 3500,
            "english_min": "Intermediate",
            "constraints_json": {"work_part_time_ok": True},
            "pathway_title": "Foundation IT",
            "pathway_summary": "Local route",
            "cost_estimate_text": "RM 800-3500/month",
            "visa_note": "General note",
            "scholarship_likelihood": "Medium",
            "readiness_gaps": ["Portfolio"],
            "next_steps": "Apply",
            "priority_weight": 9,
        },
        {
            "rule_id": "R2",
            "active": True,
            "student_level": "SPM",
            "interest_tags": ["Business"],
            "destination_tags": ["Australia"],
            "min_spm_credits": 6,
            "required_subjects_json": {"math": "C", "english": "B"},
            "min_cgpa": None,
            "budget_min": 3000,
            "budget_max": 7000,
            "english_min": "Advanced",
            "constraints_json": {"work_part_time_ok": True},
            "pathway_title": "Business Overseas",
            "pathway_summary": "Overseas route",
            "cost_estimate_text": "RM 3000-7000/month",
            "visa_note": "General note",
            "scholarship_likelihood": "Low",
            "readiness_gaps": ["English"],
            "next_steps": "Prepare",
            "priority_weight": 5,
        },
    ]

    result = evaluate_rules(rules, base_spm_input(), top_n=5)

    assert result["no_match"] is False
    assert len(result["recommendations"]) >= 1
    assert result["recommendations"][0]["rule_id"] == "R1"
    assert result["readiness"]["readiness_score"] >= 0


def test_evaluate_rules_no_match_returns_recovery_plan() -> None:
    rules = [
        {
            "rule_id": "OVERSEAS_ONLY",
            "active": True,
            "student_level": "SPM",
            "interest_tags": ["Business"],
            "destination_tags": ["UK"],
            "min_spm_credits": 8,
            "required_subjects_json": {"math": "A", "english": "A"},
            "budget_min": 5000,
            "budget_max": 12000,
            "english_min": "Advanced",
            "constraints_json": {"work_part_time_ok": False},
            "pathway_title": "Elite Overseas",
            "pathway_summary": "Difficult route",
            "cost_estimate_text": "RM 5000-12000/month",
            "visa_note": "General note",
            "scholarship_likelihood": "Low",
            "readiness_gaps": ["Funding"],
            "next_steps": "N/A",
            "priority_weight": 1,
        }
    ]

    result = evaluate_rules(rules, base_spm_input(), top_n=5)

    assert result["no_match"] is True
    assert "recovery_plan" in result
    assert len(result["recovery_plan"]["unlock_steps"]) >= 3


def test_evaluate_rules_returns_specific_university_options() -> None:
    rules = [
        {
            "rule_id": "SPM_IT_LOCAL",
            "active": True,
            "student_level": "SPM",
            "interest_tags": ["IT", "Engineering"],
            "destination_tags": ["Malaysia"],
            "min_spm_credits": 5,
            "required_subjects_json": {"math": "C", "english": "C"},
            "budget_min": 800,
            "budget_max": 3500,
            "english_min": "Intermediate",
            "constraints_json": {"work_part_time_ok": True},
            "pathway_title": "Foundation IT",
            "pathway_summary": "Local route",
            "cost_estimate_text": "RM 800-3500/month",
            "visa_note": "General note",
            "scholarship_likelihood": "Medium",
            "readiness_gaps": ["Portfolio"],
            "next_steps": "Apply",
            "priority_weight": 9,
        }
    ]

    university_programs = [
        {
            "program_code": "MY_TEST_IT_01",
            "active": True,
            "university_name": "Test University",
            "country": "Malaysia",
            "program_name": "Diploma in Information Technology",
            "program_level": "Diploma",
            "field_tags": ["IT", "Data"],
            "intake_terms": ["March", "September"],
            "application_deadline_text": "Apply 6 weeks before intake",
            "admission_requirements_json": {"student_level": "SPM", "min_spm_credits": 5, "english_min_level": "Intermediate"},
            "tuition_yearly_min_myr": 18000,
            "tuition_yearly_max_myr": 24000,
            "ielts_min": None,
            "toefl_min": None,
            "ptptn_eligible": True,
            "mohe_listed": True,
            "source_codes": ["MOHE_OFFICIAL", "PTPTN_ELIGIBLE"],
            "source_urls_json": {"MOHE_OFFICIAL": "https://www.mohe.gov.my/en/universities"},
            "application_url": "https://example.edu/apply",
            "contact_email": "admissions@example.edu",
        }
    ]

    result = evaluate_rules(rules, base_spm_input(), top_n=5, university_programs=university_programs)

    assert result["no_match"] is False
    assert result["top_university_options"]
    assert result["top_university_options"][0]["university_name"] == "Test University"
    assert result["recommendations"][0]["university_options"]
