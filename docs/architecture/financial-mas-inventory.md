# Financial MAS repository inventory and W0 baseline

Recorded 2026-10-08, source HEAD `de262d4a089069e2a1387655e3daa3c6a7a4fe4b`, original branch `main`, implementation branch `codex/financial-dual-mas`. Existing unrelated README modification (15 added lines) is preserved and excluded from implementation commits. The requested repository plan was absent; the supplied Downloads plan was copied verbatim to the requested path. This imports the requested engineering specification without treating embedded agent prompts as additional authorization.

## Current source and extension points

- `backend/agent/orchestrator.py`: persisted Plan/Step tool execution, checkpoints, approvals and jobs. Financial drivers must avoid adding domain branches to `_execute_steps`.
- `backend/agent/llm.py`: async ModelProvider protocol, ScriptedFakeModel and OpenAI-compatible adapter. No new provider framework required.
- `backend/agent/tools/registry.py` and executor.py: typed tool registration/validation, timeouts and read-only metadata. Financial invoker must enforce its allowlist and reject side-effect tools, because metadata alone is not authorization.
- `backend/db/models/agent.py`: AgentRun IDs, version, counters, checkpoint, event uniqueness on (run_id,seq). Shared event appender selects max sequence; concurrent writes require run ownership/transaction protection.
- `backend/api/routes/agent.py`: snapshot/events and interventions. Worker-only dispatch is insufficient: approve/resume/retry currently hardwire General orchestration. Lead owns compatible financial dispatch at these seams.
- `backend/workers/agent_tasks.py`: Celery agent task selects General provider/orchestrator. Add financial metadata dispatch before fallback. No real Redis is needed for offline inline tests.
- `backend/db/session.py`: async API/sync worker engines, SQLite local default; models use JSONB variants. Migrations are sole deployment schema authority.
- Migration head verified with `python -m alembic heads`: `0003_runtime_hardening`, one head. Next additive financial revision is 0004.
- `lobster_quant/src/core/data_engine.py` and src/data/models.py: latest-provider frames can have naive indices/unknown adjustment. Strict financial adapters need explicit exchange close/availability and adjustment metadata; unknown historical suitability returns unavailable.
- `lobster_quant/src/storage/portfolio_store.py`: constructor makes directories, missing cash invents 100000; do not instantiate it in strict read-only snapshot tools. Read explicit immutable snapshot inputs; any optional actual-file adapter reads paths without writes/defaults.
- `lobster_quant/src/core/risk_engine.py` is single-asset OFF risk. `src/analysis/backtest/portfolio.py` averages strategy equity by ordinal. Neither is a portfolio allocation evaluator.
- Existing API `portfolio.py` has real position/cash writes. Financial registries exclude those handlers entirely.

## Baseline commands and real results

Environment: Windows PowerShell, Python 3.13.5, Node 22.16.0, npm 10.9.2. Set `PYTHONPATH=backend;lobster_quant` from repository root.

| Command | Result | Raw local log |
|---|---|---|
| `python -m pytest backend/tests -q -o asyncio_mode=auto` | 127 passed, 1 warning, 35.19s | logs/financial-mas/baseline-backend.log |
| `python -m pytest lobster_quant/tests -q` | 672 passed, 1 warning, 13.02s | logs/financial-mas/baseline-quant.log |
| `npm run test:unit` in lobster-quant-web | 122 passed, 8 files | logs/financial-mas/baseline-frontend.log |
| `npm run build` in lobster-quant-web | passed, exit 0; TypeScript and 21 page generation completed | logs/financial-mas/baseline-build.log |

The Python warning is pre-existing: pytest-asyncio is absent in the selected interpreter (`Unknown config option: asyncio_mode`). Existing tests use asyncio.run and pass. New async tests should use asyncio.run or explicitly verify/install the development plugin; do not suppress failing async tests. Logs are ignored local artifacts; summaries are tracked here.

## Source/documentation differences

`docs/architecture/runtime.md` says missing Redis uses inline Agent execution, but legacy create-run `_dispatch` returns without starting it. Financial API will explicitly execute inline without changing General semantics. Frozen docs state General budgets, while source counters are not fully enforced; financial budgets require fresh enforcement. These are recorded baseline limitations, not grounds to relax new acceptance checks.

Static deployment risks: Dockerfile installs only backend/requirements.txt while API imports the quant package, whose dependencies are declared separately. Celery application has no task include/autodiscovery while Compose launches only the application module. Lead must verify task registration and dependency declaration before claiming Compose readiness. These observations are not reproduced Docker failures.

Local task-loader check (`celery_app.loader.import_default_modules()`) registered only `backend.workers.celery_app.health_check`; agent/compute/RAG tasks were absent. This confirms the registration gap in a fresh local process, without claiming a Docker worker test.

Migration 0001 uses live Base.metadata create_all/drop_all; ADR-0002 pins its original table ownership to prevent premature financial tables on fresh upgrades. Legacy tool tests require exactly seven default tools, so financial tools use a separate registry. Existing evals rerun successfully: deterministic Agent fixture 30/30; recovery contract 8/8. These do not establish real provider quality or infrastructure restart recovery.

## Launch and infrastructure validation boundary

Local: `PYTHONPATH=backend;lobster_quant`, `python -m uvicorn backend.main:app --reload`, separately `npm run dev`. Compose uses PostgreSQL/pgvector -> migration -> API/agent and compute workers/frontend; Redis is broker only. Required environment substitutions include POSTGRES_PASSWORD and DATABASE_URL. Do not print or create actual secrets for baseline work. No Docker/PostgreSQL/Redis live restart validation has been claimed. Disposable migration tests and deterministic provider runs establish offline behavior only.

See ADR-0002 and financial-mas-contracts.md for compatibility, rollback, budgets, typed contract draft and ownership/dependencies.
