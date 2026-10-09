# Financial runtime API v1

Status: frozen executable W1 contract; independent review PASS at 761c90a, integrated at 2b4b587. Import from `agent.shared` with absolute backend and lobster_quant directories in PYTHONPATH. ADR-0002 governs budgets, concurrency, migration ownership and read-only semantics. No Market/Portfolio implementation is imported by this package.

## Assembly and lifecycle

```python
FinancialMASDispatcher(session_factory: Callable,
    drivers: WorkflowRegistry | None = None,
    tools: ToolRegistry | None = None,
    *, clock=utcnow, lease_seconds=30)

dispatcher.create(conversation_id: str,
    request: MarketInvestigationRequest | PortfolioReviewRequest,
    *, idempotency_key: str, mode="review", budget: RunBudget | None = None,
    correlation_id: str | None = None) -> AgentRun
await dispatcher.start(run_id: str) -> AgentRun
dispatcher.approve(run_id: str, version: int) -> AgentRun
dispatcher.pause(run_id: str, version: int) -> AgentRun
dispatcher.resume(run_id: str, version: int) -> AgentRun
dispatcher.cancel(run_id: str, version: int) -> AgentRun
dispatcher.retry(run_id: str, version: int, *, idempotency_key: str) -> AgentRun
dispatcher.get_run(run_id: str) -> AgentRun
dispatcher.is_financial(run_id: str) -> bool
dispatcher.snapshot(run_id: str) -> dict
dispatcher.link_runs(source_run_id: str, target_run_id: str, *, version: int,
    relation_type: str, idempotency_key: str,
    envelope: CrossMASEnvelope | None = None) -> dict
dispatcher.relations(run_id: str) -> list[dict]
```

The existing conversation must exist. `create` requires a registered driver. Keys are unique per conversation; identical repeated creation returns the persisted run, different inputs conflict. The immutable creation_inputs record compares the full normalized request, kind, effective mode, effective initial budget, caller correlation selection and retry parent in both ordinary and concurrent-create collision paths. Omitted budget and explicitly equivalent defaults deduplicate; consumed counters are never used as creation identity. Caller correlation_id=None remains None in that identity while the generated runtime correlation ID is retained separately. Replaying with an explicitly supplied correlation ID therefore requires the original caller selection. Mode is review/auto. Review starts at waiting_user; approve permits read-only execution. Resume restores the phase preceding pause (including queued/planning/waiting_user); Lead dispatches start after approve/resume when execution is eligible. Cancel works for every nonterminal state, including created/queued/planning/waiting_user/paused. Completed/failed/cancelled/expired are terminal. Terminal retry creates a different AgentRun and preserves parent_run_id retry ancestry atomically with creation. Existing non-retry keys cannot be reused for retry. The internal `_retry_parent_id` create keyword is reserved for dispatcher.retry; API callers do not expose or pass it. API catches FinancialConflict and returns 409; KeyError maps to 404. `start` catches execution failures and returns the persisted failed run, with a safe error_code. User intervention wins over a stale worker's output.

Snapshot fields: run_id, conversation_id, status, version, mas_kind, correlation_id, request, checkpoint, budget, active_seconds, final_answer, error_code. Requests/checkpoints/budgets are JSON serialization of the corresponding Pydantic contracts. final_answer is the final artifact JSON; checkpoint.artifact_ids references immutable rows. Existing AgentEvent and SSE envelopes remain unchanged; financial event types use `mas.*`.

Application assembly registers drivers via `WorkflowRegistry.register(driver)` and separate tools via existing `ToolRegistry.register(spec)`. Constructor injection is preferred for tests. Exported `workflow_registry` and `financial_tool_registry` start empty; Lead's fresh-process bootstrap populates them before worker dispatch. They never modify default_registry. Worker detects FinancialRun before selecting financial start, otherwise invokes legacy AgentOrchestrator. Lead owns API dispatch and bootstrap wiring.

## Driver and role calls

