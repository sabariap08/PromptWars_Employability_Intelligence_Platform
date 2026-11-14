# API documentation

Base URL: `http://127.0.0.1:5000/api`

## Conventions

### Response envelope

Success:

```json
{"success": true, "message": "Profile saved.", "data": { ... }}
```

Failure:

```json
{"success": false, "message": "Human-readable reason.", "error_code": "VALIDATION_ERROR", "details": { ... }}
```

HTTP status codes are meaningful: `200`, `201`, `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`.

### Authentication

Session cookie based. Sign in with `POST /auth/login`; the session is refreshed and the response `data` contains `user`, `organization`, `department` and a fresh `csrf_token`.

### CSRF

All mutating `/api/*` requests (`POST`, `PUT`, `PATCH`, `DELETE`) require:

```
X-CSRF-Token: <token>
```

Fetch the token from `GET /auth/csrf` (or from the login/`me` response). The session is reset on login and logout, so always refresh the token afterwards. If the body also carries a token (for example email verification), send the CSRF token in the header and the verification token in the body.

### Pagination and filters

List endpoints accept `page` and `page_size` (bounded), plus `q` for search and domain filters such as `status`, `type` or `role`. Responses include `total`, `page`, `page_size`.

### Roles

`SUPER_ADMIN`, `UNIVERSITY_ADMIN`, `ORGANIZATION_ADMIN`, `STUDENT`, `EMPLOYEE`. "Learner roles" means `STUDENT` and `EMPLOYEE`. "Admin roles" means the three admin roles.

---

## Authentication — `/api/auth`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/csrf` | public | Issue/refresh the CSRF token |
| POST | `/register/student` | public | Student registration (rate limited) |
| POST | `/register/employee` | public | Employee registration (rate limited) |
| POST | `/register/university` | public | Institution + admin registration |
| POST | `/register/organization` | public | Company + admin registration |
| POST | `/verify-email` | public | Consume the email verification token |
| POST | `/login` | public | Start a session (rate limited) |
| POST | `/logout` | public | Clear the session |
| GET | `/me` | signed in | Current user, organization, department, fresh CSRF |

Student payload (required: `full_name, email, password, confirm_password, phone, organization_id, department_id, degree, academic_year, year_of_study, roll_number`):

```json
{
  "full_name": "Aarav Sharma",
  "email": "aarav@example.com",
  "password": "StrongPass@123",
  "confirm_password": "StrongPass@123",
  "phone": "+91 90000 00000",
  "organization_id": "org_...",
  "department_id": "dept_...",
  "degree": "B.E. Computer Science",
  "academic_year": "2023-2027",
  "year_of_study": "3",
  "roll_number": "21CSE001"
}
```

Employee payload (required: `full_name, email, password, confirm_password, phone, organization_id, department_id, designation, employment_type, years_experience`).

Institution/company payload (required: `name, official_email, city, state, country, admin_name, admin_email, password, confirm_password`; optional `subtype, industry, website, contact_number, address, registration_identifier, admin_phone, admin_designation, verification_documents`).

Verification response includes `verification {required, delivery}` and, when `EXPOSE_VERIFICATION_LINK` is enabled in development, the link to open.

Login error codes: `INVALID_CREDENTIALS` (401), `EMAIL_NOT_VERIFIED` (403), `ACCOUNT_NOT_APPROVED` (403), `ORGANIZATION_NOT_APPROVED` (403).

---

## Public catalog — `/api/public`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness and database mode |
| GET | `/organizations` | Approved organizations; filters `type`, `q` |
| GET | `/careers` | Active career roles |
| GET | `/skills` | Skill catalog |
| GET | `/resources` | Learning resources; filter `skill` |

Used by registration forms (organization and department selection) and the landing page.

---

## Notifications — `/api/notifications`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/` | signed in | `{notifications, unread}` |
| POST | `/read` | signed in | Mark one (`{"id": "..."}`) or all notifications read |

---

## Approvals — `/api/approvals`

