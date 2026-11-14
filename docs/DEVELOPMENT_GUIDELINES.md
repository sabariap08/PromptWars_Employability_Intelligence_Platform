# Development guidelines

## Environment

- Python 3.12, Windows/macOS/Linux.
- Node.js is only needed for `node --check` syntax validation of frontend JS; there is no bundler.
- MongoDB Atlas is optional. Without `MONGODB_URI` the app uses `mongomock` and seeds a demo dataset at startup.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/initialize_database.py
python backend/run.py
```

## Configuration

- All settings live in `backend/app/config/settings.py` and read environment variables; `.env` is loaded from the repository root.
- Never hardcode secrets. Never commit `.env`, provider keys or uploaded learner documents.
- Tests must not call external services: override config through `create_app({...})`.

## Project conventions

### Backend

- **Routes are thin.** Validate input, enforce guards, call one service, return `ok(...)`/raise `AppError`.
- **Business rules live in services.** Scoring, readiness, roadmap structure and authorization decisions belong there.
- **Repositories only query.** No role checks and no business branching inside `repositories/`.
- Use `current_user()` from `app/security/auth.py`; use `api_roles_required(...)` / `api_login_required` decorators. Page routes use the page equivalents in `pages.py`.
- Use `require_org_access` style helpers instead of comparing ids inline when the rule is reused.
- Return the standard envelope (`ok`, `AppError`) and machine-readable `error_code`s.
- Use the validators in `app/validators/` (`require_fields`, `validate_email`, `validate_password`, URL helpers) and `clean_text` for bounded strings.
- Generate ids with `app.utils.ids.new_id` and timestamps with `now_utc`; do not use `datetime.utcnow()`.
- Record operational side effects deliberately: `ops_service.notify`, `ops_service.audit`, `operations_repo.record_execution`.
- Keep tenant data out of cross-tenant responses. The Super Admin sees aggregates and organization lists, not learner workspaces.
- No comments unless they explain non-obvious *why*.

### Frontend

- No framework and no build step. One module per page under `frontend/static/js/pages/`, selected by the template's `data-page`.
- Always go through `EIP.api` (`static/js/api.js`) so CSRF headers, 401 redirects and envelope handling stay consistent.
- Escape all user-provided text with the helpers in `ui.js`; never interpolate raw HTML from API data.
- Use the existing design tokens in `app.css`; do not add gradients, glassmorphism, icon fonts or emojis. Icons are inline SVG.
- Use the shared helpers (`EIP.toast`, `EIP.confirmModal`, `EIP.promptModal`, `EIP.detailModal`, `EIP.emptyState`) before inventing new UI patterns.
- Keep element ids explicit and stable; page JS wires to ids. When changing a template, grep the matching JS module for the id.

## Common pitfalls

- **CSRF after auth changes.** Login and logout reset the session. Refetch `GET /api/auth/csrf` (or use the token returned by login) before the next mutation.
- **Two different assessment identifiers.** `POST /api/assessments/baseline` returns the new assessment with `_id`; list items expose `assessment_id`. Starting an attempt needs the id from the correct shape.
- **Option format.** Attempt questions contain `options` as `{key, text}` objects after shuffling. Do not assume an array of strings.
- **Result items** do not include `question_id`; do not depend on it in the UI.
- **Demo mode is ephemeral.** Anything you create vanishes on restart unless MongoDB is configured.
- **Expert access is assignment-based.** `is_expert` alone is insufficient; a `trainer_assignments` row must exist, and it may legitimately cross organizations.
- **Rate limiter.** Tests set `RATELIMIT_ENABLED: False`. Do not weaken production limits to make tests pass.
- **Seeding is conditional.** Demo users seed only when `users` is empty; catalog seeds whenever empty. Do not make seeding destructive.

## Adding an endpoint

1. Add the route to the relevant blueprint in `backend/app/api/`.
2. Apply the narrowest guard (`api_login_required`, `api_roles_required(...)`), then a tenant check.
3. Validate and bound input.
4. Implement the rule in a service; add repository queries if needed.
5. Return `ok(data, message)`; raise `AppError(message, code, status)` on failure.
6. Document it in `docs/API_DOCUMENTATION.md`.
7. Add a test in `backend/tests/`.

## Adding a page

1. Add a guarded route in `backend/app/pages.py`.
2. Create the template extending `app/layout.html`, with a unique `data-page` and stable ids.
3. Add `frontend/static/js/pages/<page>.js` that reads `data-page` and uses `EIP.api`.
4. Include the script from the template.
5. Verify with the page smoke script concept: authenticated `GET` per role should be 200 and all referenced static assets should exist.

## Adding an agent or provider

See [`AI_AGENTS.md`](AI_AGENTS.md). Keep agent output JSON-safe and always provide a deterministic fallback.

## Testing

```bash
python -m pytest backend/tests -q
node --check frontend/static/js/api.js   # repeat for each JS file
```

Test conventions:

- Use the `app`, `client`, `login_as`, `csrf`, `post` helpers from `backend/tests/conftest.py`.
- Every test gets a fresh in-memory database (`create_app` with `MONGODB_URI: ""`).
- Assert the response envelope and `error_code`, not just status codes.
- Cover authorization boundaries explicitly: wrong role, wrong tenant, missing assignment, missing CSRF.
- Never rely on seeded ids; query or derive them through the API.

Current coverage areas: auth/verification/CSRF, two-level approvals, full learner journey (assessment → roadmap), agent execution logging and workflow output, provider routing validation, catalog administration, cross-organization isolation.

## Security checklist for changes

- [ ] Guard applied and tenant enforced.
- [ ] CSRF unchanged for new mutating routes (handled globally, but test it).
- [ ] Input bounded and escaped in the UI.
- [ ] No secrets in responses, logs or test fixtures.
- [ ] Uploads validated by extension and stored outside source paths.
- [ ] Error messages do not leak internals.
- [ ] Audit/notification added where the action matters operationally.

## Documentation

Keep these files in sync with behaviour:

- `README.md` — setup, demo accounts, scripts.
- `docs/ARCHITECTURE.md` — layers and cross-cutting behaviour.
- `docs/DATABASE_SCHEMA.md` — collections and fields.
- `docs/API_DOCUMENTATION.md` — endpoints, payloads, errors.
- `docs/AI_AGENTS.md` — agents, workflows, providers.
- `docs/DEVELOPMENT_GUIDELINES.md` — this file.

## Git hygiene

- Small, focused commits with imperative messages.
- Run tests and JS syntax checks before committing.
- Do not commit `.env`, `instance/uploads`, `__pycache__`, `.pytest_cache` or generated artifacts.
- Do not commit or push unless explicitly asked.
