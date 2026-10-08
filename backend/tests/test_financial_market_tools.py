import asyncio
import json
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

import pytest
from pydantic import ValidationError
from agent.tools.registry import ToolRegistry
from agent.tools.executor import ToolExecutor
from agent.tools import market_history as history, market_events as events, anomaly

PACK = json.loads((Path(__file__).resolve().parents[2] / "eval/fixtures/market/packs.json").read_text())


def dependencies():
    return history.MarketDependencies(history.FixtureHistoryBackend([history.HistorySeries.model_validate(s) for s in PACK["series"]]))


def test_history_no_future_sorted_repeatable():
    request = history.MarketHistoryInput(symbol="demo", as_of=PACK["cases"][0]["as_of"])
    first = history.get_market_history(request, dependencies())
    assert first == history.get_market_history(request, dependencies())
    assert len(first.series.bars) == 21
    assert all(b.available_at <= request.as_of and b.close_at <= request.as_of for b in first.series.bars)
    assert first.series.bars[-1].close == 90


@pytest.mark.parametrize("case", PACK["cases"], ids=lambda c: c["case_id"])
def test_truth_labelled_evidence_cutoff(case):
    deps = events.EventDependencies(events.FixtureEventBackend([events.EventRecord.model_validate(e) for e in case["events"]]))
    req = events.EventEvidenceInput(symbol=case["symbol"], as_of=case["as_of"])
    result = events.get_event_evidence(req, deps)
    assert len(result.evidence) == case["truth"]["eligible_count"]
    assert result == events.get_event_evidence(req, deps)
    if not result.evidence:
        assert all(e["text"] not in result.model_dump_json() for e in case["events"])
    assert all(e.content_hash and e.source_locator for e in result.evidence)


def test_registered_tools_executor_and_numbers():
    registry = ToolRegistry()
    history.register_tools(registry, dependencies())
    anomaly.register_tools(registry, dependencies())
    events.register_tools(registry, events.EventDependencies())
    assert all(s.read_only and not s.side_effect and s.idempotent for s in registry.list())
    result = asyncio.run(ToolExecutor(registry).execute("calculate_market_anomaly", {"symbol": "DEMO", "benchmark": "SECTOR", "as_of": PACK["cases"][0]["as_of"]}))
    assert result.status.value == "succeeded"
    assert result.data["return_pct"] == pytest.approx(-10)
    assert result.data["volume_ratio_20"] == 3
    assert result.data["excess_return_pct"] == pytest.approx(-5)
    assert result.citations


def test_unknown_adjustment_and_unsafe_provider_unavailable():
    original = history.HistorySeries.model_validate(PACK["series"][0])
    for updates in ({"adjustment": "unknown"}, {"point_in_time_safe": False}):
        deps = history.MarketDependencies(history.FixtureHistoryBackend([original.model_copy(update=updates)]))
        assert history.get_market_history(history.MarketHistoryInput(symbol="DEMO", as_of=PACK["cases"][0]["as_of"]), deps).status == "unavailable"


def test_delayed_bar_gap_and_suspension_withhold_metrics():
    series = history.HistorySeries.model_validate(PACK["series"][0])
    missing = series.bars[10].session_date
    series.bars.pop(10)
    series.suspended_sessions = [missing]
    deps = history.MarketDependencies(history.FixtureHistoryBackend([series]))
    req = anomaly.MarketAnomalyInput(symbol="DEMO", as_of=PACK["cases"][0]["as_of"])
    result = anomaly.calculate_market_anomaly(req, deps)
    assert result.status == "insufficient_data"
    assert result.return_pct is None


def test_trailing_suspension_is_not_silently_a_current_return():
    series = history.HistorySeries.model_validate(PACK["series"][0])
    missing = series.bars[20].session_date
    series.bars.pop(20)
    series.suspended_sessions = [missing]
    deps = history.MarketDependencies(history.FixtureHistoryBackend([series]))
    req = anomaly.MarketAnomalyInput(symbol="DEMO", as_of=PACK["cases"][0]["as_of"])
    assert anomaly.calculate_market_anomaly(req, deps).return_pct is None


