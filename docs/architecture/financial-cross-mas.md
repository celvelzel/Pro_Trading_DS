# Financial cross-MAS routing

Status: W6 Gate accepted in root commit `a0d29f9` after independent review and
full validation on the exact commit. Typed application API, UI, SSE and navigation
integration remain W7 coordinator work.

## Historical admission block, now closed

The frozen dispatcher exposes `create`, `start`, `snapshot`, `link_runs` and
`relations` to the router. `link_runs` atomically fences the source run version,
checks immutable ownership/timepoint metadata and persists a relation plus its
source event. It does not check or reserve persisted `RunBudget.hops` or
`RunBudget.followups`. Its transaction does not admit a correlation-wide graph
transition or fence the target run's lifecycle.

At the original `eb1d256` baseline, only `RuntimeContext.consume_budget` reserved these counters. That
operation requires an executing driver's claim token; it is not a public router
operation. Reserving separately would also separate budget consumption from
relation insertion and break crash-safe idempotency.

A router cannot replace this with `snapshot`/`relations` reads followed by
`link_runs`: the reads and admission are separate transactions. Opposing sources
have independent CAS versions, so both may pass a previously observed graph.
Canonicalizing admission on one source can serialize relation changes but still
cannot reserve actual W1 counters through the allowed API. Envelope counters
alone would leave authoritative run counters unchanged and silently bypass the
frozen budget contract. Process locks would not survive restart or protect
multiple workers.

The reported blocker was resolved by independently reviewed ADR-0003 and its
public `admit_cross_message` seam. ADR-0004 independently binds immutable
execution profiles. The router uses these accepted contracts; it does not
inspect persistence tables, call private `_mutation`, or claim driver authority.

## Admission authority

The accepted atomic operation combines:

- Durable exact-payload idempotency, checked before new-request terminal rules
  so an accepted historical request can be replayed without creating new work.
- Correlation-wide serialization or a canonical admission owner, with a graph
  rule that prevents cyclic waiting across concurrent opposing requests.
- The configured run hop/follow-up ceilings, including zero, authoritative
  counter reservation, and immutable logical hop/follow-up metadata in the
  persisted envelope/relation. Define which run pays each logical operation.
- Source and target lifecycle checks, aware UTC deadline validation, immutable
  artifact ownership/schema/timepoint checks and one transactional relation/event
  write. Terminal evidence producers may transfer an existing artifact; terminal
  Portfolio consumers cannot initiate new follow-up work.

Normal combined creation still requires separate Market and Portfolio run IDs,
shared correlation and independent state/budgets/events. `parent_run_id` keeps
retry-only semantics. Admission must support one bounded additional Market run
without changing completed producer history. No third business Coordinator is
needed.

## Public router assembly

`agent.integration` imports shared contracts/runtime and the W3 snapshot contract;
it imports neither domain MAS implementation. Application assembly injects
reviewed drivers and deterministic tools separately.

```python
CrossMASRouter(dispatcher, artifact_store, snapshot_loader, *,
               execution_profile: str, clock=None, ttl_seconds=60)
router.create(request: CrossMASRequest) -> CrossMASResponse
router.restore(run_id: str) -> CrossMASResponse
await router.advance(response, *, max_deliveries=3, peer_timeout=30)
router.request_further_evidence(portfolio_run_id, market_request, *,
                               idempotency_key, mode='review') -> dict
router.transfer(market_run_id, portfolio_run_id, *, request_relation=None) -> dict
router.admit(source_run_id, target_run_id, envelope, *,
             expected_source_version, expected_target_version) -> dict
router.artifact_resolver(run_id, conversation_id,
                         request: PortfolioReviewRequest) -> MarketInvestigationArtifact | None
```

`CrossMASRequest` supplies conversation, idempotency key, review/auto mode,
optional typed Market/Portfolio requests and each independent RunBudget. Both
requests must have identical aware UTC `as_of`; direct Portfolio artifact IDs
are rejected so router consumption requires admission. `CrossMASResponse`
returns each actual run ID, common correlation and optional-peer limitations.
Correlation and creation keys are deterministic hashes of caller identity;
repeated creation uses the frozen complete creation-input comparison. Normal
combined mode creates both run IDs before either driver runs. An undeployed peer
leaves the deployed workflow available. Partial creation can be retried using
the same request/key; creation is not a two-run transaction.

The execution_profile must exactly match the injected dispatcher. Both initial
runs and further-evidence Market runs use that same dispatcher/profile. Demo
factory assembly uses `synthetic-demo-v1`; configured factory assemblies require
their explicit different identity. No symbol/snapshot inference or provider/data
fallback exists. Configured queue-worker profiles remain unsupported unless an
operator registers an independently reviewed reconstruction mapping.

## Bounded evidence and independent completion

READY and REQUEST envelopes have absolute aware UTC deadlines. TTL begins when
the logical envelope is constructed for admission, after evidence is available;
it is not a replacement for either run's active deadline. Accepted exact replay
uses its stored envelope and cannot extend that deadline. Only `cross_admitted`
relations authorize transfer/work. The router checks the trusted immutable saved
snapshot's ID, source, exact effective_at and holdings scope before admission
and before consuming an immutable artifact through scoped ArtifactStore.

Initial Market READY charges its source one hop. Further evidence charges the
Portfolio source one hop and one follow-up, across the whole correlation under
the runtime's minimum member ceilings. Its new Market run has independent
state/model/tool budget and no retry parent. The single causally matched reverse
READY or UNAVAILABLE resolves that request at zero extra hop. Relations/envelopes
retain exact message, causation, source/target, correlation, timepoint and immutable
artifact version. Actual counters remain observable in public snapshots. Another
request rejects; zero/lowered ceilings remain authoritative. No business
Coordinator is added and neither completed history nor creation_inputs changes.

