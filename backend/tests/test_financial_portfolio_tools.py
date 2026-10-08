from __future__ import annotations
import asyncio
import copy
import hashlib
import json
from pathlib import Path
from decimal import Decimal
import pytest
from pydantic import ValidationError
from agent.tools import portfolio_snapshot as snapshots, portfolio_risk as risk, allocation
from agent.tools.registry import ToolRegistry, default_registry
from agent.tools.executor import ToolExecutor

FIXTURE=Path(__file__).resolve().parents[2]/'eval/fixtures/portfolio/scenarios.json'
CASES=json.loads(FIXTURE.read_text(encoding='utf-8'))['scenarios']
BASE=next(c['input'] for c in CASES if c['id']=='snapshot_ok')['snapshot']
ASOF='2026-10-08T20:00:00Z'
HISTORY=next(c['input'] for c in CASES if c['id']=='simulation_half')['histories'][0]


def snapshot(record=None):
    return snapshots.get_portfolio_snapshot(snapshots.SnapshotInput(snapshot_id='demo-1',as_of=ASOF),lambda _:record or BASE)


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['kind']+':'+c['id'])
def test_fixture_gold(case):
    inp,gold=case['input'],case['gold']
    kind=case['kind']
    if kind=='constraint':
        output=allocation.validate_allocation(allocation.AllocationInput.model_validate(inp))
        assert sum((Decimal(v) for v in inp['weights'].values()),Decimal(0))==Decimal(gold['weight_sum'])
    elif kind=='candidate': output=allocation.generate_feasible_candidates(allocation.CandidateInput.model_validate(inp))
    elif kind=='snapshot':
        output=snapshot(inp['snapshot'])
        if 'total_value' in gold:
            assert output.total_value==Decimal(gold['total_value'])
            assert output.market_values=={k:Decimal(v) for k,v in gold['market_values'].items()}
    elif kind=='simulation':
        output=allocation.simulate_allocation(allocation.SimulationInput.model_validate(inp))
        assert float(output.path[-1].net_value)==pytest.approx(float(gold['final_value']))
    else:
        output=risk.calculate_portfolio_risk(risk.RiskInput(snapshot=snapshot(inp['snapshot']),as_of=inp['as_of'],histories=inp['histories']))
        if 'cash_weight' in gold:
            assert output.cash_weight==Decimal(gold['cash_weight'])
            assert output.concentration==Decimal(gold['concentration'])
            assert output.max_drawdown==pytest.approx(gold['max_drawdown'])
    assert output.status==gold['status']
    if kind=='candidate' and output.status=='feasible':
        assert all(c.constraint_check.status=='pass' for c in output.candidates)
        assert len(output.candidates)<=inp.get('max_candidates',3)


def test_readonly_file_hash_and_no_ctor(tmp_path,monkeypatch):
    from lobster_quant.src.storage.portfolio_store import PortfolioStore
    def forbidden(*a,**k): raise AssertionError('PortfolioStore constructor called')
    monkeypatch.setattr(PortfolioStore,'__init__',forbidden)
    file=tmp_path/'snapshot.json';file.write_text(json.dumps(BASE),encoding='utf-8')
    before=hashlib.sha256(file.read_bytes()).hexdigest()
    loader=lambda _:json.loads(file.read_text(encoding='utf-8'))
    s=snapshots.get_portfolio_snapshot(snapshots.SnapshotInput(snapshot_id='demo-1',as_of=ASOF),loader)
    result=risk.calculate_portfolio_risk(risk.RiskInput(snapshot=s,as_of=ASOF,histories=[HISTORY]))
    sim=allocation.simulate_allocation(allocation.SimulationInput(histories=[HISTORY],as_of=ASOF,currency='USD',target_weights={'A':'.5','CASH':'.5'},initial_value=100))
    assert result.status==sim.status=='ok'
    assert hashlib.sha256(file.read_bytes()).hexdigest()==before
    assert list(tmp_path.iterdir())==[file]
    assert s.content_hash==snapshot().content_hash


def test_history_cannot_use_latest_holdings_for_old_asof():
    output=snapshots.get_portfolio_snapshot(snapshots.SnapshotInput(snapshot_id='demo-1',as_of='2026-10-07T20:00:00Z'),lambda _:BASE)
    assert output.status=='insufficient_data'
    assert 'snapshot_future_or_stale' in output.reasons


@pytest.mark.parametrize('field',['cash','currency','effective_at','source'])
def test_explicit_metadata_required(field):
    record=copy.deepcopy(BASE);record[field]=None
    assert snapshot(record).status=='insufficient_data'


def test_snapshot_missing_is_not_default_cash():
    output=snapshots.get_portfolio_snapshot(snapshots.SnapshotInput(snapshot_id='missing',as_of=ASOF),lambda _:None)
    assert output.status=='insufficient_data' and output.total_value is None


@pytest.mark.parametrize('value',['NaN','Infinity','-1'])
def test_invalid_money(value):
    record=copy.deepcopy(BASE);record['cash']=value
    with pytest.raises(ValidationError): snapshot(record)


def test_naive_datetime_extra_fields_and_negative_quote_rejected():
    with pytest.raises(ValidationError): snapshots.SnapshotInput(snapshot_id='x',as_of='2026-10-08T20:00:00')
    with pytest.raises(ValidationError): allocation.AllocationInput(weights={'CASH':1},write=True)
    record=copy.deepcopy(BASE);record['quotes'][0]['price']='0'
    with pytest.raises(ValidationError): snapshot(record)


