# W8 security and recovery evidence matrix

This document maps the existing W8-T6/T7 protections to executable tests and records the bounded security slice. It does not claim live-provider, PostgreSQL, Redis/Celery-broker, broker, or trading validation.

## Evidence map

| Requirement | Existing executable evidence | Additional coverage in this slice |
|---|---|---|
| Event prompt injection remains untrusted text; time-ineligible evidence is rejected | `backend/tests/test_financial_market_tools.py::test_injection_remains_text_and_missing_backend`; `backend/tests/test_market_mas.py::test_temporal_and_injection_fixture_boundary`; `backend/tests/test_financial_market_tools.py::test_truth_labelled_evidence_cutoff` | None. The joined run includes these cases. |
| Specialist tool allowlists and read-only enforcement | `backend/tests/test_financial_runtime.py::test_readonly_tool_permissions_audit_and_cache`; `backend/tests/test_financial_market_tools.py::test_registered_tools_executor_and_numbers`; `backend/tests/test_financial_portfolio_tools.py::test_tool_registry_execution_and_general_unchanged` | None. Existing tests exercise both role authorization and tool metadata/execution. |
| Cross-run, conversation, and artifact ownership rejection | `backend/tests/test_financial_api.py::test_result_rejects_corrupt_or_foreign_artifact_ownership`; `backend/tests/test_cross_mas.py` attack/scope and receiver-ownership cases; `backend/tests/test_financial_runtime.py::test_final_artifact_rejects_wrong_requested_asset_or_snapshot` | None. |
| Malformed requests, forged values, stale/future prices and evidence | `backend/tests/test_financial_api.py::test_invalid_creation_rejected_before_writes`; `backend/tests/test_financial_market_tools.py::test_strict_inputs_and_rag_unknown_metadata`, `test_hash_tampering_and_invalid_prices_rejected`; `backend/tests/test_financial_portfolio_tools.py::test_history_safety`, `test_forged_values_are_recomputed`; `backend/tests/test_portfolio_mas.py` malformed/verifier cases | None. |
| Provider diagnostic text and credentials do not leak through failure responses/audit | No prior financial API-level assertion found for exception-message redaction. | `backend/tests/test_financial_w8_security.py::test_provider_exception_text_is_not_exposed_by_financial_api_or_audit` injects a synthetic sentinel in a provider exception, exercises the actual local worker/API path, and checks the public result plus persisted event/invocation data. This tests exception-message containment only; it is not a credential-store or live-provider audit. |
| Portfolio state is read-only | `backend/tests/test_financial_portfolio_tools.py::test_readonly_file_hash_and_no_ctor` verifies only that a disposable temporary snapshot file is unchanged; `backend/tests/test_financial_portfolio_tools.py::test_tool_registry_execution_and_general_unchanged` verifies the registered tools are read-only. The no-portfolio-write-endpoint assertion belongs to the W7 browser E2E in `lobster-quant-web/e2e/financial-mas.spec.ts`. | None. These are separate checks with separate scopes. |
| Duplicate delivery, cancel/resume, checkpoint restore, CAS/version fencing, monotonic event sequence | `backend/tests/test_financial_runtime.py`; `backend/tests/test_financial_api.py::test_stale_version_and_pause_resume_only_submitted_run` and duplicate/cancel cases; `backend/tests/test_cross_mas.py` restore, duplicate, expiry, and CAS cases; `backend/tests/test_financial_worker_authorization.py` | None. The joined run includes these suites. |
| Migration safety | `backend/tests/test_financial_runtime_migrations.py::test_fresh_existing_upgrade_and_downgrade_preserves_general`; PostgreSQL JSONB is checked by compiling DDL in `test_financial_postgresql_ddl_uses_jsonb`. | None. Migration execution uses disposable SQLite only. |
| No-Redis local inline delivery and duplicate worker delivery | `backend/tests/test_financial_api.py::test_three_workflows_real_ids_initial_dispatch_and_idempotency`; `backend/tests/test_financial_bootstrap.py::test_worker_bootstraps_both_financial_drivers_in_fresh_process` | None. These use local background/task calls with `REDIS_URL` unset, not a broker. |

## Reproduction

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "backend;lobster_quant"
python -m pytest `
  backend/tests/test_financial_w8_security.py `
  backend/tests/test_financial_market_tools.py `
  backend/tests/test_market_mas.py `
  backend/tests/test_financial_portfolio_tools.py `
  backend/tests/test_portfolio_mas.py `
  backend/tests/test_financial_runtime.py `
  backend/tests/test_financial_api.py `
  backend/tests/test_cross_mas.py `
  backend/tests/test_financial_execution_authorization.py `
  backend/tests/test_financial_worker_authorization.py `
  backend/tests/test_financial_runtime_migrations.py `
  backend/tests/test_financial_bootstrap.py -q
```

Run output is retained as `logs/financial-mas/w8-security-recovery.log` in the security worktree. The joined run passed **515 tests in 399.85 seconds** (2026-10-09); the log is an ignored local evidence artifact and is not part of the commit.

## Scope limits

All runtime and worker tests use synthetic providers and disposable SQLite databases. Portfolio file immutability is checked against a temporary test file. No live holdings, provider, external endpoint, real database, broker, or trading API is used. On this host, `docker version` reports a client but cannot connect to the Docker Desktop Linux engine pipe, so PostgreSQL coverage is DDL compilation only; no PostgreSQL server, Redis service, or Celery broker behavior is claimed. The exception-boundary regression protects against accidental serialization of provider exception messages, but does not audit external provider logging or secret-management infrastructure.
