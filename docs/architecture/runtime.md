# Agent Runtime

## Local development

The API runs from the repository root with the backend directory on the Python path:

```powershell
$env:PYTHONPATH="backend;lobster_quant"
python -m uvicorn backend.main:app --reload
```

The frontend runs separately:

```powershell
cd lobster-quant-web
npm run dev
```

Without Redis, agent and document requests use the local inline execution path. With Redis, Celery dispatches agent, compute, and RAG work to their dedicated queues.

## Compose deployment

The production-shaped local stack is defined in `compose.yaml`:

```powershell
Copy-Item .env.example .env
# Replace POSTGRES_PASSWORD before using a shared environment.
docker compose up --build
```

Startup order is database health check -> Alembic migration -> API/worker -> frontend. The API container does not create tables implicitly; migrations are the only schema source of truth. The current migration head is `0003_runtime_hardening`.

The API exposes `/api/health/live` for process liveness, `/api/health/ready`
for database readiness, and `/metrics` for low-cardinality Prometheus text
metrics. A missing `AI_API_KEY` is reported as `AI_PROVIDER_NOT_CONFIGURED`;
the deterministic fake model and fake embedding provider remain available for
offline contract tests.

## Operational boundaries

- The default model provider is deterministic and offline-safe; external model calls require explicit provider configuration.
- Backtest tools create jobs and return job identifiers. Long-running work is owned by Celery workers.
- The SSE endpoint replays events by sequence number and uses `Last-Event-ID` when supplied.
- The SSE connection is bounded for local proxies and clients reconnect with `after_seq`; the REST snapshot remains authoritative.
- Uploaded documents are stored under the configured document volume and become searchable only after ingestion reaches `ready`.
- No live trading, broker order placement, OCR, or production secret provisioning is included in this upgrade.
- The recovery runner validates state transitions and event replay without claiming a full Docker fault-injection test.

## Database commands

```powershell
alembic heads
alembic upgrade head
alembic downgrade -1
```