```python
class WorkflowDriver(Protocol):
    kind: Literal["market_investigation", "portfolio_rebalance"]
    specialists: SpecialistRegistry
    async def execute(self, context: RuntimeContext,
        state: MarketState | PortfolioState
    ) -> MarketInvestigationArtifact | PortfolioProposalArtifact | None: ...

SpecialistSpec(role: str, provider: ModelProvider, system_prompt: str,
    allowed_tools: frozenset[str] = frozenset(),
    result_model: type[BaseModel] = SpecialistResult)
SpecialistRegistry.register(spec: SpecialistSpec) -> None
SpecialistRegistry.get(role: str) -> SpecialistSpec
WorkflowRegistry.register(driver: WorkflowDriver) -> None
WorkflowRegistry.get(kind: str) -> WorkflowDriver

await context.invoke(role: str, invocation_key: str, task: BaseModel) -> BaseModel
await context.tool(role: str, invocation_key: str, name: str,
    payload: BaseModel) -> ToolResultEnvelope
context.tool_result_ref(invocation_key: str) -> ToolResultRef
context.checkpoint(state: MarketState | PortfolioState,
    *, action="handoff", evidence_ids: list[str] | None = None) -> None
context.consume_budget(counter: str) -> None  # rounds / hops / followups
context.check_budget() -> None
```

Context attributes: request (typed request), state (typed domain state), run_id, conversation_id, invoker. A driver is the sole domain-state writer. It selects the next role/tool from validated results, checkpoints each accepted handoff, and returns the final typed artifact. `None` releases an unfinished delivery at the current checkpoint; a later `start` continues it. Active deadline continues across unfinished deliveries, so scheduling/restoration cannot reset it. Domain drivers never call `reserve`, `record_result`, `complete` or persistence tables directly. The dispatcher completes/artifact-writes transactionally.

`task` can be the shared request or a domain-specific BaseModel carrying the current question and permitted evidence. Each model call builds a new system/user pair; task JSON is delimited as untrusted data. ModelProvider.complete must return its structured result in ModelResponse.payload. Default SpecialistResult contains role, action, summary, evidence_ids, missing_checks, hypotheses and proposed_weights. Default result role must match the invoked role. Domain workers may supply a stricter custom result_model; extra fields and time/provenance rules must remain validated by their model.

Different specialists can use separate ScriptedFakeModel scripts or independently configured provider objects. Provider objects may share a remote endpoint, but calls and prompt/context are separate. No hidden reasoning or prompt text is persisted in events. Tool calls enforce role allowlists plus read_only=True and side_effect=False, both through the invoker and the context. Tools are executed by the existing ToolExecutor, with existing ToolCall/ToolResult audit rows. Envelope.call_id is the persisted ToolCall UUID, not the logical invocation key. Failed tool envelopes remain replayable results; Coordinator decides whether to degrade or stop.

`tool_result_ref` returns a typed ToolResultRef(run_id, tool_call_id, tool_result_id, tool_name, tool_version). tool_call_id is ToolCall.id, and tool_result_id is ToolResult.id; these are the IDs used by NumericFact and deterministic risk/simulation references. Fresh/cached/restored invocations return the same persisted IDs. Lookup is scoped to the producing run and requires a completed tool invocation and matching audit row; missing, model-only, pending, or foreign references raise KeyError. A persisted failed tool envelope can have an audit reference, so domain code must verify its status before using numerical output.