@pytest.mark.parametrize("has_calendar", [True, False])
@pytest.mark.parametrize("suspended_symbol", ["DEMO", "SECTOR"])
def test_filled_suspension_overrides_bar_with_or_without_calendar(has_calendar, suspended_symbol):
    series = [history.HistorySeries.model_validate(s) for s in PACK["series"]]
    suspended = next(s for s in series if s.symbol == suspended_symbol)
    bar = suspended.bars[20]
    for field in ("open", "high", "low", "close"):
        setattr(bar, field, 100.)
    bar.volume = 0.
    suspended.suspended_sessions = [bar.session_date]
    if not has_calendar:
        suspended.expected_sessions = []
    deps = history.MarketDependencies(history.FixtureHistoryBackend(series))
    cutoff = PACK["cases"][0]["as_of"]
    output = history.get_market_history(history.MarketHistoryInput(symbol=suspended_symbol, as_of=cutoff), deps)
    assert output.status == "insufficient_data"
    assert bar.session_date in output.gaps
    assert output.series.suspended_sessions == [bar.session_date]
    result = anomaly.calculate_market_anomaly(anomaly.MarketAnomalyInput(symbol="DEMO", benchmark="SECTOR", as_of=cutoff), deps)
    assert result.status == "insufficient_data"
    assert result.excess_return_pct is None
    assert result.relative_strength is None
    if suspended_symbol == "DEMO":
        assert result.return_pct is None
        assert result.volume_ratio_20 is None
    else:
        assert result.return_pct == pytest.approx(-10)
        assert result.volume_ratio_20 == 3


def test_future_suspension_does_not_affect_historical_metrics():
    series = history.HistorySeries.model_validate(PACK["series"][0])
    series.suspended_sessions = [series.bars[21].session_date]
    deps = history.MarketDependencies(history.FixtureHistoryBackend([series]))
    req = history.MarketHistoryInput(symbol="DEMO", as_of=PACK["cases"][0]["as_of"])
    output = history.get_market_history(req, deps)
    assert output.status == "ok"
    assert output.series.suspended_sessions == []
    assert output.gaps == []


def test_bar_not_yet_available_and_nontrading_cutoff():
    req = history.MarketHistoryInput(symbol="DEMO", as_of=PACK["cases"][0]["as_of"])
    before_availability = req.model_copy(update={"as_of": req.as_of - timedelta(minutes=8)})
    assert len(history.get_market_history(before_availability, dependencies()).series.bars) == 20
    # September 26 is Saturday; Friday September 25 is the last eligible close.
    weekend = history.MarketHistoryInput(symbol="DEMO", as_of=datetime(2026, 9, 26, 22, tzinfo=timezone.utc), lookback=2)
    output = history.get_market_history(weekend, dependencies())
    assert weekend.as_of.weekday() == 5
    assert output.status == "ok"
    assert output.gaps == []
    assert output.series.bars[-1].session_date == date(2026, 9, 25)
    assert output.data_last_bar_at == datetime(2026, 9, 25, 20, tzinfo=timezone.utc)
    assert all(b.close_at <= weekend.as_of and b.available_at <= weekend.as_of for b in output.series.bars)


def test_strict_inputs_and_rag_unknown_metadata():
    with pytest.raises(ValidationError):
        history.MarketHistoryInput(symbol="DEMO", as_of="2026-09-01T00:00:00")
    with pytest.raises(ValidationError):
        history.MarketHistoryInput(symbol="DEMO", as_of=PACK["cases"][0]["as_of"], injected="bad")
    with pytest.raises(ValidationError):
        events.normalize_rag_record({"chunk_id": "current", "text": "Undated retrieved text"})


def test_injection_remains_text_and_missing_backend():
    case = next(c for c in PACK["cases"] if c["case_id"] == "injection")
    record = events.EventRecord.model_validate(case["events"][0])
    assert "modify holdings" in record.text
    assert events.get_event_evidence(events.EventEvidenceInput(symbol="DEMO", as_of=case["as_of"]), events.EventDependencies()).status == "unavailable"


def test_hash_tampering_and_invalid_prices_rejected():
    event = PACK["cases"][0]["events"][0]
    with pytest.raises(ValidationError):
        events.EventRecord.model_validate({**event, "content_hash": "wrong"})
    bar = PACK["series"][0]["bars"][0]
    with pytest.raises(ValidationError):
        history.HistoryBar.model_validate({**bar, "close": float("nan")})
