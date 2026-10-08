# Deterministic portfolio tools (W3)

These five read-only tools have local Pydantic contracts and explicit registration functions. Importing them never registers financial tools in the General registry. They have no provider/network dependency, storage constructor, order endpoint or write operation. Lead assembles the financial registry after review; W5 adapts shared runtime contracts to these input models.

## Registration and callable APIs

```python
from agent.tools.registry import ToolRegistry
from agent.tools import portfolio_snapshot, portfolio_risk, allocation

registry = ToolRegistry()
portfolio_snapshot.register_tools(registry, {"snapshot_loader": trusted_readonly_loader})
portfolio_risk.register_tools(registry)
allocation.register_tools(registry)
```

The loader is a synchronous callable `snapshot_id -> SnapshotRecord | dict | None`, supplied by trusted application code. It must read a saved immutable snapshot rather than synthesize historical holdings from current holdings. No live loader is installed by this change. Loader exceptions propagate to the existing executor's safe error envelope. Invalid structural data yields its validation error; represent unavailable fields with None/absent quotes to obtain `insufficient_data`.

- `get_portfolio_snapshot(SnapshotInput, loader) -> SnapshotOutput`: ID, source, explicit holdings/cash/base currency, saved holdings effective timestamp, quote source/currency/effective/available timestamps are checked. Historical `as_of` cannot precede holdings. Quotes marked cost_basis are refused. Missing cash never becomes 100000. Mixed currencies are refused; no FX adapter is provided. Default snapshot/quote maximum age is 86400 seconds; input can choose 0 through 604800. Hash is SHA256 of canonical sorted JSON of the complete record. Positive portfolio value is required. Empty holdings with explicit positive cash is valid. Zero-share positions need no quote but retain currency checking. Snapshot and nested holding/quote models are frozen; tuple collections are used. Monetary valuation uses Decimal precision 28 and JSON decimal strings. Outputs are revalued by the risk tool, preventing a modified output dictionary from overriding input prices.
- `calculate_portfolio_risk(RiskInput) -> RiskOutput`: explicit validated snapshot, as_of and AssetHistory tuples. Actual market-value weights include CASH. Reports maximum single noncash asset weight, cash fraction, sample annualized volatility, maximum drawdown and pair correlations. Risk history defaults to a maximum age of 604800 seconds, configurable through 31536000. Cash-only has zero volatility/drawdown. One return observation makes sample volatility unavailable and status insufficient_data. Source identifiers, snapshot hash, dates and observation count accompany numeric outputs.
- `validate_allocation(AllocationInput) -> ConstraintCheck`: explicit CASH, nonnegative weights, sum one within tolerance, symbol caps, minimum cash, optional maximum equity and sector caps. Each requested hard check is pass/fail/unknown; fail takes aggregate precedence but unknowns remain visible. Unknown never produces pass. Classifications require an explicit source supplied by trusted application code; arbitrary model-generated classifications must not be accepted as trusted. The tool verifies provenance presence, not provider authenticity. Positive noncash exposure needs all relevant classifications; zero exposure has no classification requirement. Default tolerance 1e-8, configurable 0 through 1e-4. All constraint bounds are in [0,1]. Inputs normalize symbols uppercase; CASH is reserved. All symbol-keyed maps reject case/whitespace alias collisions before Pydantic key normalization, including caps, weights, classifications and simulation targets. Sector labels are trimmed and normalized uppercase, matching the shared W1 contract; sector-cap key collisions are likewise rejected. Classification sector/source and snapshot/quote/history source strings must be nonblank after trimming; optional missing metadata remains None and cannot pass required checks.
- `generate_feasible_candidates(CandidateInput) -> CandidateOutput`: at most 32 symbols, at most eight requested candidates. Tries an all-cash witness and three deterministic greedy allocations using cash cap/minimum and forward/reversed symbol order. Candidates are returned only after every requested check passes. Returns infeasible for cash minimum/cap contradictions or proven simple capacity exhaustion; classification gaps and inconclusive interacting equity/sector bounds return insufficient_data. It never changes constraints and makes no return prediction or optimality claim. Current implementation produces at most four distinct candidates even if eight requested.
- `simulate_allocation(SimulationInput) -> SimulationOutput`: explicit histories, as_of, currency, fixed target weights including CASH, positive initial value, positive rebalance_every measured in common trading observations, explicit nonnegative fee_bps/slippage_bps. Combined costs must be below 10000 bps. Target weights accepted within the 1e-8 sum tolerance are normalized to one before simulation, preventing artificial wealth from rounding. The typed model validates malformed inputs; unusable history or target sum returns insufficient_data. Cash-only paths need an explicit historical calendar (supply any eligible AssetHistory); no calendar is invented.

