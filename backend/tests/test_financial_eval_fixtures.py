"""Deterministic fixture conformance, not workflow/model-quality evaluation."""
import copy
import hashlib
import json
from pydantic import ValidationError
import importlib.util
from decimal import Decimal
from datetime import datetime
from pathlib import Path
import pytest
from agent.tools import portfolio_snapshot as snapshots, portfolio_risk as risk, allocation, anomaly, market_history, market_events

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('financial_fixtures',ROOT/'eval/financial_fixtures.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
M,P=f.load_cases()

def test_manifest_counts_sources_and_identity():
    manifest=f.verify_manifest()
    assert manifest['counts']=={'market':12,'portfolio':30}
    assert [c.case_id for c in M]==[f'M{i:02}' for i in range(1,13)]
    assert [c.case_id for c in P]==[f'P{i:02}' for i in range(1,31)]
    assert manifest['actual_tokens'] is None
    assert all(not c.conformance['actual_workflow_executed'] for c in M+P)

@pytest.mark.parametrize('case',M,ids=lambda c:c.case_id)
def test_market_time_and_numeric_gold(case):
    hd,ed=f.market_dependencies(case)
    out=market_events.get_event_evidence(market_events.EventEvidenceInput(symbol=case.request.symbol,as_of=case.request.as_of),ed)
    assert len(out.evidence)==case.gold['eligible_count']
    assert all(e.published_at<=case.request.as_of and e.available_at<=case.request.as_of for e in out.evidence)
    history=market_history.get_market_history(market_history.MarketHistoryInput(symbol='DEMO',as_of=case.request.as_of),hd)
    assert len(history.series.bars)==21
    for benchmark,excess,relative in [('SECTOR',-5,-1/19),('SPY',-10,-.1)]:
        result=anomaly.calculate_market_anomaly(anomaly.MarketAnomalyInput(symbol='DEMO',benchmark=benchmark,as_of=case.request.as_of),hd)
        assert result.return_pct==pytest.approx(-10,abs=1e-12)
        assert result.volume_ratio_20==3
        assert result.excess_return_pct==pytest.approx(excess,abs=1e-12)
        assert result.relative_strength==pytest.approx(relative,abs=1e-12)

def test_weekday_weekend_pair_and_independent_spy():
    assert M[9].events[0].published_at.weekday()==3
    assert M[10].events[0].published_at.weekday()==5
    assert [e.credibility for e in M[11].events]==['rumor','primary']
    hd,_=f.market_dependencies(M[0])
    spy=market_history.get_market_history(market_history.MarketHistoryInput(symbol='SPY',as_of=M[0].request.as_of),hd).series
    assert all(b.close==100 for b in spy.bars)
    assert 'workflow-v1/history/SPY' in spy.source_locator

@pytest.mark.parametrize('case',P,ids=lambda c:c.case_id)
def test_every_adapter_typed_and_deterministic(case):
    # All 30 requests and dependency records are typed, even malformed proposals.
    ci=case.candidate_input(); ai=case.allocation_input()
    snapshot=snapshots.get_portfolio_snapshot(case.snapshot_input(),lambda _:case.snapshot)
    before=risk.calculate_portfolio_risk(case.risk_input(snapshot))
    check=allocation.validate_allocation(ai)
    candidates=allocation.generate_feasible_candidates(ci)
    assert check.status==case.gold['constraint_status']
    reason=case.gold['reason']
    if reason:
        observed=set(snapshot.reasons)|set(before.reasons)|set(check.violations)|set(check.unknowns)|set(candidates.reasons)
        assert reason in observed
    if case.gold['status']=='infeasible':
        assert candidates.status=='infeasible'
    if case.gold['status']=='feasible':
        assert snapshot.status=='ok' and before.status=='ok' and check.status=='pass'
        assert before.annualized_volatility==pytest.approx(case.gold['before']['annualized_volatility'],abs=1e-12)
        assert before.max_drawdown==pytest.approx(float(case.gold['before']['max_drawdown']),abs=1e-12)
        sim=allocation.simulate_allocation(case.simulation_input(snapshot.total_value))
        assert sim.status=='ok'
        assert [point.net_value for point in sim.path]==pytest.approx([Decimal(v) for v in case.gold['nav']],abs=Decimal('1e-20'))
        assert sim.total_return==pytest.approx(Decimal(case.gold['net_return']),abs=Decimal('1e-20'))
        # Construct a virtual data record using the manual value/quote equation.
        record=case.snapshot.model_dump(mode='python')
        raw=case.proposals[-1]
        prices={q.symbol:q.price for q in case.snapshot.quotes}
        record['holdings']=[dict(symbol=s,quantity=snapshot.total_value*Decimal(w)/prices[s],currency='USD') for s,w in raw.items() if s!='CASH' and Decimal(w)>0]
        record['cash']=snapshot.total_value*Decimal(raw.get('CASH','0'))
        virtual=snapshots.get_portfolio_snapshot(case.snapshot_input(),lambda _:record)
        after=risk.calculate_portfolio_risk(case.risk_input(virtual))
        assert after.status=='ok'
        for key in ('concentration','cash_weight','max_drawdown','annualized_volatility'):
            assert float(getattr(after,key))==pytest.approx(float(case.gold['after'][key]),abs=1e-12)
        assert sim.path[-1].net_value==pytest.approx(Decimal(case.gold['nav'][-1]),abs=Decimal('1e-20'))
    if case.case_id=='P28':
        assert allocation.validate_allocation(case.allocation_input(0)).status=='fail'
        assert allocation.validate_allocation(case.allocation_input(1)).status=='pass'
    if case.case_id=='P29':
        assert tuple(str(d) for d in before.dates)==('2026-10-06','2026-10-07','2026-10-08')
        assert before.correlations['A|B'] is None
        assert 'undefined_correlation:A|B' in before.warnings



def test_source_case_and_adapter_hashes():
    for filename,key in [('market_cases.jsonl','cases'),('portfolio_cases.jsonl','scenarios')]:
        for line in (ROOT/'eval'/filename).read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            adapter={k:v for k,v in row.items() if k not in ('gold','conformance','adapter_sha256')}
            canonical=lambda value:json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode()
            assert hashlib.sha256(canonical(adapter)).hexdigest()==row['adapter_sha256']
            if row['source_file']:
                source=json.loads((ROOT/row['source_file']).read_text())[key]
                identity='case_id' if key=='cases' else 'id'
                original=next(c for c in source if c[identity]==row['source_case_id'])
                assert hashlib.sha256(canonical(original)).hexdigest()==row['source_case_sha256']

def test_negative_proposal_is_check_failure_not_request_rejection():
    assert allocation.validate_allocation(P[2].allocation_input()).status=='fail'
    with pytest.raises(ValidationError):
        P[2].simulation_input(150)
