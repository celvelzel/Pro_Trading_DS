# Independent Market investigation

`agent.market_mas.MarketCoordinator` implements the frozen W1 WorkflowDriver.
`create_market_driver(providers, *, mode='autonomous', max_rounds=3,
yield_after_handoff=False)` constructs it; `register_market_driver(registry,
providers, **kwargs)` additionally registers it. `providers` explicitly maps
`coordinator`, `price_volume`, `macro_sector`, `event`, `critic` to ModelProvider
objects. Each role makes a separate model call with a distinct prompt and typed
board slice. Assembly separately registers the three W2 read-only tools with
injected history/event dependencies. No Portfolio implementation is imported.

The Coordinator first calls deterministic anomaly with SPY, establishes market,
sector, company-event and unknown competing hypotheses, then invokes independent
roles. Macro uses the requested sector benchmark; Event obtains historical
records. Price receives market facts; Event receives event text; Macro receives
market/macro evidence; Critic and Coordinator see the accepted board. Role
allowlists enforce read-only operations; Critic has no tools. Only the
Coordinator mutates MarketState and calls checkpoint.

Validated missing_checks (`history`, `market`, `sector`, `events`) select the
next actual tool after the Critic's challenge, then independent Coordinator and
Critic calls reconsider the board. At most two follow-up rounds and nine model
calls occur with default settings. Request/runtime ceilings may be lower;
runtime safely fails if initial roles cannot fit. Failed tools degrade to
explicit insufficient evidence. Failed/invalid models fail the run through W1.
Logical invocation keys and phase checkpoints remain stable across delivery
restart; persisted tool envelopes and calls are replayed, retaining actual
ToolResult UUIDs. `yield_after_handoff` supports reproducible checkpoint demos.
Changing execution configuration behind an existing run is unsupported.

NumericFacts are copied only from validated W2 anomaly fields and cite
`ctx.tool_result_ref(key).tool_result_id`, not the W2 content reference or
logical invocation key. Tool scope must match request symbol/as_of. Event
publication and availability must both be known and no later than as_of;
W2 validates content hashes and excludes future/unknown text before returning.
Model citations must belong to its provided evidence slice. Arbitrary model
claims and numbers never enter the final artifact: explanations use a closed
qualitative vocabulary, and support/against IDs remain explicitly unverified.
Source text is untrusted data, including eligible rumors and injection attempts.
Source authenticity still depends on audited caller adapters; the driver does
not authenticate publishers. Consequently results are partial or
insufficient_evidence, never confirmed causes.

`mode='fixed'` disables adaptive checks while keeping the initial roles/tools.
`mode='single'` uses only the Coordinator model with the same initial market,
sector and event tool inputs. All modes use the same runtime ceilings and
injected datasets; W8 can compare actual reserved model/tool cost and artifact
verification. These are experimental baseline hooks, not claims of quality.
Synthetic tests use the versioned W2 fixture pack and ScriptedFakeModel. No
default remote provider, secrets, portfolio writes or trading are configured.

For reusable offline assembly, inject `{role: SyntheticMarketModel(role) for
role in ('coordinator', 'price_volume', 'macro_sector', 'event', 'critic')}`.
The exported stateless provider reads only its supplied task board. Critic
requests history for text labeled rumor/denial/instruction, events for absent
events, or sector for absent sector facts. This deliberately simple synthetic
policy uses no per-case answer script and invents no numeric facts. Its token
usage is unspecified; zero remote calls is not a real-model cost measurement.

Validation: `PYTHONPATH=backend;lobster_quant python -m pytest
backend/tests/test_market_mas.py -q` on Windows (set PYTHONPATH separately).
Tests use disposable SQLite and actual typed W2 tools, check persisted numeric
audit rows, independent roles, evidence-driven routing, failed tools, temporal
fixtures, forged references, cancellation, provider timeout, low budget,
checkpoint restoration and baseline hooks. PostgreSQL/Celery/live-provider
acceptance and model quality require separate integration/evaluation gates.
Independent Reviewer acceptance is required before W4 is declared PASS.