def test_empty_cash_and_zero_portfolio():
    record=copy.deepcopy(BASE);record.update(holdings=[],quotes=[],cash=100)
    output=snapshot(record)
    assert output.total_value==100
    r=risk.calculate_portfolio_risk(risk.RiskInput(snapshot=output,as_of=ASOF))
    assert r.status=='ok' and r.weights=={'CASH':Decimal(1)}
    record['cash']=0
    assert snapshot(record).status=='insufficient_data'


def test_forged_values_are_recomputed():
    valued=snapshot().model_copy(update={'market_values':{'A':Decimal(99999)},'total_value':Decimal(100049)})
    r=risk.calculate_portfolio_risk(risk.RiskInput(snapshot=valued,as_of=ASOF,histories=[HISTORY]))
    assert r.total_value==150 and r.weights['CASH']==Decimal(1)/3


@pytest.mark.parametrize('mutation,reason',[
 (lambda h:h.update(currency='EUR'),'mixed_history_currencies'),
 (lambda h:h['bars'][-1].update(available_at='2026-10-09T20:00:00Z'),'future_history_bar'),
 (lambda h:h['bars'].pop(),'stale_history:A'),
])
def test_history_safety(mutation,reason):
    h=copy.deepcopy(HISTORY);mutation(h)
    kwargs={'max_history_age_seconds':0} if reason.startswith('stale') else {}
    r=risk.calculate_portfolio_risk(risk.RiskInput(snapshot=snapshot(),as_of=ASOF,histories=[h],**kwargs))
    assert r.status=='insufficient_data' and reason in r.reasons


def test_classified_sector_and_equity_checks():
    classes={'A':{'asset_class':'equity','sector':'tech','source':'fixture:sector/v1'}}
    r=allocation.validate_allocation(allocation.AllocationInput(weights={'A':'.8','CASH':'.2'},constraints={'max_equity_weight':'.7','max_sector_weight':{'tech':'.5'}},classifications=classes))
    assert r.status=='fail' and set(r.violations)=={'max_equity','max_sector:tech'}
    assert not r.unknowns


def test_unknown_hard_check_never_produces_feasible_candidate():
    r=allocation.generate_feasible_candidates(allocation.CandidateInput(symbols=['A'],constraints={'max_weight_by_symbol':{'CASH':'.2'},'max_sector_weight':{'tech':'.5'}}))
    assert r.status=='insufficient_data' and not r.candidates


def test_bounded_candidates_preserve_constraints():
    c=allocation.AllocationConstraints(min_cash_weight='.1',max_weight_by_symbol={'A':'.4','B':'.6','CASH':'.2'})
    r=allocation.generate_feasible_candidates(allocation.CandidateInput(symbols=['A','B'],constraints=c,max_candidates=1))
    assert r.status=='feasible' and len(r.candidates)==1
    assert c.min_cash_weight==Decimal('.1') and r.candidates[0].weights['CASH']<=Decimal('.2')


def test_tool_registry_execution_and_general_unchanged():
    old=default_registry.schemas()
    registry=ToolRegistry()
    snapshots.register_tools(registry,{'snapshot_loader':lambda _:BASE})
    risk.register_tools(registry)
    allocation.register_tools(registry)
    assert len(registry.list())==5
    assert all(t.read_only and not t.side_effect for t in registry.list())
    envelope=asyncio.run(ToolExecutor(registry).execute('get_portfolio_snapshot',{'snapshot_id':'demo-1','as_of':ASOF}))
    assert envelope.status.value=='succeeded' and envelope.data['status']=='ok'
    envelope=asyncio.run(ToolExecutor(registry).execute('validate_allocation',{'weights':{'CASH':1}}))
    assert envelope.status.value=='succeeded' and envelope.data['status']=='pass'
    assert default_registry.schemas()==old


def test_missing_quote_price_is_insufficient_data():
    record=copy.deepcopy(BASE);record['quotes'][0].pop('price')
    assert snapshot(record).status=='insufficient_data'


def test_mixed_adjustment_and_duplicate_history_refused():
    h=copy.deepcopy(HISTORY);h['symbol']='B';h['adjustment']='adjusted'
    r=allocation.simulate_allocation(allocation.SimulationInput(histories=[HISTORY,h],as_of=ASOF,currency='USD',target_weights={'A':'.5','B':'.5','CASH':0},initial_value=100))
    assert r.status=='insufficient_data' and 'mixed_adjustment_conventions' in r.reasons
    r=risk.calculate_portfolio_risk(risk.RiskInput(snapshot=snapshot(),as_of=ASOF,histories=[HISTORY,HISTORY]))
    assert r.status=='insufficient_data' and 'duplicate_history_symbol' in r.reasons


def test_nonfinite_weights_and_constraints_rejected():
    with pytest.raises(ValidationError): allocation.AllocationInput(weights={'CASH':'NaN'})
    with pytest.raises(ValidationError): allocation.AllocationConstraints(min_cash_weight='Infinity')


def test_quote_unknown_date_and_duplicate_holding_rejected():
    record=copy.deepcopy(BASE);record['quotes'][0]['effective_at']=None
    assert snapshot(record).status=='insufficient_data'
    record=copy.deepcopy(BASE);record['holdings']*=2
    with pytest.raises(ValidationError): snapshot(record)
