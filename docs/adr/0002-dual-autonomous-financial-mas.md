# ADR-0002: Two autonomous financial MAS workflows

- Status: Accepted for implementation; each wave remains subject to its review gate.
- Date: 2026-10-08
- Baseline: `de262d4a089069e2a1387655e3daa3c6a7a4fe4b`

## Decision

Extend the existing Plan-and-Execute platform with two registered workflow drivers, `market_investigation` and `portfolio_rebalance`. Each owns its Coordinator, specialist registry, typed domain state, verification, run ID, budget and evaluation. Neither imports the other's implementation. A thin combined router creates two distinct AgentRun records with a shared correlation ID; it exchanges immutable, versioned artifacts. The legacy `parent_run_id` retains retry semantics.

Reuse ModelProvider, ToolRegistry/ToolExecutor, AgentRun, AgentEvent, state transitions, SQLAlchemy/Alembic and the Celery agent queue. Do not introduce LangGraph or a second queue/storage authority. Add domain metadata/checkpoints, invocation records, artifacts and cross-run relations through one migration following `0003_runtime_hardening`. JSON uses the existing PostgreSQL JSONB / SQLite JSON variant. PostgreSQL remains deployment authority; SQLite is the offline integration-test adapter. Register model metadata for migrations and tests using the existing import convention.

Compatibility repair: migration 0001 currently creates/drops all live ORM metadata. Pin its original owned table names so registering new financial models does not create them at revision 0001 or drop unrelated later tables. Preserve original table definitions/semantics; 0004 exclusively creates/drops financial tables. Validate fresh upgrade, existing 0003 upgrade and downgrade to 0003 preserving General rows on disposable databases. This narrowly scoped historical migration repair is authorized by this ADR, not a new schema interpretation for legacy records.

## Compatibility and lifecycle

General Copilot keeps its requests, six-step plan limit, eight executed steps, ten model calls, eight tool calls and one replan. Financial workflows use separate bounded settings: at most 16 model calls, 20 tool calls, three coordination rounds, one cross-system follow-up, two hops and a 120-second wall deadline. Requests can lower limits, never raise ceilings. Count and persist reservations before calls, including failed attempts; checkpoint state and artifacts transactionally. A coordinator is the sole domain-state writer. Concurrent/duplicate workers acquire a DB-backed lease/claim and optimistic version checks; event append uses the existing per-run sequencing under that ownership. Replay never repeats a persisted specialist result. A crash after external invocation but before persistence cannot provide exactly-once external billing; document this uncertainty and retain bounded attempts.

Keep the existing run states and legacy event envelope. Add namespaced `mas.*` and `cross_mas.*` event types carrying role/action/evidence references, never hidden reasoning or prompts. Existing SSE transports unknown event types compatibly. Financial approval authorizes read-only analysis/simulation only. Worker dispatch detects financial metadata before selecting a driver, otherwise selects AgentOrchestrator. Lifecycle API dispatch similarly preserves General behavior. Terminal retries create a new run and keep immutable history.

All financial mutations, including API interventions and worker checkpoints, share transactional CAS/fencing and event sequence allocation. A worker lease alone cannot serialize user interventions; stale ownership cannot persist results. Financial cancellation is allowed from any nonterminal state, including queued/planning/waiting_user/paused. Pause from queued/planning/waiting_user preserves its resume phase; executing pause is cooperative at call boundaries. Implement these through financial dispatcher semantics without changing the General transition table. The wall deadline covers active execution time, not human review/paused waiting; persist accumulated active seconds and restart timestamps so restart cannot reset the allowance. Cross-message TTL remains absolute UTC.

## Safety and provenance

All registered financial tools are read-only and side-effect-free. Specialists have separate model calls, prompts and allowlists; untrusted evidence is delimited data and cannot add tools. Financial numbers are computed by deterministic typed tools. Never invoke position/cash writes, broker endpoints or order placement. Strict snapshots require explicit holdings/cash, source, valuation prices, currency and aware timestamps; historical holdings must be a saved historical snapshot, never today's holdings valued at historical prices.

Use a separate financial ToolRegistry assembled explicitly by Lead. The default General registry stays at its existing seven tools (the legacy regression asserts exact membership). Feature modules export registration functions and never mutate a global registry at import.

`as_of` is an aware UTC knowledge cutoff. Evidence publication and availability must both be known and no later than the cutoff. Retrieval time is separate. Price bars have explicit close/availability times, exchange timezone and adjustment convention. Insufficient data is a valid outcome. Constraint unknowns cannot be approved as passes. Mixed currencies require explicit conversion provenance or refusal. Simulations use date-aligned returns, explicit fees/slippage and no future data.

## Cross-system boundaries

Artifacts are immutable and scoped to conversation and producing run. Validate schema version, as_of, symbols, ownership and deadline before consumption. Messages reference artifacts rather than arbitrary chat histories. Enforce TTL, idempotency, at most two hops and one follow-up; unavailable peers produce a degraded result without blocking an independent workflow. Store relationship metadata separately from retry ancestry.

## Rollback and validation

Disable financial entry points/driver registration first; legacy General continues. Downgrade only on an isolated database or after exporting financial history, because additive-table downgrade removes that history. Do not downgrade a user database during development. Test upgrade/downgrade on disposable SQLite and inspect PostgreSQL-compatible DDL; actual PostgreSQL/Redis restart tests must be reported separately from offline tests.

Gate W0 requires independent review of this ADR and contract/ownership map. W1-W3 integrate only after their tests and independent review; W4/W5 consume frozen W1 contracts and their corresponding tools. W6 follows independent domain gates, W7 follows cross-system gate, and W8 requires reproducible evaluations plus legacy regressions and frontend build. No gate can be passed by weakening assertions.
