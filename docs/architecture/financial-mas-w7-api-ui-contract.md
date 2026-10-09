# Financial MAS W7 API and UI contract

Status: frozen v1 after independent contract Review PASS on 2026-10-09 against
the exact W6 Gate acceptance at `a0d29f9`.
This is an additive API/UI contract. It does not change the shared
Runtime, existing General routes, or the W1 executable contract.

## Workflow creation

`workflowType` is a UI selection (`general | market | portfolio | combined`); it
is separate from the existing execution `mode` (`review | auto`). General remains
the default and continues to call the unchanged `/api/agent` API.

Financial creation uses three typed, additive endpoints:

| Endpoint | Required input |
| --- | --- |
| `POST /api/financial/market-investigations` | `CrossMASRequest` with `market` set and `portfolio` absent |
| `POST /api/financial/portfolio-reviews` | `CrossMASRequest` with `portfolio` set and `market` absent |
| `POST /api/financial/combined-reviews` | `CrossMASRequest` with both inputs set and matching `as_of` |

The body contract is `conversation_id`, `idempotency_key`, `mode`, typed
`market`/`portfolio` request objects, and their independent `RunBudget` values.
Each endpoint rejects inputs for the wrong workflow. Combined rejects direct
artifact IDs and uses only the admitted W6 relation for cross-MAS evidence.
Before creating a Combined run, the API also checks that both budgets permit
at least one cross hop and that the Market symbol belongs to the selected
trusted Portfolio snapshot; invalid scope or zero-hop requests return 422 before
either run is created. These checks use the configured immutable synthetic
snapshot, never browser-supplied holdings.
Requests cannot select an execution profile. Until a separately reviewed trusted
provider mapping exists, API/worker execution is limited to
`synthetic-demo-v1`; Portfolio accepts only the configured synthetic snapshot
`synthetic-mu-soxx-v1`. The UI must label these results as synthetic demo data
and must not submit browser-local real holdings or cash.

Create returns HTTP 202 with
`{schema_version: 1, conversation_id, correlation_id, market_run_id?,
portfolio_run_id?, runs: [{run_id, mas_kind, status, version}]}`. Combined must
return two distinct run IDs with the same conversation/correlation; a one-domain
workflow returns only its own ID. The W6 router owns creation/idempotency and
preserves separate per-run budgets, states, event sequences and lifecycle.

Creation commits the typed runs first, then dispatches every created run. A
standalone run uses the existing `run_agent` task. A paired Combined run uses
one new pair task: it reconstructs both trusted synthetic drivers, calls
`CrossMASRouter.restore()` from either member run ID, then calls `advance()` on
the persisted pair. It never submits two unrelated single-run tasks for a
Combined workflow. In `auto`, this starts the bounded workflow; in `review`,
the initial delivery moves each independent run to `waiting_user` and emits its
own `mas.review_required` event. A successful approval/resume CAS re-dispatches
only the standalone task or persisted pair task; pause fences without
scheduling work. Cancelling one paired member changes only that submitted run
through CAS, then dispatches reconciliation from its still nonterminal peer ID.
Reconciliation may advance that peer according to its own persisted mode and
budget (including moving Review to `waiting_user` or executing Auto), but never
approves or changes the peer's approval decision. The cancelled member stays
terminal. Cancelling Market can deliver bounded `SYSTEM_UNAVAILABLE` to
Portfolio; cancelling Portfolio lets Market continue independently.

In Combined Review, approvals remain per-run. Approving Market never approves
Portfolio. Portfolio approval is rejected with 409 while its paired Market run
is queued, executing, paused, or waiting for its own review. Once Market is
terminal, Portfolio may be approved even if W6 could not persist an optional
transfer relation after its bounded retries; the result API must then expose a
derived `market_evidence_unavailable` limitation and the UI must not imply that
Market evidence reached Portfolio. A recorded `SYSTEM_UNAVAILABLE` relation is
shown explicitly. This prevents early approval from skipping an active Market
review while avoiding a permanently stuck Portfolio after optional transfer
failure; transfer failure does not authorize bypassing scope or hop validation.

Financial endpoints also work without Redis: they schedule the same trusted
financial task entrypoints as FastAPI background work in local mode. If a
configured broker rejects task publication after run creation, the API uses
that same inline-local path; duplicate broker/inline delivery is safe through
the existing financial CAS, lease, idempotency and pair restoration rules.
Responses remain 202 and expose created run IDs and current persisted statuses;
the UI must keep polling/subscribing rather than imply that 202 means completion.
Retrying the same idempotency key returns the original IDs and re-dispatches
their current persisted work. This local fallback is not a durable queue
guarantee across API-process loss; do not describe it as such. The legacy
General API's existing no-Redis behavior is unchanged. W8 must exercise actual
inline-local workflows and duplicate/retry behavior.

## Result and lifecycle

`GET /api/financial/runs/{run_id}` returns a versioned typed result. `artifact`
is a discriminated union of `MarketInvestigationArtifact`,
`PortfolioProposalArtifact`, or null; it is never an untyped free-form object.
The `mas_kind` field selects which artifact schema is valid.
The API validates artifact ID, schema version, conversation, `as_of`, producing
run ID, and MAS kind against the selected run before returning it. The response
shape is shown below; `limitations` also contains a derived
`market_evidence_unavailable` entry when a Combined Portfolio run is terminal
without an admitted usable Market evidence relation.