Direct example:

```python
from agent.tools.allocation import AllocationInput, validate_allocation
check = validate_allocation(AllocationInput(
    weights={"MU": "0.4", "SOXX": "0.4", "CASH": "0.2"},
    constraints={"min_cash_weight": "0.2", "max_weight_by_symbol": {"MU": "0.5"}},
))
assert check.status == "pass"
```

## Date, statistics and simulation policy

Every timestamp must be aware and is normalized to UTC. HistoryBar.date is the UTC close date; exchange_timezone separately records the market timezone. Close/available timestamps must be ordered and no later than as_of. Duplicate symbol/date histories, mixed currencies and mixed adjustment conventions are refused. AssetHistory adjustment is explicitly adjusted or total_return; there is no implicit raw-close fallback. The producer remains responsible for actual adjustment accuracy and availability provenance. Fixtures are synthetic, not real market observations.

Only sorted common dates across positive exposures are used; no forward fill or ordinal alignment. Excluded noncommon dates generate a warning. Risk computes prices' interval returns on those common endpoints, then uses constant **current** portfolio weights (cash earns zero). It compounds those proxy returns for drawdown. This is a historical constant-weight proxy, not a reconstruction of actual historical positions or future expected return. Annualization is sample standard deviation times sqrt(periods_per_year), default 252. When common intervals are irregular, this equal-interval annualization is an approximation; inspect returned dates/warnings and select a suitable frequency rather than interpreting it as a guaranteed daily estimator. Correlation uses sample covariance; constant series or fewer than two returns produce null and a warning. Statistical outputs use binary64, unlike monetary Decimal outputs. High-concentration warning threshold is strictly >0.5; high pair-correlation is strictly >0.8.

Simulation fixes target weights before the first bar. Purchases at the first common close charge initial costs. Interval i returns apply to holdings established at close i-1. At eligible close i, it rebalances for the next interval; no rebalance or liquidation fee is charged at the final close. Cash return is zero, fractional units are allowed, and there are no taxes, financing, liquidity, corporate-action reconstruction or lot constraints. Total-return inputs imply dividend reinvestment within each asset. Fee plus slippage is a linear rate on sum of absolute buy/sell notional, excluding CASH. At each rebalance, a 120-iteration Decimal bisection solves `post_NAV + rate * sum(abs(target_weight * post_NAV - pretrade_asset_value)) = pre_NAV`. This is self-financing and cannot fund fees with hidden additional cash. Costs and turnover are reported per date and in aggregate. Net return includes initial purchase costs. No lookahead enters target selection or holdings, though this is a retrospective simulation requiring ex-ante target selection by its caller. These modules do not use PortfolioBacktest or TradeSimulator.

## Offline verification

`eval/fixtures/portfolio/scenarios.json` contains 27 versioned synthetic scenarios with explicit gold statuses, weight sums, valuation and net-value/risk references. Tests additionally cover hand paths, common-date alignment, fees/slippage, zero volatility, undefined correlation, empty holdings, zero/negative/nonfinite values, missing/late/stale metadata, currencies, forged valuations, strict schemas and unchanged file hashes. A patched forbidden PortfolioStore constructor proves tools never instantiate it. Existing ToolExecutor is exercised with asyncio.run.

From this worktree, use absolute PYTHONPATH to avoid another checkout's `agent` package:

```powershell
$env:PYTHONPATH="C:\Users\RickyMa\.codex\worktrees\financial-mas-quant\Pro_Trading_DS\backend;C:\Users\RickyMa\.codex\worktrees\financial-mas-quant\Pro_Trading_DS\lobster_quant"
python -m pytest backend/tests/test_financial_portfolio_tools.py lobster_quant/tests/unit/test_portfolio_risk.py lobster_quant/tests/unit/test_allocation_simulator.py -q
```

Result on 2026-10-08: 116 passed; pre-existing warning for unavailable pytest-asyncio config option. Full backend regression: 212 passed with Lead support commit 5e0e727 files restored locally (stock-name packaging fix, excluded from W3 feature commit). Initial clean-W0 backend collection had three ModuleNotFoundError errors for the ignored data.stock_name_map module. Full quant regression: 703 passed, one pre-existing warning. No real provider, production holdings, broker, PostgreSQL/Redis or live historical data validation is claimed. Shared registry/contract integration and W5 autonomous workflow remain dependent gates.
