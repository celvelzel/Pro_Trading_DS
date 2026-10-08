# Standalone Portfolio MAS

The `agent.portfolio_mas.PortfolioDriver` implements `portfolio_rebalance` using
the frozen W1 financial runtime and five registered W3 read-only tools. It does
not import Market MAS, PortfolioStore, write routes, brokers or LangGraph.
Application bootstrap explicitly registers the driver and tools; importing this
package changes no global registry.

## Assembly

```python
deps = PortfolioDependencies(
    snapshot_loader=trusted_saved_snapshot_loader,
    history_loader=trusted_point_in_time_history_loader,
    classifications=trusted_asset_classifications,
)
driver = PortfolioDriver(providers, deps, artifact_store=scoped_artifact_store)
workflows.register(driver)
portfolio_snapshot.register_tools(tools, {"snapshot_loader": deps.snapshot_loader})
portfolio_risk.register_tools(tools)
allocation.register_tools(tools)
```

`providers` maps `coordinator`, `opportunity`, `risk`, `constraint`, `verifier` to
ModelProvider objects. All five independently call `complete` with separate
system/user contexts; each has a different tool allowlist. A provider endpoint
may be shared. No provider automatically loads credentials or incurs billing.
`SyntheticPortfolioModel(role)` is an explicitly synthetic no-network demo
provider, with no forecast or real investment recommendation claim.

`PortfolioDependencies` is frozen and contains:

- `snapshot_loader: Callable[[str], SnapshotRecord | dict | None]`, consumed by
  W3's registered snapshot tool only. It must read explicit trusted immutable
  saved holdings, cash, quotes and timepoint metadata. No implicit default cash
  or cost-basis quote is accepted.
- `history_loader: Callable[[SnapshotRecord, datetime], tuple[AssetHistory, ...] | Awaitable[tuple[AssetHistory, ...]]]`.
  The original validated snapshot and request as_of are passed to this trusted
  adapter. It supplies immutable adjusted/total-return histories;
  W3 checks availability, date alignment, currency and statistical sufficiency.
  Empty histories represent unavailable data. Cash-only simulation requires an
  explicit eligible history supplying the calendar, even with no equity holdings.
- `classifications: Mapping[str, AssetClassification]` from trusted code, with
  source metadata. Symbol and sector normalization uses W3 guards. Model claims
  cannot manufacture classifications.

Loader results and optional artifact selection must be immutable across a run's
replays. Changing them behind an already completed invocation produces the frozen
runtime's input identity conflict rather than silently replacing evidence.

## Coordination and numeric verification

Coordinator is the sole writer of typed PortfolioState. Opportunity proposes
qualitative candidate directions; Risk and Constraint independently review tool
evidence; Verifier independently accepts or rejects the fully calculated proposal.
Their financial claims never enter final numeric fields. Risk/Constraint rejection
or missing checks prevents feasibility; Verifier approval is additionally required
in full mode. Original user constraints, including weight_tolerance, pass unchanged
to W3. Sector keys and classification sectors are uppercase.

The tools read/value the original snapshot, calculate before-risk, generate bounded
candidates, validate each proposed allocation, calculate after-risk and simulate.
After-risk uses a virtual SnapshotRecord: each proposed positive holding's quantity
is `original_total_value * proposed_weight / original_known_market_price`, with
explicit proposed cash and original quote metadata. Unknown/new symbols cannot
be valued. W3 revalues this record and computes deterministic risk. The original
record and saved file never change. Final artifact snapshot_id is always the
request's original snapshot ID, never the virtual snapshot ID.

Every successful deterministic output is tied to `ctx.tool_result_ref(key)`:
evidence_ids are persisted ToolResult primary keys, risk metrics reference their
respective actual results, and simulation references its actual result. No logical
invocation key, model-provided citation or failed result becomes financial evidence.
Current and proposed weights come from these checked calculations/candidates.
Simulation currently uses explicit zero fees/slippage and daily common-observation
rebalance; these are recorded assumptions, not estimates of actual execution cost.
Risk is a historical constant-weight proxy, not actual holding history or a forecast.

