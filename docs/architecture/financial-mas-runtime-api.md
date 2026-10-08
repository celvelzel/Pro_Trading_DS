# Financial runtime API v1

Status: executable W1 contract, pending independent W1 review. Import from `agent.shared` with absolute backend and lobster_quant directories in PYTHONPATH. ADR-0002 governs budgets, concurrency, migration ownership and read-only semantics. No Market/Portfolio implementation is imported by this package.

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

The existing conversation must exist. `create` requires a registered driver. Keys are unique per conversation; identical repeated creation returns the persisted run, different inputs conflict. Mode is review/auto. Review starts at waiting_user; approve permits read-only execution. Resume restores the phase preceding pause (including queued/planning/waiting_user); Lead dispatches start after approve/resume when execution is eligible. Cancel works for every nonterminal state, including created/queued/planning/waiting_user/paused. Completed/failed/cancelled/expired are terminal. Terminal retry creates a different AgentRun and preserves parent_run_id retry ancestry atomically with creation. Existing non-retry keys cannot be reused for retry. The internal `_retry_parent_id` create keyword is reserved for dispatcher.retry; API callers do not expose or pass it. API catches FinancialConflict and returns 409; KeyError maps to 404. `start` catches execution failures and returns the persisted failed run, with a safe error_code. User intervention wins over a stale worker's output.

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
context.checkpoint(state: MarketState | PortfolioState,
    *, action="handoff", evidence_ids: list[str] | None = None) -> None
context.consume_budget(counter: str) -> None  # rounds / hops / followups
context.check_budget() -> None
```

Context attributes: request (typed request), state (typed domain state), run_id, conversation_id, invoker. A driver is the sole domain-state writer. It selects the next role/tool from validated results, checkpoints each accepted handoff, and returns the final typed artifact. `None` releases an unfinished delivery at the current checkpoint; a later `start` continues it. Active deadline continues across unfinished deliveries, so scheduling/restoration cannot reset it. Domain drivers never call `reserve`, `record_result`, `complete` or persistence tables directly. The dispatcher completes/artifact-writes transactionally.

`task` can be the shared request or a domain-specific BaseModel carrying the current question and permitted evidence. Each model call builds a new system/user pair; task JSON is delimited as untrusted data. ModelProvider.complete must return its structured result in ModelResponse.payload. Default SpecialistResult contains role, action, summary, evidence_ids, missing_checks, hypotheses and proposed_weights. Default result role must match the invoked role. Domain workers may supply a stricter custom result_model; extra fields and time/provenance rules must remain validated by their model.

Different specialists can use separate ScriptedFakeModel scripts or independently configured provider objects. Provider objects may share a remote endpoint, but calls and prompt/context are separate. No hidden reasoning or prompt text is persisted in events. Tool calls enforce role allowlists plus read_only=True and side_effect=False, both through the invoker and the context. Tools are executed by the existing ToolExecutor, with existing ToolCall/ToolResult audit rows. Failed tool envelopes remain replayable results; Coordinator decides whether to degrade or stop.

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

AllocationConstraints: max_weight_by_symbol, min_cash_weight, max_equity_weight, max_sector_weight, weight_tolerance. ConstraintCheck: pass/fail/unknown, typed ConstraintViolation entries and unknown reasons. NumericFact requires evidence_id and tool_result_id. EvidenceRef distinguishes published_at/available_at/observed_at; domain verification must reject unknown/future availability for historical attribution. Market artifact fields and Portfolio artifact fields are defined by contracts.py, not by tool output adapters. Proposed/current nonempty weight maps require CASH, finite nonnegative weights and sum=1 within 1e-6. Sector/symbol cap checks are deterministic tool responsibility.

```python
ArtifactStore(session_factory)
store.get(artifact_id: str, *, conversation_id: str,
    as_of=None, symbols: list[str] | None = None, schema_version=1
) -> MarketInvestigationArtifact | PortfolioProposalArtifact
```

Store has no public update/delete. Final insertion is owned by dispatcher transaction and enforces producing run, request timepoint and domain kind. Repeated identical insertion returns the same artifact; different payload at the same artifact key is rejected. Reads enforce conversation, schema, optional exact UTC as_of and symbol subset. Cross-MAS router must also check its absolute envelope deadline before consuming.

FinancialRelation stores separate source/target/correlation/type/envelope/idempotency metadata. `link_runs` uses source-run CAS and event allocation; both runs must have the same conversation, correlation and request as_of, distinct IDs and distinct kinds. A combined relation may omit envelope. An envelope must match source/target kinds, source run, correlation, as_of and key; expired/future-created envelopes are rejected. Artifact refs must be immutable source-run snapshots at the correct version/timepoint; a Market target additionally requires its symbol in the referenced artifact. W6 owns additional portfolio scope checks, TTL consumption, cycle, hop and follow-up policy, using public APIs. Terminal producers can transfer final evidence; terminal runs cannot issue new requests. `relations` returns links with relation_id, conversation_id, source_run_id, target_run_id, correlation_id, relation_type, idempotency_key and envelope. Identical repeated insertion with the current version returns the same relation without changing run version; stale version and payload conflicts return 409. No router/domain code needs private `_mutation`.

## Evidence and limits

W1 validation uses disposable SQLite databases and deterministic providers. Tests cover independent role contexts, two independent runs, checkpoint recovery, duplicate/concurrent claims, intervention fencing, phase-preserving pause, cancellation, reservations, active deadline, scoped artifacts, tool permissions/audit, fresh upgrade, 0003 upgrade and downgrade preserving General rows. PostgreSQL JSONB DDL is compiled separately. This does not establish live PostgreSQL/Redis/Celery restart behavior or external provider quality. Migration 0001 pins original table ownership; 0004 owns only four financial tables. Downgrade deletes financial history and is tested only on disposable databases.