```json
{
  "schema_version": 1,
  "run_id": "...",
  "conversation_id": "...",
  "correlation_id": "...",
  "mas_kind": "market_investigation | portfolio_rebalance",
  "status": "queued | executing | waiting_user | paused | completed | failed | cancelled | expired",
  "mode": "review | auto",
  "version": 1,
  "error_code": null,
  "artifact_ref": null,
  "artifact": null,
  "validation_outcome": "verified | partial | insufficient_evidence | feasible | infeasible | insufficient_data | pending",
  "limitations": []
}
```

`artifact_ref` and `artifact` are null until a validated immutable artifact
exists. For a Market artifact, `validation_outcome` maps to its exact
`verified | partial | insufficient_evidence` status. For a Portfolio artifact,
it maps to its exact `feasible | infeasible | insufficient_data` status. Before
an artifact exists it is `pending`; terminal failure remains represented by
`status` and `error_code`, not disguised as a validation result. The API does
not expose prompts, hidden reasoning, or mutable checkpoint internals.

Financial actions use separate typed routes
`POST /api/financial/runs/{run_id}/{approve|pause|resume|cancel}` with
`{expected_version, reason?}`. They dispatch only through
`FinancialMASDispatcher` and its versioned CAS; they never fall through to
`AgentOrchestrator`. `approve` and `resume` enqueue execution only after the CAS
succeeds. `pause` fences the submitted run and does not enqueue work. `cancel`
fences only the submitted run; if paired, it dispatches reconciliation from the
still nonterminal peer. That task may advance the peer under its persisted mode,
but cannot approve it or change its approval decision.
For a paired or follow-up run, approval/resume re-enqueues the durable W6 router
task; for a standalone run it enqueues the existing single-run task. A Review
approval authorizes only the analysis/simulation lifecycle. No route or UI action
can authorize a trade, broker call, or real holdings/cash mutation. Stale versions
return 409; unknown runs return 404; invalid typed input returns 422. The current
application has no user-authentication dependency; these endpoints must not
claim user-level conversation/run isolation.

The pair task reconstructs a trusted dispatcher with both domain drivers and the
W6 router; it accepts either actual member run ID, calls
`restore(member_run_id)`, then advances the persisted relation graph. It is safe
for duplicate task delivery and is the only worker path that executes Combined
evidence transfer. Single-domain routing continues to use a single-domain worker
configuration so an undeployed peer is not imported.

## Events and UI

SSE continues to use the existing replay endpoint
`GET /api/agent/runs/{run_id}/events?after_seq={cursor}`. The named-event envelope,
`schema_version`, `event_id`, per-run `seq`, `run_id`, and payload stay unchanged.
The client subscribes to each actual run ID independently; Combined keeps two
EventSources and two cursors, and labels each event with its run and role. A gap
replays from the last contiguous sequence, deduplicating by `event_id`/`seq`.

The client recognizes the financial named events emitted by the dispatcher:
`mas.created`, `mas.retry_linked`, `mas.approve`, `mas.pause`, `mas.resume`,
`mas.cancel`, `mas.expired`, `mas.review_required`, `mas.started`,
`mas.checkpoint`, `mas.failure`, `mas.invoked`, `mas.returned`,
`mas.invocation_failed`, `mas.budget_reserved`, `mas.artifact_created`,
`mas.completed`, `mas.handoff`, `mas.challenge`, `mas.replan`,
`cross_mas.admitted`, `cross_mas.received`, and `cross_mas.linked`. Events with
a `role` use that role label; lifecycle events without one use a stage/system
label derived from the event type. It renders only structured role/kind/action
summaries, evidence IDs, status, artifact references, and relation IDs/endpoints;
it never renders model prompts or hidden reasoning.

Copilot adds workflow selection while preserving General defaults and the
separate Review/Auto mode. Market, Portfolio, and Combined views fetch typed
results and show loading, waiting-for-review, partial/failure, and final states.
Market, Portfolio, and Combined results must show the role trajectory, evidence
board with source citations, limitations, and (for Portfolio) before/after risk
metrics. The analysis page can launch a symbol-scoped Market demo; the Portfolio
page can launch the explicitly labelled synthetic read-only Portfolio/Combined
demo without transmitting its locally stored actual holdings or cash. Neither
entrypoint persists investment preferences. Financial MAS endpoints and UI
actions never call the existing portfolio position/cash write APIs, trading
routes, or broker operations. Existing portfolio editing features remain
independent and unchanged. Both entrypoints are research/simulation only.

## Acceptance evidence

Backend tests cover endpoint-specific input validation, legacy General route
compatibility, three creation modes, independent IDs/correlation, typed result
references and run ownership, version conflicts, per-run Combined approval,
both paired-cancel directions with terminal-member and peer-state assertions,
initial Auto/Review dispatch, no-Redis inline dispatch, broker-publication
fallback, and repeat-create recovery. Frontend tests cover schema parsing,
every listed named event, per-run SSE replay/reconnect/gap/duplicates, two-run
state, role/evidence rendering without reasoning, empty/partial/error and
accessibility states, and legacy General behavior. Browser E2E must run
Market-only, Portfolio-only and Combined through the actual typed API and
synthetic drivers, show independent run/event state and both Combined IDs, and
verify the Portfolio page's local holdings/cash remain byte-for-byte unchanged.

## Freeze record

The contract passed independent read-only Review after two repair rounds. The
final review confirmed W6 compatibility for Combined Review ordering,
zero-hop/scope preflight, transfer-failure degradation, both cancellation
directions, per-run approval, no-Redis local dispatch, typed artifact ownership,
all named events, and unchanged General behavior. No W1 frozen contract or W6
implementation changed. This is a W7 design/contract gate only; it does not
claim API/UI code, tests, browser E2E, or the W7 acceptance Gate are complete.