Further evidence must be requested before Portfolio context acceptance or role
invocation. The router does not mutate an existing model's task or create new
work from a completed Portfolio run. `advance` restores admitted requests from
relations; it delivers at most the configured bounded number of checkpoints.
The default scheduler starts initial Market before Portfolio but each driver
also runs independently in parallel. Failed/cancelled/undeployed/timed-out peers,
expired optional messages and exhausted cross budgets do not require waiting:
Portfolio proceeds with its existing optional-evidence limitation. Review-mode
approval remains external through the existing versioned lifecycle APIs.

Trusted scope checks used by asynchronous advance run in a bounded offloaded
transfer; Portfolio resolver callbacks are offloaded by the reviewed W5 driver.
Peer timeout does not replace the independent Portfolio execution allowance.
Python cannot kill a synchronous adapter's running thread; trusted adapters must
configure bounded I/O. A timed-out driver delivery can retain its runtime lease
until recovery; the router does not modify claims or lease state.

## First acceptance versus historical checkpoint replay

First resolver acceptance chooses the newest admitted causal reply when present,
otherwise initial READY. It validates conversation, profile, schema, producer,
exact as_of, current trusted holdings and live TTL before recording selection.
The immutable `artifact_selection` diagnostic relation is written with the
Portfolio receiver's CAS, fencing cancellation; its deadline is the admitted
READY's deadline, so public link validation rechecks TTL inside the transaction.
Its non-work SYSTEM_UNAVAILABLE envelope carries no artifact and identifies
the exact admitted READY by causation. This is receipt metadata distinguished by
relation type, not an executable unavailable response or work authorization.

Subsequent checkpoint replay follows that exact receiver-owned receipt back to
the admitted READY and reads the same immutable context. This is historical
context replay, not new cross-message consumption: expiry cannot replace the
cached role task with None or silently select a different artifact. Current
authorized holdings, profile/as_of/schema/producer still revalidate; no new
message, receipt, hop or follow-up is emitted. An unselected expired READY or a
new/retry receiver with no receipt returns None; failed/cancelled/expired receivers
cannot accept context. This distinction preserves the frozen W5 invocation input
identity without weakening the TTL of a new transfer.

## Evidence, remaining review and deployment limits

`backend/tests/test_cross_mas.py` assembles actual W4/W5 drivers, real W2/W3 typed
tools, explicit synthetic MU/SOXX/SPY/TLT data, disposable SQLite and audit rows.
It checks three workflows, actual artifact/tool-result references, distinct
events and budgets, input/artifact immutability, one follow-up and zero-cost
reply, duplicate/concurrent CAS, lowered budgets, time/schema/scope/cause denial,
peer failure/cancel/timeout, disabled-peer fresh-process imports, review approval,
Market checkpoint restoration and Portfolio revision checkpoint replay after
TTL expiry. First acceptance cancellation/expiry races and new-receiver rejection
are explicit tests. The reviewed shared admission suite supplies additional
atomic graph/correlation-membership and resolution-race coverage.

Creating a further-evidence run and admitting its request are separate public
transactions. A concurrent admission loser can leave an unadmitted queued Market
run. Every initial Market-only, Portfolio-only and Combined run explicitly stores
`FinancialExecutionAuthorization(purpose='independent')`. Every follow-up stores
`cross_followup`, its exact Portfolio source and the deterministic REQUEST
message ID before target creation. Missing relations never imply independence.
All router snapshot paths reject absent stored origin, including legacy
uncorrelated roots that the shared runtime deliberately supports for compatibility.
Further-evidence sources must explicitly store `independent` purpose.
Follow-up transfer requires the exact persisted admitted REQUEST relation and
reverses its endpoints with its exact message ID as causation. Missing, forged
or other-target REQUEST arguments fail before mutation; independent transfers
cannot impersonate REQUEST resolution. The public router admission wrapper also
rejects a follow-up reply with missing/wrong causation or receiver.
Restore and scheduler preflight call public `validate_queue_eligibility`; denied
orphans cannot restore, advance or execute through either actual worker entry.
Admission binds the exact target/source/message/conversation/correlation/domain,
execution profile and as_of. The shared atomic `start` claim is authoritative:
expiry after a successful preflight transitions to `expired` with zero model or
tool calls. Same-key retry reconstructs the original run and marker. No public
atomic creation-and-admission API is claimed.

Fresh process tests persist router-created targets in SQLite, exit, and invoke
the actual Celery task functions (`run_agent` and `resume_agent_job`) in a new
interpreter. Trusted synthetic provider instrumentation checks independent
completion, denied orphan zero persistence changes, expired target zero calls,
duplicate delivery and single-domain absent-peer imports. This is process restart
and real task-entry evidence, not broker or Redis delivery evidence.

No live provider, PostgreSQL/Redis/broker-backed Celery restart, real holdings,
real trading, application-route wiring, W7 or W8 acceptance is claimed. W6 was
independently reviewed against `dc09ae4..a0d29f9` and accepted after 252 scoped
tests and 716 Full Backend tests passed on the exact candidate. The tests use
SQLite, synthetic providers and direct Celery task-function calls in fresh
interpreters; they do not establish broker or PostgreSQL behavior. Exact commands,
raw output, earlier fixture failures and stopped pre-fix runs are retained under
`C:/Users/RickyMa/.codex/worktrees/financial-cross-repair/Pro_Trading_DS/logs/financial-mas/w6-repair-*`.
