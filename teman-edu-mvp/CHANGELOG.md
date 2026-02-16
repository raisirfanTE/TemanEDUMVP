# Changelog

## 2026-02-15 - Chat-first Student Refactor

### What changed
- Replaced student 10-step wizard path with a chatbot-style progressive intake flow.
- Added canonical `student_profile` state and helper functions:
  - `render_chat()`
  - `render_chat_message()`
  - `next_question()`
  - `validate_answer()`
  - `update_profile()`
  - `compute_progress()`
- Added mapping layer `_profile_to_engine_inputs()` to keep compatibility with deterministic engine inputs.
- Kept deterministic logic core intact in `logic.py`:
  - `evaluate_rule_gate`
  - `compute_fit_score`
  - `compute_readiness_score`
  - `build_university_matches`
  - `evaluate_rules`
- Switched student default page to `student-chat`.
- Added dedicated `results` page with simplified student-first sections:
  - Readiness Snapshot
  - Top 3 Pathways (Safe / Target / Aspirational)
  - University Shortlist
  - 90-day Action Plan
  - Explainability
  - Consent-gated Save + Export
- Removed student left sidebar layout and moved counselor/admin entry points to subtle footer links on student pages.
- Kept counselor/admin functionality intact.
- Added lightweight Alumni Insights using seeded `content_snippets` keys (no paid APIs, no forum).
- Updated PDF export structure to reflect readiness snapshot + top pathways + 90-day plan.

### Why
- Reduce cognitive load and improve mobile usability with conversational intake.
- Keep trust-first and explainable deterministic recommendations.
- Preserve existing Postgres persistence and admin/counselor workflows while prioritizing student UX.

## Future improvements backlog
1. Add structured conversation transcript persistence for resumable cross-device chat.
2. Add richer alumni insights table + moderation workflow (if product scope expands).
3. Add deterministic deadline calculator by intake month/year and country.
4. Add deeper test coverage for chat branching, mapping, and refresh reconstruction.
5. Add comparative shortlist mode (side-by-side university comparison).
