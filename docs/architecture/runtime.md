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
$env:POSTGRES_PASSWORD="local-only-password"
$env:DATABASE_URL="postgresql+asyncpg://pro_trading_ds:local-only-password@db:5432/pro_trading_ds"
docker compose up --build
```

Startup order is database health check -> Alembic migration -> API/worker -> frontend. The API container does not create tables implicitly; migrations are the only schema source of truth.

## Operational boundaries

- The default model provider is deterministic and offline-safe; external model calls require explicit provider configuration.
- Backtest tools create jobs and return job identifiers. Long-running work is owned by Celery workers.
- The SSE endpoint replays events by sequence number and uses `Last-Event-ID` when supplied.
- Uploaded documents are stored under the configured document volume and become searchable only after ingestion reaches `ready`.
- No live trading, broker order placement, OCR, or production secret provisioning is included in this upgrade.

## Database commands

```powershell
alembic heads
alembic upgrade head
alembic downgrade -1
```

