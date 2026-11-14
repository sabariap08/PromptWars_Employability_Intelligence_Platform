# AI agents and providers

The AI layer is deliberately **advisory**. Deterministic rules own scoring, readiness and prioritisation. LLMs write explanations and mentor messages grounded in facts fetched by the backend. This means the product works with no API keys and cannot hallucinate a learner's score.

## Orchestration

`backend/app/orchestration/`

- `AGENTS` — registry of the seven agent classes.
- `WORKFLOWS` — event → ordered agent chain.
- `run_workflow(event, user, payload)` — creates state `{event, user, payload, results}`, runs agents in order, and accumulates results. Agents can read earlier results (`state["results"]`), which is how handoffs work.

For each agent the orchestrator records `ai_agent_executions` and an execution summary:

- `status` (`SUCCESS`/`FAILED`), `provider`, `model`, `duration_ms`, `handoff_to`.
- `input_summary` (event + role) and a truncated `output_summary` with internal keys removed.
- An agent exception is caught and logged; the workflow **continues** so a learner action never fails because of an agent.

Unknown events are a no-op (`skipped: true`).

## Workflows

| Event | Chain | Trigger |
| --- | --- | --- |
| `registration.approved` | profile | Member approved by an administrator |
| `profile.completed` | profile → assessment | Profile reaches complete for the first time |
| `assessment.submitted` | assessment → progress_evaluation → skill_analysis → career_intelligence → learning_recommendation → ai_mentor | Attempt submitted |
| `career.changed` | career_intelligence → skill_analysis → learning_recommendation → progress_evaluation → ai_mentor | Target career set |
| `certification.added` | profile → assessment → skill_analysis → career_intelligence → learning_recommendation | Certification submitted |
| `project.added` | profile → skill_analysis → progress_evaluation → career_intelligence → assessment | Project submitted |
| `trainer.feedback` | skill_analysis → career_intelligence → learning_recommendation | Expert records feedback |

## The seven agents

### 1. Profile Intelligence Agent (`profile`)

Builds a structured summary of the learner: learner type, target career, skill/certification/project counts, onboarding state. Flags missing fields (`target_career_id`, `skills`, `learning_style`, `weekly_hours`). On `project.added`, detects declared skills, records project evidence (unverified, score 55) and stores an `ai_analysis` summary on the project. Deterministic only.

### 2. Assessment & Integrity Agent (`assessment`)

- `profile.completed` — prepares a baseline assessment if none exists.
- `assessment.submitted` — evaluates a submitted attempt if needed, recomputes skill proficiency, and reports score, topic scores, weak skills and integrity risk/flags.
- `certification.added` — creates a verification check for the certification and links it.
- `project.added` — creates a follow-up check for the project and stores its id.

Deterministic only. Integrity signals (tab switches, visibility events, client events) are scored server-side and can cap the result.

### 3. Skill Analysis Agent (`skill_analysis`)

Recomputes every learner skill from evidence, then reports skill count, verified count, strong (≥60), weak (<40) and missing skills plus total evidence. This is the explainable bridge between evidence and readiness. Deterministic only.

### 4. Career Intelligence Agent (`career_intelligence`)

Runs the deterministic readiness analysis for the target career, finds alternative careers, and asks an LLM for **two encouraging sentences** using only supplied facts (career, readiness, strengths, gaps). Falls back to a templated explanation. Numbers always come from the rules engine.

### 5. Learning Recommendation Agent (`learning_recommendation`)

Owns roadmap decisions:

- No target career → skipped with a reason.
- `career.changed` or no roadmap → generate a new roadmap (preserves completed history).
- `assessment.submitted` → adapt the roadmap: low scores add remediation tasks, high scores advance/complete tasks.
- Otherwise keep the existing plan.

Returns version, completion and next tasks. Deterministic only.

### 6. Progress Evaluation Agent (`progress_evaluation`)