There are at most two coordination rounds. An invalid proposal generates a
checkpointed revision_request with the previous proposal/check and independently
reviewed evidence. A feasible revised candidate must actually pass the same
unchanged constraints. Candidate-tool proven contradictions/capacity exhaustion
produce infeasible. Unknown classifications/inconclusive bounded search, missing
quotes/history/calendar, rejected proposals and exhausted revision produce
insufficient_data. A failed arbitrary model proposal never proves infeasibility.
The strict frozen artifact weight schema is checked in addition to W3 tolerance.

## Lifecycle and optional Market evidence

Stable keys include `snapshot:v1`, `risk:current:v1`, `candidates:v1`, and round
qualified role/check/risk/simulation keys. Checkpoints track round0,
revision_ready, round1, final. Replay reconstructs completed prior phases via public
cached calls without reserving a second round or calling models again; incomplete
calls may retry under W1's documented budget/billing semantics. Cancellation,
pause, active deadlines and worker fencing are supplied by RuntimeContext.
`yield_after_revision=True` releases a delivery at the revision checkpoint for
deterministic restart testing. It is not needed in ordinary assembly.

Optional `request.market_artifact_id` is read via an injected scoped shared
ArtifactStore. An optional sync or async resolver allows W6 to attach evidence after
the two immutable run requests have already been created:

```python
artifact_resolver(run_id: str, conversation_id: str,
                  request: PortfolioReviewRequest) -> MarketInvestigationArtifact | None | Awaitable[MarketInvestigationArtifact | None]
PortfolioDriver(providers, deps, artifact_resolver=artifact_resolver)
```

The resolver is a trusted application adapter and must resolve authorized
immutable relation/artifact rows through scoped shared ArtifactStore, enforcing
conversation/schema/as_of and relation authorization. The driver independently
requires a typed Market artifact with exact request as_of and its symbol within
the original snapshot's holdings. Unavailable/rejected optional artifacts add a
limitation and do not prevent standalone numeric completion. The full external
artifact is untrusted task data; it cannot override tool checks. The resolver must
select a stable artifact once role invocation begins. W6 owns transfer deadlines,
cycle/budget policy and durable relation selection; this driver creates no peer
run and waits for no peer service.

Injected history/resolver/store calls run through `ctx.external`; synchronous
callables are offloaded with `asyncio.to_thread`, and returned awaitables are
awaited. This keeps the event loop responsive and preserves runtime deadline,
lease and intervention fencing. History adapter failure is insufficient_data;
optional artifact adapter failure (including peer timeout) adds a limitation and
continues standalone analysis. BudgetExhausted/FinancialConflict/RunInterrupted
are never converted into missing data. Raw adapter exception text is not exposed.
Python worker threads cannot be forcibly killed: runtime delivery can be expired
or cancelled while a synchronous read continues, and `asyncio.run` may wait for
default-executor shutdown. This is the same limitation as the existing W3
ToolExecutor, not a process hard-kill guarantee. Trusted adapters must remain
read-only and configure their own underlying I/O timeouts.

## Evaluation and validation boundaries

`mode="full"` is the default. `mode="single"` invokes only Coordinator and
preserves exactly the same data, deterministic tool pipeline and budget ceilings.
`mode="no_verifier"` keeps Coordinator, Opportunity, Risk and Constraint calls,
omitting only the independent model Verifier. Both retain deterministic validation.
These are W8 ablation hooks; no superiority or production provider quality is
claimed. Tool permissions remain role-scoped in the single-agent variant.

`backend/tests/test_portfolio_mas.py` uses disposable SQLite, actual frozen runtime
and registered W3 tools with explicit synthetic snapshots/history/providers. It
covers standalone feasibility, infeasibility, missing prices/classification,
zero cash, explicit cash-only calendars, real candidate revision, checkpoint
resume/cache replay, malicious proposals, verifier rejection, cancellation and
active deadline, immutable source hashes, real audit IDs and ablation parity.
Production PostgreSQL/Redis/Celery restarts, live loaders/model quality and real
market data remain integration/deployment validation responsibilities.
