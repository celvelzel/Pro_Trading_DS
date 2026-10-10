"""The demo is synthetic, cutoff-safe and independent of real portfolio files."""
from datetime import timedelta
from agent.financial_demo import (DEMO_AS_OF, DEMO_SNAPSHOT_ID, DEMO_SYMBOLS,
    demo_market_dependencies, demo_snapshot_loader, demo_histories, demo_classifications)
from agent.tools.market_history import MarketHistoryInput, get_market_history
from agent.tools.market_events import EventEvidenceInput, get_event_evidence
from agent.tools.portfolio_snapshot import SnapshotInput, get_portfolio_snapshot
from agent.tools.portfolio_risk import RiskInput, calculate_portfolio_risk
from agent.tools.allocation import AllocationInput, validate_allocation


def test_demo_provenance_and_cutoff():
    market, events = demo_market_dependencies()
    for symbol in DEMO_SYMBOLS:
        history = get_market_history(MarketHistoryInput(symbol=symbol, as_of=DEMO_AS_OF), market)
        assert history.status == "ok"
        assert history.series.provider.startswith("synthetic")
        evidence = get_event_evidence(EventEvidenceInput(symbol=symbol, as_of=DEMO_AS_OF), events)
        assert evidence.excluded_count == 1
        assert all("SYNTHETIC TEST DATA" in e.text and e.available_at <= DEMO_AS_OF for e in evidence.evidence)


def test_demo_is_explicit_and_cannot_substitute_real_snapshot():
    assert demo_snapshot_loader("real-portfolio") is None
    snapshot = get_portfolio_snapshot(SnapshotInput(snapshot_id=DEMO_SNAPSHOT_ID, as_of=DEMO_AS_OF), demo_snapshot_loader)
    assert snapshot.status == "ok" and snapshot.snapshot.snapshot_kind == "demo"
    risk = calculate_portfolio_risk(RiskInput(snapshot=snapshot, as_of=DEMO_AS_OF, histories=demo_histories()))
    assert risk.status == "ok" and risk.observations >= 20
    assert validate_allocation(AllocationInput(weights=risk.weights, classifications=demo_classifications())).status == "pass"
    stale = get_portfolio_snapshot(SnapshotInput(snapshot_id=DEMO_SNAPSHOT_ID, as_of=DEMO_AS_OF+timedelta(days=2)), demo_snapshot_loader)
    assert stale.status == "insufficient_data"
    assert snapshot.content_hash == get_portfolio_snapshot(SnapshotInput(snapshot_id=DEMO_SNAPSHOT_ID, as_of=DEMO_AS_OF), demo_snapshot_loader).content_hash
