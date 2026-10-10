# Point-in-time market tools (W2)

The three modules export `register_tools(registry, dependencies)` and do not register at import. Tools are read-only, idempotent and run with the existing ToolExecutor. No model/provider calls or portfolio writes occur.

```python
from agent.tools.registry import ToolRegistry
from agent.tools import market_history, market_events, anomaly

registry = ToolRegistry()
history_dependencies = market_history.MarketDependencies(
    market_history.FixtureHistoryBackend(series_models))
event_dependencies = market_events.EventDependencies(
    market_events.FixtureEventBackend(event_models))
market_history.register_tools(registry, history_dependencies)
anomaly.register_tools(registry, history_dependencies)
market_events.register_tools(registry, event_dependencies)
```

`series_models` is a list of `HistorySeries`; `event_models` is a list of `EventRecord`. Load fixture JSON at `eval/fixtures/market/packs.json` using `model_validate`. This versioned pack contains two synthetic OHLCV series and ten truth-labelled event cases; it is synthetic test evidence, never real news or a verified cause.

Direct APIs: `get_market_history(MarketHistoryInput, MarketDependencies) -> MarketHistoryOutput`; `calculate_market_anomaly(MarketAnomalyInput, MarketDependencies) -> MarketAnomalyOutput`; `get_event_evidence(EventEvidenceInput, EventDependencies) -> EventEvidenceOutput`. Handler names match tool names, version `1`. Anomaly input adds optional `benchmark` to history input. Both use uppercase symbols, aware UTC `as_of`, explicit adjustment (`raw` default), and bounded lookback (anomaly defaults to 21).

History requires provider, locator, currency, exchange/timezone, adjustment and audited `point_in_time_safe=True`. Unknown adjustment or historical suitability returns unavailable. Bars have exchange-local session dates, aware close/availability times, positive finite OHLC and nonnegative volume. Only bars with both times <= as_of appear. Sessions are sorted, duplicates rejected; supplied expected sessions identify gaps/suspensions, which withhold anomaly metrics. Without an explicit calendar, limitations explain that gaps/nontrading days cannot be inferred. A nontrading-day cutoff returns preceding eligible bars; absence of bars/short history is insufficient data.

Optional `DataEngineHistoryBackend(engine, metadata, session_times)` requires per-symbol HistorySeries metadata and a date-to-(close_at, available_at) mapping. It refuses missing mappings and unknown adjustment. `point_in_time_safe` is an audited caller assertion about historical revisions, not a guarantee derived from latest prices. Existing live providers lack this provenance by default; live point-in-time operation is unsupported without a separately audited adapter. No timezone/availability is guessed from a naive frame index.

Anomaly computes latest return in percent (`r_asset * 100`), latest volume divided by mean of twenty *prior* sessions, excess return in percentage points (`(r_asset - r_benchmark) * 100`), and `(1+r_asset)/(1+r_benchmark)-1` relative strength. Persisted Market NumericFact units distinguish `percent` from `percentage_points`; ratio metrics retain their raw values. The benchmark must contain the identical two session dates and compatible currency. No ordinal date substitution or extrapolation occurs. Zero prior volume, missing benchmark, insufficient history and suspensions produce explicit limitations/null metrics. Relative strength is a fraction, not percent. This corrects new artifact labeling; existing immutable historical artifacts are not rewritten.

Event records are manual/fixture or explicitly normalized document records. `normalize_rag_record(dict)` requires the complete EventRecord metadata; existing Retriever chunk fields alone are insufficient and rejected. Both publication and availability must be known and <= as_of. `observed_at` records later retrieval independently and does not authorize historical use. Future/unknown records are counted but their text is not returned. Text hashes and source/timing-based IDs detect tampering; result refs/citations are deterministic for the same inputs. Eligible rumors/injection remain untrusted text with credibility labels, never instructions or causal proof. No historical provider configured returns unavailable; no news is invented.

Validation uses asyncio.run for ToolExecutor, hand-computed numerical tests and repeatability/timing fixture tests. These establish offline behavior only, not real exchange/provider acceptance or real-news causality.

Calendar gaps include trailing expected sessions through the exchange-local cutoff date. Intraday/incomplete sessions conservatively count as missing until their bars become available; this daily tool does not claim an intraday anomaly. Calendar dates after the cutoff are excluded.

Declared suspended sessions in the returned history window are unusable even if a provider supplies a filled OHLCV bar, and even when no expected-session calendar is supplied. They appear in `gaps` and retain suspension metadata, yielding insufficient data. Asset suspensions withhold all anomaly metrics; benchmark suspensions withhold benchmark-relative metrics. Future suspension dates are excluded by the same exchange-local cutoff.
