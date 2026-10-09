# Financial MAS W8 evaluation

This page defines the reproducible workflow evaluation and its scoring boundaries. The 12 Market and 30 Portfolio workflow-v1 fixture cases remain unchanged. A separate Combined smoke uses the already accepted W7 synthetic demo snapshot; it is not included in either case denominator.

## Execution

From the repository root, run:

```powershell
$env:PYTHONPATH="backend;.;lobster_quant"
python eval/run_financial_mas_w8.py --domain all --output-dir logs/financial-mas/w8-eval-<new-run-name>
```

The output directory must be empty. The runner refuses an existing nonempty destination so previous evidence is preserved. It verifies the workflow-v1 fixture manifest, creates an isolated temporary SQLite database, assembles the accepted dispatcher with `demo=False` and the explicit `w8-fixture-v1` profile, creates each run, and calls the persisted runtime's `start` path. It exports the stored AgentRun, FinancialRun, invocations, tool calls/results, events, artifacts, and relations to per-case JSONL records before the temporary database is removed.

The canonical W8 v1 result set remains 36 Market rows, 120 Portfolio rows, and one separate Combined smoke. Follow-up comparisons can add strategy rows from the same unchanged 12/30 fixture sets; they belong in a new output directory and must not overwrite the canonical v1 evidence.

No public API or real provider is used. Market evidence and Portfolio snapshots/histories are immutable synthetic adapters; model roles use deterministic no-network synthetic providers. The runner verifies that every registered tool is read-only and has no side effect. It does not read user holdings, call a broker, submit orders, or modify a portfolio. Token usage is explicitly `null` because the runtime does not persist token counts.

Each strategy receives the same request, fixture adapter, and default `RunBudget` ceilings within its domain. Actual call counts are read from persisted budget counters and cross-checked against persisted invocation rows. Latency is measured around runtime execution; it is environment-dependent and is not a model-quality score.

| Domain | Comparator | Meaning |
|---|---|---|
| Market | `autonomous` | Accepted adaptive coordinator/specialist workflow |
| Market | `fixed` | Same specialists and tools, no dynamic follow-up routing |
| Market | `single` | One coordinator model call path with the same deterministic tools; its synthetic response cites only evidence IDs supplied in that persisted model invocation |
| Portfolio | `full` | Accepted adaptive workflow with independent verifier |
| Portfolio | `fixed` | One-pass fixed specialist sequence, deterministic checks, and verifier; no revision round |
| Portfolio | `single` | One coordinator model call path with the same deterministic tools |
| Portfolio | `no_verifier` | Verifier ablation of the adaptive workflow; this is not the fixed baseline |
| Portfolio | `no_independent_risk_critic` | Adaptive multi-agent ablation that omits both the independent risk-review model role and the risk-critic verifier; it retains the Opportunity, Coordinator, and Constraint specialists plus deterministic risk calculations and allocation/constraint gates |

`no_verifier` and `no_independent_risk_critic` are distinct. The former still invokes the independent `risk` model review; the latter omits both that review and the verifier, whose independent review also includes risk. The latter comparator is used only by the explicit W8 evaluation profile and does not change the application default or API workflow selection. Persisted invocation roles and counters are the evidence for its actual model cost.

The default application modes remain Market `autonomous` and Portfolio `full`. The comparison is a synthetic runtime-conformance experiment, not a strong real-LLM benchmark. Synthetic providers do not establish real-model reasoning or market-data quality.

## Metrics and denominators

Market metrics are computed per case and aggregated by summing their numerators and denominators:

- Event eligibility count and artifact status correctness use all 12 Market cases.
- Evidence citation precision uses explicit hypothesis `support_ids` and `against_ids`. Its denominator is the count of those citation positions; the numerator counts references resolving to evidence or result references in persisted ToolResult rows. Embedded artifact evidence is scored separately for provenance, so it cannot validate itself. For `market:single`, the one coordinator response references IDs from its actual supplied evidence board; the runner does not add citations after the model response.
- Numeric fact accuracy uses the fixture's six deterministic gold facts per case. Each fact is compared at absolute tolerance `1e-9`; missing facts remain in the denominator.
- Timing violations count cited fixture events with missing `published_at`/`available_at` or either timestamp later than the request `as_of`. The denominator is the number of cited event references, not the entire evidence board.
- Unsupported causal claims are reported as not scorable. The persisted final schema has unverified hypotheses but no distinct causal-assertion field; a `supported` hypothesis disposition alone is not treated as a causal claim.

Portfolio metrics use the following denominators:

- Hard-constraint safety uses all 30 cases. A violation is counted only if the final artifact says `feasible` while its deterministic `constraint_check` is not `pass`.
- Infeasibility detection includes only input-determined fixture cases. True positives/false negatives use the two constraint-proven infeasible cases; false positives use cases whose fixture independently labels the feasible set feasible. Positive and negative denominators are reported separately.
- Missing-data safety includes only fixtures with data/classification reasons that should independently prevent a feasible declaration. It does not score invalid model-proposal fixtures as missing data: the model is free to propose a different valid allocation, as stated in the fixture preparation record.
- Status accuracy is limited to input-determined infeasible and missing-data cases. Proposal-conditioned status expectations are retained in each raw record but are not treated as a required model output.
- Risk calculation accuracy compares persisted artifact values with a direct calculation from the same immutable snapshot, actual selected weights, and fixture histories. Accuracy's denominator is each observed numeric risk field on a fixture side marked data-valid by the manual gold; tolerance is `1e-10`. Computable fields and output coverage are reported separately, so an omitted result is visible without treating expected missing-data cases as inaccurate calculations.
- Simulation consistency independently recomputes every daily NAV point from the persisted tool input when fees and slippage are zero. The denominator is the number of expected NAV points; final net return must also match both the persisted tool result and artifact within `1e-16`. Cases without an executed simulation contribute zero points, rather than being silently treated as correct.

The separate `synthetic_demo_v1.json` Combined smoke uses snapshot id `synthetic-mu-soxx-v1`, the existing W7 `DEMO_AS_OF`, and `demo_market_dependencies()`. Its raw row includes both run IDs, both run/artifact/counter records, all persisted relations, completion status, and timing. It demonstrates the admitted Combined path only; it is not a third benchmark sample.

## Evidence and limitations

Each domain/strategy JSONL row includes the exact request and fixture hashes, output artifact, persisted runtime records, measured wall time, actual and maximum budgets, and metric values. `summary.json` aggregates these rows without replacing the raw evidence. Reruns generate new random run/conversation IDs and new timing measurements, while fixture hashes, input requests, provider behavior, and deterministic tool outputs remain reproducible.

Rows distinguish execution from evaluation with `run_status`, `evaluation_status`, and `failure_stage`. A scoring exception after a completed run is retained as `evaluation_error` with its actual run ID, budgets, counters, artifact, and persisted records. A pre-execution failure remains a `harness_error`; failures after run creation retain available run identity and snapshot data and are labelled by the capture/runtime stage. If a post-run snapshot/export fails but persisted records can be recovered, the runner restores the budget and counters from those records and keeps the runner exception in `capture_error`; `run_error_code` remains the persisted runtime error field. `metric_scoring_coverage` reports scored and unscored fixture rows. Metrics with fixture-defined denominators give unscored rows zero credit, while metrics whose denominator depends on emitted output are marked unscorable when scoring coverage is incomplete. Portfolio status eligibility and its denominator come from fixture gold, including rows that fail execution or scoring.

All claims are limited to the local synthetic SQLite execution. These results do not validate PostgreSQL concurrency, Redis/Celery delivery, live market-data freshness, live provider behavior, future investment performance, or causal attribution.