| Method | Path | Role | Description |
| --- | --- | --- | --- |
| GET | `/organizations` | Super Admin | Pending organizations (`status`, `type`, `q`) |
| POST | `/organizations/<org_id>/approve` | Super Admin | Approve institution/company |
| POST | `/organizations/<org_id>/reject` | Super Admin | Reject with `{reason}` |
| POST | `/organizations/<org_id>/status` | Super Admin | Set `{status, reason}` (`APPROVED`, `SUSPENDED`, ...) |
| GET | `/members` | Admin roles | Members of your organization |
| POST | `/members/<user_id>/approve` | Admin roles | Approve a member |
| POST | `/members/<user_id>/reject` | Admin roles | Reject with `{reason}` |
| POST | `/experts/<user_id>` | Organization admin | `{enabled: true|false}` expert capability |
| POST | `/assignments` | Admin roles | `{trainer_id, learner_id}` create mentoring assignment |

Tenant rule: member endpoints only act on users in the caller's organization; `assign_trainer` requires the trainer and learner to share that organization. The resulting assignment authorizes cross-organization expert review later.

---

## Organization context — `/api/organizations`

Admin roles only.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/me` | Organization, departments, admin |
| GET | `/me/overview` | Tenant-scoped analytics |
| GET | `/me/learners` | Learners (`status`, `q`, pagination) |
| GET | `/me/trainers` | Approved employees with expert capability |
| POST | `/me/departments` | `{name, code}` create department |
| GET | `/me/audit` | Recent audit logs for the organization (`limit`) |

---

## Learner workspace — `/api/learner`

Learner roles unless noted.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/profile` | Profile bundle (profile, skills, certifications, projects, career) |
| POST/PUT | `/profile` | Save profile and optional `skills[]`; first completion fires `profile.completed` |
| GET | `/dashboard` | Dashboard aggregates |
| GET | `/progress` | Progress record |
| GET | `/readiness` | Readiness analysis for the target career |
| POST | `/career` | `{career_id}` set target career; fires `career.changed` |
| POST | `/skills` | `{name, level}` self-report a skill |
| DELETE | `/skills/<skill_name>` | Remove a skill and its evidence |
| GET | `/certifications` | List certifications |
| POST | `/certifications` | Multipart: `name, issuer, issued_on, skills`, optional `file`; fires `certification.added` |
| GET | `/projects` | List projects |
| POST | `/projects` | `{name, description, technologies[], repo_url}`; fires `project.added` |
| GET | `/activity` | Learning activity (`limit`) |
| GET | `/notifications` | Learner notification inbox |
| POST | `/notifications/read` | `{id?}` |
| GET | `/expert/learners` | Experts: assigned learners with readiness |
| GET | `/expert/learners/<learner_id>` | Experts: assignment-checked learner snapshot + feedback |
| POST | `/expert/feedback` | `{learner_id, skill_name, rating, feedback, task_id?}`; fires `trainer.feedback` |

Expert endpoints require `is_expert` **and** an explicit assignment to the learner. A rating ≥ 3 creates verified evidence and a 20×rating score.

Certification uploads: PDF/PNG/JPG, stored under `instance/uploads/<user_id>/`, size limited.

---

## Assessments — `/api/assessments`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | List learner assessments (`assessment_id`, purpose, status, score) |
| POST | `/baseline` | Prepare a baseline assessment for the learner |
| POST | `/skill-check` | `{skills: [...], title?}` prepare a targeted check |
| POST | `/<assessment_id>/start` | Create an attempt with shuffled options |
| GET | `/attempts/<attempt_id>` | Attempt with questions, expiry and remaining time |
| POST | `/attempts/<attempt_id>/submit` | Submit, evaluate, then run the assessment workflow |
| GET | `/attempts/<attempt_id>/result` | Evaluated result breakdown |
| POST | `/certifications/<cert_id>/verify` | Create a certification verification check |
| POST | `/projects/<project_id>/follow-up` | Create a project follow-up check |

Submit payload:

```json
{
  "answers": [
    {"question_id": "q_...", "selected_option": "B", "text_answer": ""}
  ],
  "integrity": {
    "tab_switch_count": 0,
    "visibility_events": 0,
    "client_events": []
  }
}
```

Notes:

