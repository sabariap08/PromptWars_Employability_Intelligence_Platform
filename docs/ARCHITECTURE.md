# Architecture

## Overview

EIP is a server-rendered Flask application with a JSON API consumed by Vanilla JS page modules. It is deliberately dependency-light: no build step, no SPA framework, no ORM. MongoDB is accessed through focused repository modules; business rules live in services; routes stay thin.

```
Browser
  Jinja page shell (role-aware)  +  static/js/pages/*.js
        │  fetch (JSON, CSRF header)
        ▼
Flask blueprints (api/*, pages.py)
        │  guards: session, role, tenant, CSRF, rate limit
        ▼
Services (auth, approvals, assessment, learning, career, mentor, analytics, ops)
        │
        ├── Repositories ── MongoDB Atlas / mongomock
        └── Orchestrator ── 7 agents ── ProviderManager (optional LLMs)
```

## Layers

### App factory (`backend/app/__init__.py`)

- Creates Flask with `frontend/templates` and `frontend/static`.
- Loads `Config` from environment, applies optional test overrides.
- Initializes MongoDB (Atlas if `MONGODB_URI` responds to `ping`, otherwise mongomock), indexes, CSRF, rate limiter and the AI `ProviderManager`.
- Registers API and page blueprints, injects template globals (`current_user`, `csrf_token`, `app_name`, `db_mode`), error handlers, security headers and seeding.

`create_app(overrides=None)` is the only supported construction path, which keeps tests and scripts consistent with the server.

### Pages (`backend/app/pages.py`)

Server-rendered routes render an empty shell; data is fetched by page JavaScript. Guards:

- `page_login_required` — redirect to `/login?next=…`.
- `page_roles_required(*roles)` — redirect to the user's dashboard.
- `/app` routes by role: Super Admin → platform, admins → institution overview, learners → dashboard.

### API (`backend/app/api/`)

Ten blueprints, all mounted under `/api`:

| Blueprint | Prefix | Purpose |
| --- | --- | --- |
| `auth_api` | `/api/auth` | CSRF token, registration, verification, session |
| `public_api` | `/api/public` | Unauthenticated catalog and organization search |
| `notifications_api` | `/api/notifications` | Inbox for every signed-in role |
| `approvals_api` | `/api/approvals` | Organization/member approvals, experts, assignments |
| `organizations_api` | `/api/organizations` | Institution context, overview, learners, trainers, audit |
| `learner_api` | `/api/learner` | Profile, skills, evidence, career, readiness, expert review |
| `assessments_api` | `/api/assessments` | Assessment generation, attempts, submission |
| `learning_api` | `/api/learning` | Roadmap, tasks, activity, resources |
| `mentor_api` | `/api/mentor` | Context, history, chat |
| `admin_api` | `/api/admin` | Platform overview, organizations, users, agents, providers, catalog |

Routes validate input, enforce guards, call one service and return the standard envelope.

### Services (`backend/app/services/`)

| Service | Responsibility |
| --- | --- |
| `auth_service` | Registration, email verification, login/logout |
| `approval_service` | Two-level approvals, expert capability, trainer assignments |
| `profile_service` | Profile bundle, certifications (upload), projects |
| `skill_service` | Skills, evidence, verification strength |
| `career_service` | Target career, readiness analysis |
| `assessment_service` | Question selection, attempts, scoring, integrity flags |
| `learning_service` | Adaptive roadmaps and task transitions |
| `progress_service` | Dashboard aggregates |
| `mentor_service` | Grounded chat with deterministic fallback |
| `context_service` | Compact learner context for the mentor and agents |
| `analytics_service` | Tenant-safe institution and platform analytics |
| `ops_service` | Notifications, audit, safe logging |

### Repositories (`backend/app/repositories/`)

One module per collection group. They contain queries only — no authorization, no business rules. This keeps tenant and role enforcement in one place (services/routes) and makes queries easy to test.

### Orchestration and agents

`workflow_registry.WORKFLOWS` maps domain events to ordered agent chains. `orchestrator.run_workflow(event, user, payload)` runs each agent, records an execution, supports handoffs, and never lets an agent failure break the user action.

Workflows:

| Event | Chain |
| --- | --- |
| `registration.approved` | profile |
| `profile.completed` | profile → assessment |
| `assessment.submitted` | assessment → progress → skill → career → learning → mentor |
| `career.changed` | career → skill → learning → progress → mentor |
| `certification.added` | profile → assessment → skill → career → learning |
| `project.added` | profile → skill → progress → career → assessment |
| `trainer.feedback` | skill → career → learning |

### AI provider layer

`ProviderManager` holds every provider adapter, resolves the configured order (primary + fallback list), and iterates only configured providers. Text and JSON generation always have deterministic fallbacks. Scored values are produced by rules, never by an LLM.

## Multi-tenancy model

- Every user except Super Admin belongs to one `organization_id`.
- Institution admins can only read and mutate records in their organization.
- Learners can only read their own profile, attempts and plans.
- Experts can review a learner when a `trainer_assignments` record exists; the assignment is the authorization, which permits cross-organization mentorship.
- Super Admin is global and sees aggregate platform data plus organization lists, not learner workspaces.

Tenant checks are centralized in `app/security/auth.py` (`require_org_access`, `require_admin_for_org`) and in service-level `_admin_scope` helpers.

## Request lifecycle (mutating API)

1. Flask `before_request` CSRF check compares `X-CSRF-Token` with the session token.
2. Rate limiter applies endpoint-specific limits.
3. Route guard resolves `current_user()`, validates role and tenant.
4. Payload is validated; invalid input raises `AppError` with a machine-readable code.
5. Service performs the change and records notifications/audit where relevant.
6. Response is `{success, message, data}` with ISO timestamps.

## Frontend architecture

- `static/js/api.js` — fetch wrapper, CSRF header injection, 401 redirect, envelope handling.
- `static/js/ui.js` — escaping, formatting, toasts, modals, badges, loading/empty states.
- `static/js/app.js` — shell behaviour: sidebar, logout, session bootstrap, notification badge.
- `static/js/auth.js` — login, demo fill, multi-mode registration, organization search, verification.
- `static/js/pages/<page>.js` — one module per page, wired to `data-page` and explicit element IDs.

The design system in `static/css/app.css` uses CSS variables, a teal/amber palette, no gradients and no icon fonts; icons are inline SVG.

## Failure behaviour

- MongoDB unreachable at startup → in-memory demo mode with a warning.
- Seeding failure → logged, app still starts.
- AI provider failure → next provider, then deterministic fallback; the execution is logged.
- Agent exception → execution logged as `FAILED`; the workflow continues.
- Email delivery failure → verification link still exposed in development.

## Extensibility seams

- Add an API area: new blueprint + service + repository; register in `api/__init__.py`.
- Add an agent: subclass the base agent, register in `orchestration/orchestrator.AGENTS`, add it to workflows.
- Add a provider: implement the base adapter, add it to `PROVIDER_CLASSES`.
- Add a page: route in `pages.py`, template extending `app/layout.html`, JS module in `static/js/pages/`.
- Add a catalog item: use the super-admin catalog endpoints; seeding stays optional.
