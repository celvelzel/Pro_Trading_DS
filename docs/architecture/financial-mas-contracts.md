# Financial MAS contract draft v1 (W0)

The implementation plan is `docs/plans/financial-dual-mas-implementation.md`. W1 freezes executable Pydantic contracts and documents exact exported signatures here before W4/W5 begin. Draft changes needed by W1 are reviewed before freeze. After freeze, incompatible changes require an ADR and a reported dependency block.

## Common rules

All public models forbid extra fields and nonfinite numbers. Dates are aware UTC (normalize offsets); retain exchange timezone separately. Artifact schema_version is literal 1. Symbols are normalized uppercase. Financial weights are nonnegative, sum to one within documented tolerance and include explicit CASH. Constraints use typed models, never permanent arbitrary dictionaries. Diagnostic statuses distinguish unknown/missing inputs from infeasibility.

Requests: MarketInvestigationRequest(symbol, as_of, lookback_trading_days=20, sector_benchmark?, max_llm_calls<=16); PortfolioReviewRequest(portfolio_snapshot_id, as_of, typed user_constraints, market_artifact_id?). API envelopes add conversation_id, mode(review/auto), request_id/idempotency_key and immutable input references without changing legacy RunCreate.

EvidenceRef: id, source_type, source_locator, published_at?, available_at?, observed_at, content_hash, excerpt?. Unknown publication or availability excludes strict historical attribution. NumericFact: name, value, unit, evidence/tool-result reference. Hypothesis: explanation, support IDs, against IDs, disposition(supported/contradicted/unverified). Market artifact: producing run_id, symbol, as_of, numeric facts, hypotheses, evidence, limitations, status(verified/partial/insufficient_evidence).

AllocationConstraints: symbol caps, minimum cash, maximum equity, sector caps, weight tolerance. ConstraintCheck: status(pass/fail/unknown), typed violations and unknowns. Portfolio artifact: producing run_id, snapshot_id, as_of, current/proposed weights, constraint check, deterministic risk comparison, simulation assumptions/results, evidence IDs, status(feasible/infeasible/insufficient_data). Feasible requires every requested hard check to pass.

## Runtime extension seam

W1 exclusively owns `backend/agent/shared/`: SpecialistRegistry, SpecialistInvoker, WorkflowDriver Protocol, RunBudget, dispatcher, artifact store and executable shared schemas. Providers reuse `agent.llm.ModelProvider.complete`. Invocations have separate role context and read-only tool allowlists. Drivers get run-scoped runtime context and resume from persisted state; the dispatcher owns persistence, budgets, claims, status transitions and events. Each invocation returns a schema-validated role result; coordinator alone commits domain state. Export exact methods and fake-driver examples at W1 gate.

W2 owns independent Pydantic input/output models and registration functions in market_history.py, market_events.py, anomaly.py. W3 does the same in portfolio_snapshot.py, portfolio_risk.py, allocation.py. Neither edits shared schemas or default tool registry initialization. Financial registry assembly is sequentially integrated by Lead after review. Quant calculation modules are independent of backend contracts and ModelProvider.

CrossMAS Envelope: message_id, schema_version, origin/target MAS and agent, run_id, correlation_id, causation_id, message type, payload_ref, as_of, created_at, deadline_at, idempotency_key, budget/hops. Immutable artifact references carry artifact_id and schema_version. Cross-run relations use separate metadata, not parent_run_id. Reject unauthorized conversation, version, symbol or timepoint before passing data to a specialist.

## External compatibility

Add `/api/financial/market-investigations`, `/portfolio-reviews`, `/combined-reviews`, and typed result retrieval. Actual IDs refer to existing AgentRun rows. Keep `/api/agent/runs/{id}/events` and versioned interventions; dispatch by financial metadata. Default legacy requests remain General. No automatic trading or preference persistence.

## Ownership and dependency gates

| Wave | Worker ownership | Required gates |
|---|---|---|
| W0 | Lead: plan, ADR, inventory, contracts, task ledger | independent Reviewer |
| W1 | Runtime: agent/shared, db/models/financial_mas.py, migration 0004, runtime tests; narrowly granted worker dispatch, model imports and 0001 ownership pinning per ADR | W0 |
| W2 | Market Data: analysis/market_anomaly.py, three new market tools, eval/fixtures/market, dedicated tests | W0 |
| W3 | Quant: core/portfolio_risk.py, allocation_simulator.py, three portfolio tools, eval/fixtures/portfolio, dedicated tests | W0 |
| W4 | Market: agent/market_mas, dedicated tests | W1 + W2 |
| W5 | Portfolio: agent/portfolio_mas, dedicated tests | W1 + W3 |
| W6 | Integration: agent/integration, dedicated tests | W4 + W5 |
| W7 | API/UI: financial routes/models and financial UI/tests | W6 |
| W8 | Evaluation: eval scripts/cases, E2E, evidence docs | W7 |

Lead integrates shared registration, main.py, legacy route dispatch and navigation. Every writer gets a distinct worktree based on the same gate-approved commit. Reviewers are read-only, cannot delegate, and report evidence and actionable findings. No remote push/PR is required by this local task; local commits and review records make each wave reviewable.
