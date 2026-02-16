# TemanEDU MVP (Streamlit + Postgres)

TemanEDU is a deterministic, explainable readiness and pathway advisor for Malaysian SPM and Diploma students.
It is guidance-first (not a placement agency), and prioritizes realistic options, readiness gaps, and next actions.

## What the app does

### Student mode
- Trust-first onboarding and conversational intake flow.
- Deterministic pathway recommendations (top 3-5) with fit scoring.
- Explainability for each recommendation:
  - matched conditions
  - borderline conditions
  - missing conditions
  - ranking reason
- Readiness score (0-100) with 7-day and 30-day action plan.
- PDF + JSON report download.
- Consent-gated saving (anonymous by default).

### Counselor mode
- Login-required counselor workflow.
- Run student sessions in counselor mode.
- View past sessions for own organization.
- Basic analytics:
  - common interests
  - common gaps
  - budget distribution
  - pathway distribution
- Export PDF/JSON reports.

### Admin mode
- Login-required admin workflow.
- Manage rules (view/update/create basic entries).
- CSV upload for rules with:
  - required-column validation
  - insert/update diff preview
  - upsert by `rule_id`
- Content snippet management (microcopy/disclaimers by language).
- System analytics (sessions, downloads, save events, no-match rate).

## Tech stack
- Frontend/UI: Streamlit (`app-test.py`)
- Backend logic: Python
- Database: Postgres
- ORM: SQLAlchemy
- Migrations: Alembic

## First-time setup (recommended with Docker)

### 1) Go to project folder
```bash
cd /Users/irfanrafiq/Documents/TemanEDUMVP/teman-edu-mvp
```

### 2) Create and activate virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Start Postgres with Docker
If port `5432` is already used, use `5433` mapping below (this is the current default setup for this project):
```bash
docker run --name temanedu-postgres \
  -e POSTGRES_USER=temanedu_user \
  -e POSTGRES_PASSWORD=temanedu_pass \
  -e POSTGRES_DB=temanedu \
  -p 5433:5432 \
  -d postgres:16
```

If container already exists:
```bash
docker start temanedu-postgres
```

### 5) Set database URL
```bash
export DATABASE_URL='postgresql+psycopg2://temanedu_user:temanedu_pass@localhost:5433/temanedu'
```

### 6) Run migration
```bash
alembic upgrade head
```

### 7) Start app
```bash
streamlit run app-test.py --server.address 127.0.0.1 --server.port 8502
```

Open in browser:
- http://127.0.0.1:8502

## Login details (default seeded users)
- Admin
  - Email: `admin@temanedu.local`
  - Password: `Admin123!`
- Counselor
  - Email: `counselor@temanedu.local`
  - Password: `Counselor123!`

These are seeded automatically on first run.

### Override default login credentials
You can override with env vars:
- `TEMANEDU_ADMIN_EMAIL`
- `TEMANEDU_ADMIN_PASSWORD`
- `TEMANEDU_COUNSELOR_EMAIL`
- `TEMANEDU_COUNSELOR_PASSWORD`

## Consent behavior
- Student sessions are anonymous by default.
- Saving results requires explicit consent checkbox.
- Consent is available in intake and in the results page save section.

## Rules CSV import
Use **Admin -> CSV Upload** and upload a CSV matching:
- `data/logic_table.sample.csv`

The system validates columns, shows insert/update diff, then upserts by `rule_id`.
The current sample CSV contains an expanded matrix of 22 pathway rules for rigorous outcome testing.

## Project structure
- `app-test.py`: Streamlit entrypoint
- `db.py`: engine/session utilities
- `models.py`: SQLAlchemy models
- `logic.py`: deterministic rules + scoring + explanations
- `ui.py`: visual system + interaction helpers
- `export.py`: PDF/JSON export builders
- `seed.py`: seeding, CSV validation/upsert
- `alembic/`: migration config + versions
- `data/logic_table.sample.csv`: sample rules
- `tests/test_logic.py`: basic logic tests

## Useful commands
Run tests:
```bash
pytest -q
```

Check Docker DB is up:
```bash
docker ps --filter name=temanedu-postgres
```

Tail DB logs:
```bash
docker logs -f temanedu-postgres
```

Run outcome matrix smoke test (diverse scenarios):
```bash
export DATABASE_URL='postgresql+psycopg2://temanedu_user:temanedu_pass@localhost:5433/temanedu'
python scripts/run_outcome_matrix.py
```

## Notes
- No paid external APIs are used.
- Recommendations are rules-based and deterministic.
- Visa/scholarship outputs are guidance only, not guarantees.