- Question options are objects `{key, text}`; keys are assigned after shuffling (`A`–`F`).
- The baseline create response uses `_id` for the new assessment; list items expose `assessment_id`.
- Scoring is server-side and deterministic. Integrity signals are recorded and can cap the score.
- Result items contain `prompt, skill_name, selected_option, text_answer, correct_option, points_awarded, points_possible, correct`.

---

## Learning — `/api/learning`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/roadmap` | Active roadmap, summary and version history |
| POST | `/roadmap/generate` | Generate/replan from current gaps |
| POST | `/tasks/<task_id>` | `{action: "start"|"complete", evidence_url?}` |
| GET | `/activity` | Learning activity (`limit`) |
| GET | `/resources` | Catalog resources (`skill`) |

Generating a roadmap archives the current active plan and inserts a new version. Completed tasks become evidence; sufficient evidence can auto-complete tasks.

---

## Mentor — `/api/mentor`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/context` | Grounded learner context used by the mentor |
| GET | `/history` | Messages, suggested prompts and context |
| POST | `/chat` | `{message}`; rate limited to 30/minute |

The mentor only sees the learner's own context. Responses state the provider used and fall back to deterministic guidance when no LLM is configured.

---

## Platform admin — `/api/admin`

| Method | Path | Role | Description |
| --- | --- | --- | --- |
| GET | `/overview` | Super Admin | Platform analytics (`organizations`, `users`, `agents`, `providers`, `database_mode`) |
| GET | `/organizations` | Super Admin | All organizations (`status`, `type`, `q`, pagination) |
| GET | `/users` | Super Admin | All users (`role`, `q`, pagination); secrets stripped |
| GET | `/learner/<user_id>` | Admin roles / assigned expert | Learner snapshot with tenant guard |
| GET | `/agents` | Super Admin | Agent registry and workflow map |
| GET | `/executions` | Super Admin | Recent AI executions and stats (`limit` ≤ 200) |
| GET | `/providers` | Super Admin | Provider health/status, settings and order |
| PUT | `/providers` | Super Admin | `{primary_provider, fallback_order}`; rebuilds the manager |
| GET | `/catalog` | Super Admin | Skills, careers, resources, counts |
| POST | `/catalog/skills` | Super Admin | `{name, category?, description?}` |
| POST | `/catalog/careers` | Super Admin | Career definition (see below) |
| POST | `/catalog/resources` | Super Admin | `{title, url, provider, resource_type, skill_names, difficulty, duration_hours}` |
| POST | `/catalog/questions` | Super Admin | `{skill_name, prompt, options, correct_option, difficulty, question_type, correct_keywords, points}` |
| GET | `/audit` | Admin roles | Audit log; Super Admin may filter `org_id` |

Career payload:

```json
{
  "name": "Data Analyst",
  "description": "Turns data into decisions.",
  "experience_level": "Entry level",
  "required_skills": [{"skill_name": "SQL", "min_proficiency": 65, "weight": 3}],
  "preferred_skills": ["Power BI"],
  "certifications": ["Google Data Analytics"],
  "project_expectations": "Two end-to-end dashboards.",
  "milestones": ["Portfolio review", "Mock interview"]
}
```

Provider update validation rejects unknown provider keys with `INVALID_PROVIDER` and returns `{providers, order}` after the rebuild.

---

## Error codes

| Code | Typical status | Meaning |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Missing/invalid field |
| `INVALID_CREDENTIALS` | 401 | Wrong email/password |
| `EMAIL_NOT_VERIFIED` | 403 | Verify email first |
| `ACCOUNT_NOT_APPROVED` | 403 | Awaiting administrator approval |
| `ORGANIZATION_NOT_APPROVED` | 403 | Institution/company not approved |
| `CSRF_TOKEN_MISSING` / `CSRF_TOKEN_INVALID` | 400 | Missing/mismatched CSRF header |
| `FORBIDDEN` | 403 | Role, tenant or assignment check failed |
| `NOT_FOUND` / `ATTEMPT_NOT_FOUND` | 404 | Unknown resource |
| `NOT_EVALUATED` | 409 | Result requested before evaluation |
| `EMAIL_EXISTS` / `ORGANIZATION_EXISTS` | 409 | Duplicate registration |
| `INVALID_PROVIDER` | 422 | Unknown AI provider key |
| `RATE_LIMITED` | 429 | Too many requests |
