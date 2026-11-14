# Employability Intelligence Platform (EIP)

A multi-tenant employability platform that connects universities and companies, measures learners against real job requirements, and uses seven collaborating AI agents to turn evidence into an adaptive learning plan.

Built for the **PromptWars x RTC** hackathon. Flask + MongoDB Atlas + Vanilla JS, no build step.

## Highlights

- **Two-level approvals** — the platform owner approves institutions; institutions approve their own members.
- **Explainable readiness** — deterministic, weighted scoring of verified evidence against career requirements. AI never invents scores.
- **Evidence-based assessments** — baseline, skill checks, certification and project follow-ups with server-side scoring, shuffled options, timing and integrity signals.
- **Adaptive roadmaps** — phased tasks generated from gaps, re-planned when evidence changes.
- **Seven-agent orchestration** — profile, assessment, skill analysis, career intelligence, learning recommendation, progress evaluation and AI mentor, triggered by domain events.
- **Provider-agnostic AI** — Groq, Gemini, OpenRouter, Hugging Face and Ollama behind one fallback chain. With no keys the platform still works using deterministic fallbacks.
- **Tenant isolation and audit** — organization-scoped data, role guards, CSRF, rate limiting, security headers and an audit log.
- **Demo mode** — with no MongoDB URI the app runs against an in-memory store and seeds a complete demo in seconds.

## Quick start

```bash
# 1. Dependencies
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Configuration
copy .env.example .env
# Edit .env: set SECRET_KEY. MONGODB_URI is optional (empty = in-memory demo).

# 3. Initialize (indexes + catalog + first Super Admin)
python scripts/initialize_database.py

# 4. Run
python backend/run.py
# http://127.0.0.1:5000
```

In-memory mode is **not persistent**: data resets when the server restarts. Set `MONGODB_URI` to an Atlas connection string for durable storage.

## Demo accounts

All demo accounts use the password **`Demo@12345`** (development only).

| Role | Email | Scope |
| --- | --- | --- |
| Super Admin | `superadmin@eip.local` | Whole platform |
| University admin | `rathinam.admin@eip.local` | Rathinam Technical Campus |
| Organization admin | `nova.admin@eip.local` | Nova Systems |
| Expert reviewer | `employee@eip.local` | Nova Systems (expert enabled) |
| Student | `aarav@eip.local` | Rathinam Technical Campus |

Demo seeding only runs when the `users` collection is empty. The catalog seeds whenever it is empty.

## Roles at a glance

| Role | Landing page | Main capabilities |
| --- | --- | --- |
| `SUPER_ADMIN` | `/app/platform` | Organization approvals, platform analytics, providers, catalog, agent log |
| `UNIVERSITY_ADMIN` | `/app/admin` | Institution analytics, member approvals, learners, trainer assignments |
| `ORGANIZATION_ADMIN` | `/app/admin` | Company analytics, member approvals, expert capability, assignments |
| `EMPLOYEE` | `/app/dashboard` | Learner workspace; expert review when `is_expert` is enabled |
| `STUDENT` | `/app/dashboard` | Profile, assessments, readiness, roadmap, mentor |

## Scripts

| Script | Purpose |
| --- | --- |
| `python scripts/initialize_database.py` | Create indexes, seed catalog, ensure Super Admin |
| `python scripts/create_super_admin.py` | Create or reset the Super Admin (`--reset-password`) |
| `python scripts/seed_demo_data.py` | Seed demo organizations and accounts (only when empty) |

## Tests

```bash
python -m pytest backend/tests -q
```

The suite covers authentication and CSRF, registration/verification, two-level approvals, the full learner journey (assessment → evaluation → roadmap), agent execution logging, provider routing validation, catalog administration and cross-organization isolation.

## Project layout

```
backend/
  run.py                 # Entry point
  app/
    __init__.py          # App factory, error handlers, security headers
    pages.py             # Server-rendered routes and role guards
    api/                 # 10 JSON blueprints
    services/            # Business logic (auth, approvals, assessment, learning, ...)
    repositories/        # MongoDB access, one module per domain
    orchestration/       # Agent registry, workflow map, orchestrator
    agents/              # Seven agents
    ai_providers/        # Provider manager and adapters
    security/            # Sessions, roles, CSRF, passwords, rate limiting
    database/            # Connection, indexes, seed catalog
    validators/          # Input validation
    utils/               # Response envelope, IDs, text helpers
  tests/                 # Pytest suite
frontend/
  templates/             # Jinja: public site, auth, app shell, 15 app pages
  static/css/app.css     # Design system
  static/js/             # api/ui/app/auth + one module per page
scripts/                 # Operational scripts
docs/                    # Architecture, schema, API, agents, guidelines
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — layers, request flow, tenancy, orchestration.
- [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) — collections, fields and indexes.
- [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md) — conventions and endpoint reference.
- [`docs/AI_AGENTS.md`](docs/AI_AGENTS.md) — agents, workflows, providers and fallback behaviour.
- [`docs/DEVELOPMENT_GUIDELINES.md`](docs/DEVELOPMENT_GUIDELINES.md) — conventions and extension recipes.

## Security notes

- Passwords hashed with bcrypt; session cookies are HttpOnly and SameSite=Lax.
- CSRF double-submit token required on every mutating `/api/*` request.
- Role and tenant guards on every protected endpoint; expert access requires an explicit assignment.
- Login/registration/verification are rate limited.
- Uploads are size-limited and stored under `instance/uploads`.
- Never commit `.env` or provider keys.

## License

Hackathon project. Add a license before commercial use.