Domain driver fragment using only public APIs (history_input is the registered tool's typed input):

```python
history = await ctx.tool("investigator", "history:round1", "get_market_history", history_input)
audit = ctx.tool_result_ref("history:round1")
# After deterministic output/status validation, attach the audit to a typed fact.
fact = NumericFact(name="computed_return", value=validated_return, unit="ratio",
    evidence_id=validated_evidence_id, tool_result_id=audit.tool_result_id)
```

Invocation keys must be stable, run-local and unique for each logical operation, for example `price-volume:round1:market-history` and `critic:round1`. Reusing a succeeded key returns its persisted schema-validated output without billing/calling again. Reusing a key for a different role/kind/input conflicts. Identity hashes cover model task, result schema and system prompt; tool identity covers name and input. Drivers must not change these behind an existing key. A reserved/failed operation after crash may be attempted again, consuming another budget reservation; there is no exactly-once guarantee for external billing after a crash between remote completion and DB persistence.

## Minimal independent driver example

```python
class MarketDriver:
    kind = "market_investigation"
    def __init__(self, investigator_provider, critic_provider):
        self.specialists = SpecialistRegistry()
        self.specialists.register(SpecialistSpec(
            "investigator", investigator_provider, "Investigate evidence only",
            frozenset({"get_market_history"})))
        self.specialists.register(SpecialistSpec(
            "critic", critic_provider, "Check the independent evidence"))

    async def execute(self, ctx, state):
        for role in ("investigator", "critic"):
            if any(result.role == role for result in state.results):
                continue
            result = await ctx.invoke(role, role + ":1", ctx.request)
            state.results.append(result)
            # Real Coordinator selects subsequent work using result.missing_checks,
            # hypotheses and available evidence; this example is intentionally fake.
            ctx.checkpoint(state, action="handoff", evidence_ids=result.evidence_ids)
        return MarketInvestigationArtifact(
            producing_run_id=ctx.run_id, symbol=ctx.request.symbol,
            as_of=ctx.request.as_of, status="partial",
            limitations=["Example has no deterministic evidence tools"])

registry = WorkflowRegistry()
registry.register(MarketDriver(
    ScriptedFakeModel([{"kind": "result", "payload": {
        "role": "investigator", "action": "finding", "summary": "missing evidence"}}]),
    ScriptedFakeModel([{"kind": "result", "payload": {
        "role": "critic", "action": "verdict", "summary": "remain partial"}}])))
dispatcher = FinancialMASDispatcher(session_factory, registry, financial_tools)
```

Portfolio uses the same seam with kind portfolio_rebalance and PortfolioState. Its final PortfolioProposalArtifact must carry constraint_check; feasible additionally requires nonempty proposed weights, pass, deterministic risk_comparison and simulation. Missing data is insufficient_data, never a synthetic feasible result. Independent fake drivers for both kinds are executable in test_financial_runtime.py.

## Contract fields and artifacts

All FinancialModel objects forbid extras/nonfinite numbers and normalize aware timestamps to UTC. RunBudget ceilings: model16, tool20, rounds3, hops2, followups1, active120 seconds; callers may only lower them. New-run counters must be zero. Reservations commit before calls, including failed attempts. The dispatcher persists active_since and active_seconds; review/paused time is excluded. Lease recovery waiting counts as active time; default lease30 seconds is renewed every10 seconds during outstanding calls. A crash can therefore consume part of the remaining allowance before reclaim. Resume cannot reset counters/deadline.

Checkpoint(schema_version=1, state=MarketState|PortfolioState discriminator kind, artifact_ids). MarketState contains phase, typed results/evidence/hypotheses/numeric_facts and missing_checks. PortfolioState contains phase, typed results/proposed_weights/constraint_check/risk_comparison and missing_checks. Driver-specific questions belong in typed tasks; accepted state fields cannot silently become broad dict blobs.

AllocationConstraints: max_weight_by_symbol, min_cash_weight, max_equity_weight, max_sector_weight, weight_tolerance. Constraint tolerance is strictly positive and at most 1e-4, default 1e-6, matching the deterministic tool's supported range. Adapters pass the explicit tolerance through without clamping. All symbol/sector mappings, including specialist/state candidates and artifact weights, validate Mapping inputs before Pydantic key coercion: reject non-string keys, blanks and normalized collisions, including bytes/string collisions. Valid UserDict/MappingProxyType mappings and numeric Decimal/string values remain supported. ConstraintCheck: pass/fail/unknown, typed ConstraintViolation entries and unknown reasons. NumericFact requires evidence_id and tool_result_id. EvidenceRef distinguishes published_at/available_at/observed_at; domain verification must reject unknown/future availability for historical attribution. Market artifact fields and Portfolio artifact fields are defined by contracts.py, not by tool output adapters. Proposed/current nonempty weight maps require CASH, finite nonnegative weights and sum=1 within 1e-6. Sector/symbol cap checks are deterministic tool responsibility.

```python
ArtifactStore(session_factory)
store.get(artifact_id: str, *, conversation_id: str,
    as_of=None, symbols: list[str] | None = None, schema_version=1
) -> MarketInvestigationArtifact | PortfolioProposalArtifact
```

Store has no public update/delete. Final insertion is owned by dispatcher transaction and enforces producing run, request timepoint, domain kind and requested Market symbol or Portfolio holdings snapshot ID. A mismatch fails before any final artifact or completion event is persisted. Repeated identical insertion returns the same artifact; different payload at the same artifact key is rejected. Reads enforce conversation, schema, optional exact UTC as_of and symbol subset. Cross-MAS router must also check its absolute envelope deadline before consuming.

FinancialRelation stores separate source/target/correlation/type/envelope/idempotency metadata. `link_runs` uses source-run CAS and event allocation; both runs must have the same conversation, correlation and request as_of, distinct IDs and distinct kinds. A combined relation may omit envelope. An envelope must match source/target kinds, source run, correlation, as_of and key; expired/future-created envelopes are rejected. Artifact refs must be immutable source-run snapshots at the correct version/timepoint; a Market target additionally requires its symbol in the referenced artifact. W6 owns additional portfolio scope checks, TTL consumption, cycle, hop and follow-up policy, using public APIs. Terminal producers can transfer final evidence; terminal runs cannot issue new requests. `relations` returns links with relation_id, conversation_id, source_run_id, target_run_id, correlation_id, relation_type, idempotency_key and envelope. Identical repeated insertion with the current version returns the same relation without changing run version; stale version and payload conflicts return 409. No router/domain code needs private `_mutation`.

## Evidence and limits

W1 validation uses disposable SQLite databases and deterministic providers. Tests cover independent role contexts, two independent runs, checkpoint recovery, duplicate/concurrent claims, intervention fencing, phase-preserving pause, cancellation, reservations, active deadline, scoped artifacts, tool permissions/audit, fresh upgrade, 0003 upgrade and downgrade preserving General rows. PostgreSQL JSONB DDL is compiled separately. This does not establish live PostgreSQL/Redis/Celery restart behavior or external provider quality. Migration 0001 pins original table ownership; 0004 owns only four financial tables. Downgrade deletes financial history and is tested only on disposable databases.

## Atomic cross-message admission (ADR-0003 additive seam)

```python
dispatcher.admit_cross_message(source_run_id: str, target_run_id: str,
    *, expected_source_version: int, expected_target_version: int,
    envelope: CrossMASEnvelope) -> dict
```

This API creates an immutable `cross_admitted` relation and audit events for both runs in one transaction. Only this API creates that reserved relation type. Its return fields match `relations`; W6 executes only admitted envelopes. Legacy `link_runs` remains a diagnostic seam, keeps its source-version replay semantics, and rejects the reserved type. All envelope-bearing relations require a nonblank, conversation-unique message ID, including diagnostic relations.

Financial relation writers, cross-counter reservations, creation and retry membership acquire a no-op conversation-row UPDATE before run CAS. Admission checks both caller versions in stable run-ID order and leaves status, checkpoint, claim and lease untouched. Stale versions and terminal recipients reject new messages. Exact source/target/envelope replay of an admitted key returns its historical relation before version, terminal and TTL checks, without counters or events. Consumers must check the absolute deadline again; historical replay does not extend validity. Changed payloads and diagnostic key collisions conflict.

Persisted counters are authoritative. All financial members of the conversation/correlation contribute to hop/follow-up totals; the smallest member ceiling applies to charged work. Creation/retry membership starts at commit. A lower-ceiling join can prevent further work without rewriting counters or revoking a zero-cost resolution. `RuntimeContext.consume_budget('hops'/'followups')` preserves claim requirements and uses this same correlation accounting and lock order. Round reservations keep their single-run path.

An initial Market READY transfer charges one source hop. A Portfolio-to-Market `MARKET_EVIDENCE_REQUEST` charges one source hop and follow-up. Exactly one reverse READY or UNAVAILABLE may resolve that admitted request without another hop: causation must identify its unique message ID, exact reversed endpoints and correlation, creation cannot precede the request, and deadline cannot exceed it. READY requires the producing Market run's immutable artifact at the same schema/timepoint; completed producers may transfer final evidence. UNAVAILABLE has no artifact and charges no new work, including a terminal producer's diagnostic. Without causation it resolves no wait edge. `PORTFOLIO_IMPACT_REQUEST` is unsupported and rejects without mutation. Outstanding unresolved requests between nonterminal runs form the wait graph; new requests reject cycles. Diagnostic legacy relations neither authorize work nor resolve waiting requests.

W6 additionally checks Portfolio holdings scope through its trusted immutable snapshot loader before admission and consumption. This shared seam validates run/envelope direction, absolute creation/deadline, schema, artifact ownership/timepoint, and any Market recipient symbol, but does not load Portfolio holdings. Envelope cross ceilings and counters are validated for work messages; they never grant budget authority. Failure rolls back both run versions, counters, relation and independent monotonic audit events. No schema, migration, General registry or infrastructure change is required. Local tests use disposable SQLite threads; PostgreSQL conversation-lock UPDATE is compiled, with no live Docker/PostgreSQL recovery claim.

## Immutable execution profiles (ADR-0004 additive seam)

```python
FinancialMASDispatcher(session_factory, drivers=None, tools=None, *,
    clock=utcnow, lease_seconds=30, execution_profile: str | None = None)
```

`execution_profile` identifies a trusted, versioned provider/data assembly. It is a string of 1–128 characters with no surrounding whitespace; invalid values raise exported `FinancialExecutionProfileError(ValueError)` instead of coercing or trimming aliases. The dispatcher exposes its constructor profile as a read-only property. Non-None profiles are persisted in the existing immutable `creation_inputs` JSON and participate in full ordinary/concurrent create idempotency comparison. Legacy None omits the JSON key, preserving the previous identity. `snapshot` adds the stored `execution_profile`, returning None for legacy runs.

Before `start` acquires a claim, performs CAS, emits events or calls any provider/tool, its profile must match the stored profile exactly. A mismatch raises `FinancialExecutionProfileError` outside the stale-worker conflict handler and preserves all persisted state. This also applies to duplicate delivery of terminal runs. None/profile and differently named profiles cannot substitute for each other. Reads and versioned approve/pause/resume/cancel remain available without a matching assembly.

`retry` checks the parent's profile under the canonical conversation lock before creating or replaying a child; the insertion transaction rechecks the parent profile with retry authority. A matching assembly preserves that profile along with existing retry ancestry, correlation and reset counters. Matching legacy None dispatchers continue to execute and retry directly. No artifact/request schema, table, migration or General registry changes are introduced.

The shared runtime checks identity; application assembly must bind each identifier to the same trusted versioned configuration across restarts. Factory/worker reconstruction is separately owned and must reject missing/unknown deployment mappings rather than falling back to synthetic data. The initial demo identity is `synthetic-demo-v1`; custom configuration cannot reuse that reserved identity. A matching identifier alone is no proof of real-provider quality or live distributed recovery. Local validation includes fresh Python processes, complete database before/after comparisons on rejection, no provider calls, concurrent identity checks, legacy compatibility and the Backend regression suite.
