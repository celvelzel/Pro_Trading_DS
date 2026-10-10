"""Explicit synthetic read-only demo inputs; never reads a user's portfolio.

Prices, events, calendar and classifications are invented test data, not
observations about the named securities. No corporate actions exist in this
synthetic world, so raw and total-return prices coincide by construction.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from agent.tools.market_history import HistoryBar, HistorySeries, FixtureHistoryBackend, MarketDependencies
from agent.tools.market_events import EventRecord, FixtureEventBackend, EventDependencies
from agent.tools.portfolio_snapshot import SnapshotRecord, Holding, ValuationQuote
from agent.tools.portfolio_risk import AssetHistory, HistoryBar as RiskBar
from agent.tools.allocation import AssetClassification

DEMO_AS_OF = datetime(2026, 9, 29, 20, 5, tzinfo=timezone.utc)
DEMO_SNAPSHOT_ID = "synthetic-mu-soxx-v1"
DEMO_SYMBOLS = ("MU", "SOXX", "SPY", "TLT")
DEMO_SOURCE = "synthetic-financial-demo-v1"


def _sessions():
    current = date(2026, 9, 1)
    result = []
    while current <= DEMO_AS_OF.date():
        if current.weekday() < 5:
            result.append(current)
        current += timedelta(days=1)
    return result


def demo_market_dependencies():
    """Fresh isolated input copies, including a future excluded event."""
    sessions = _sessions()
    series = []
    for symbol, final in zip(DEMO_SYMBOLS, (92, 96, 99, 101)):
        bars = []
        for index, day in enumerate(sessions):
            close = float(final if index == len(sessions) - 1 else Decimal(100) + Decimal(index % 3) / 10)
            closed = datetime.combine(day, time(20), timezone.utc)
            bars.append(HistoryBar(session_date=day, close_at=closed,
                available_at=closed + timedelta(minutes=5), open=close, high=close,
                low=close, close=close, volume=3000 if index == len(sessions)-1 else 1000))
        series.append(HistorySeries(symbol=symbol, provider=DEMO_SOURCE,
            source_locator=f"fixture://financial-demo/v1/{symbol}", currency="USD",
            exchange="SYNTHETIC", exchange_timezone="America/New_York",
            adjustment="raw", point_in_time_safe=True, bars=bars,
            expected_sessions=sessions))
    events = []
    for symbol in DEMO_SYMBOLS:
        events.append(EventRecord(symbol=symbol, source_type="document",
            source_locator=f"fixture://financial-demo/v1/{symbol}/sector",
            published_at=DEMO_AS_OF-timedelta(hours=1), available_at=DEMO_AS_OF-timedelta(minutes=50),
            observed_at=DEMO_AS_OF, credibility="primary",
            text="SYNTHETIC TEST DATA: a sector-wide repricing hypothesis is reported; no company-specific causal conclusion is established."))
        events.append(EventRecord(symbol=symbol, source_type="document",
            source_locator=f"fixture://financial-demo/v1/{symbol}/future",
            published_at=DEMO_AS_OF+timedelta(hours=1), available_at=DEMO_AS_OF+timedelta(hours=1),
            observed_at=DEMO_AS_OF+timedelta(hours=2), credibility="primary",
            text="SYNTHETIC FUTURE EVENT: this text must not enter historical reasoning."))
    return MarketDependencies(FixtureHistoryBackend(series)), EventDependencies(FixtureEventBackend(events))


def demo_snapshot_loader(snapshot_id):
    if snapshot_id != DEMO_SNAPSHOT_ID:
        return None
    return SnapshotRecord(snapshot_id=DEMO_SNAPSHOT_ID, source=DEMO_SOURCE,
        effective_at=DEMO_AS_OF, snapshot_kind="demo", currency="USD", cash=Decimal(20000),
        holdings=tuple(Holding(symbol=s, quantity=q, currency="USD", sector=sector,
            classification_source=DEMO_SOURCE) for s,q,sector in
            (("MU",Decimal(400),"TECH"),("SOXX",Decimal(200),"TECH"),("SPY",Decimal(100),"BROAD"),("TLT",Decimal(100),"BOND"))),
        quotes=tuple(ValuationQuote(symbol=s, price=Decimal(p), currency="USD",
            effective_at=DEMO_AS_OF-timedelta(minutes=5), available_at=DEMO_AS_OF,
            source=DEMO_SOURCE) for s,p in zip(DEMO_SYMBOLS,(92,96,99,101))))


def demo_histories():
    market, _ = demo_market_dependencies()
    return tuple(AssetHistory(symbol=s, currency="USD", source=DEMO_SOURCE,
        adjustment="total_return", exchange_timezone="America/New_York",
        bars=tuple(RiskBar(date=b.session_date, price=Decimal(str(b.close)),
            close_at=b.close_at, available_at=b.available_at)
            for b in market.history_backend.load(s).bars)) for s in DEMO_SYMBOLS)


def demo_classifications():
    return {s: AssetClassification(asset_class="other" if s=="TLT" else "equity",
        sector=sector, source=DEMO_SOURCE) for s,sector in
        zip(DEMO_SYMBOLS,("TECH","TECH","BROAD","BOND"))}