Computes progress aggregates, reads the latest evaluated attempt, derives weak skills and a primary skill, classifies adaptation (`remediation` <50, `advance` ≥75, else `none`), and detects a stalled plan (all tasks pending). Deterministic only; feeds the learning agent through the workflow chain.

### 7. AI Mentor Agent (`ai_mentor`)

Produces a short learner-facing update for the triggering event, grounded in `context_service.build(user)` (readiness, career, next tasks). Writes the message as an in-app notification. Uses an LLM when configured, otherwise `mentor_service.explain_change` templates. Also powers interactive chat via `POST /api/mentor/chat`, which is rate limited and uses the same grounded context.

## Provider layer

`backend/app/ai_providers/`

| Key | Adapter | Configured when | Default model |
| --- | --- | --- | --- |
| `groq` | Groq (OpenAI-compatible) | `GROQ_API_KEY` | `openai/gpt-oss-20b` |
| `gemini` | Google Gemini | `GEMINI_API_KEY` | `gemini-1.5-flash` |
| `openrouter` | OpenRouter | `OPENROUTER_API_KEY` | `meta-llama/llama-3.1-8b-instruct` |
| `huggingface` | Hugging Face Inference API | `HF_API_KEY` | `meta-llama/Llama-3.1-8B-Instruct` |
| `ollama` | Ollama (local or Cloud) | `OLLAMA_ENABLED` | `llama3.1` |

Relevant configuration: `AI_PRIMARY_PROVIDER`, `AI_FALLBACK_ORDER` (comma-separated), provider API keys/models, `OLLAMA_HOST` and optional `OLLAMA_API_KEY`. Local Ollama uses `http://localhost:11434` without a key; Ollama Cloud uses `https://ollama.com` plus a Bearer key (Cloud may require credits/subscription for generation). `OLLAMA_ENABLED` defaults to off; enabling it without a reachable server shows `unreachable` in provider health.

### Routing

`ProviderManager` resolves the order as `[primary] + fallback` (deduplicated) from stored settings first, then environment. `_chain()` yields only configured providers in order. Super Admins can change routing at runtime via `PUT /api/admin/providers`; the manager is rebuilt immediately and unknown names are rejected with `INVALID_PROVIDER`.

### Failure handling

- Provider errors set `last_error` for that provider and the chain moves on.
- When every provider fails or none is configured, `FallbackProvider` returns the supplied deterministic text with `provider = deterministic-fallback`.
- `generate_json` extracts JSON, validates required keys and otherwise returns the supplied fallback object. Invalid JSON never reaches business logic.

## Prompting policy

- System prompts restrict the model to supplied facts.
- Prompts include explicit "do not invent scores/skills/courses" instructions and length limits.
- Only explanations and notification copy come from models. Scoring, readiness, roadmap structure, task selection and evidence strength are computed in Python.
- Execution summaries exclude raw prompts and sensitive personal data.

## Observability

- Admins see agents, workflow map, recent executions and aggregate stats on `/app/agents`.
- `/app/settings` shows provider health, order, models, last error and allows reordering.
- `GET /api/admin/executions?limit=…` returns recent executions and counts by status/provider.
- Logs use `eip.agents` and `eip.ai` loggers.

## Adding an agent

1. Create `backend/app/agents/my_agent.py` subclassing `BaseAgent` with `name`, `label` and `run(state)`.
2. Return a dict; include `_provider`/`_model` (and `_ai` when applicable) for observability.
3. Register it in `orchestrator.AGENTS`.
4. Add it to the relevant chains in `workflow_registry.WORKFLOWS`.
5. Add a test that runs the workflow and asserts the execution log and output shape.

## Adding a provider

1. Implement the adapter in `backend/app/ai_providers/` returning `{text, provider, model}` and raising `AIProviderError` on failure.
2. Implement `is_configured()`, `model()` and a useful `health()`.
3. Register it in `PROVIDER_CLASSES`.
4. Document the environment variables in `.env.example` and this file.
