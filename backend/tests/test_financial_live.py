"""Live assembly conformance with injected data/model, no network or user data."""
import asyncio
import json
import uuid
from decimal import Decimal
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from agent import financial_live as live
from agent.financial_config import model_config, FinancialRoleModel
from agent.financial_constraints import parse_rules, parse_constraints
from agent.financial_demo import (DEMO_AS_OF, DEMO_SYMBOLS, demo_snapshot_loader,
    DEMO_SNAPSHOT_ID, demo_market_dependencies, demo_histories, demo_classifications)
from agent.market_mas import SyntheticMarketModel
from agent.portfolio_mas import SyntheticPortfolioModel
from agent.llm import ScriptedFakeModel
from agent.tools.portfolio_risk import RiskInput, calculate_portfolio_risk
from agent.tools.portfolio_snapshot import SnapshotInput, get_portfolio_snapshot
from api.routes import financial
from db.base import Base
from db.models import Conversation, AgentRun, FinancialDataset
from workers import agent_tasks


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv('FINANCIAL_CONFIG_PATH',str(tmp_path/'absent.json'))
    monkeypatch.setenv('FINANCIAL_AI_BASE_URL','https://example.test/v1')
    monkeypatch.setenv('FINANCIAL_AI_MODEL','fixture-model')
    monkeypatch.setenv('FINANCIAL_AI_API_KEY','private-test-key')
    monkeypatch.delenv('REDIS_URL',raising=False)
    return model_config()


def fixture_data(workflow='combined'):
    market, events = demo_market_dependencies()
    identifier = str(uuid.uuid4())
    snapshot = demo_snapshot_loader(DEMO_SNAPSHOT_ID).model_copy(update={'snapshot_id':'user-'+identifier,'snapshot_kind':'saved'})
    return live.CapturedInputs(dataset_id=identifier,conversation_id='c',as_of=DEMO_AS_OF,
        model_identity=model_config().identity(),workflow=workflow,
        market_symbol='MU' if workflow!='portfolio' else None,
        sector_benchmark='SOXX' if workflow!='portfolio' else None,
        snapshot=snapshot if workflow!='market' else None,
        market_histories=[market.history_backend.load(s) for s in DEMO_SYMBOLS],
        risk_histories=list(demo_histories()), events=[e for s in DEMO_SYMBOLS for e in events.event_backend.load(s)],
        classifications=demo_classifications(),limitations=['Injected fixture only; no live provider evidence.'])


class FixtureRole:
    def __init__(self,config,role): self.role=role
    async def complete(self,messages,*,request_id=None):
        task,_=json.JSONDecoder().raw_decode(messages[-1]['content'].split('<task_data>')[-1])
        provider = SyntheticPortfolioModel(self.role) if 'request' in task else SyntheticMarketModel(self.role)
        return await provider.complete(messages,request_id=request_id)


@pytest.fixture
def api(tmp_path,monkeypatch,configured):
    engine=create_engine('sqlite:///'+str(tmp_path/'live.db'),connect_args={'check_same_thread':False})
    sessions=sessionmaker(engine,expire_on_commit=False)
    Base.metadata.create_all(engine)
    with sessions() as s: s.add(Conversation(id='c')); s.add(Conversation(id='other')); s.commit()
    monkeypatch.setattr(financial,'sync_session_factory',sessions)
    monkeypatch.setattr(agent_tasks,'sync_session_factory',sessions)
    monkeypatch.setattr(live,'FinancialRoleModel',FixtureRole)
    monkeypatch.setattr(live.YahooCapture,'fetch',lambda *args:pytest.fail('Worker must not refresh captured inputs'))
    app=FastAPI(); app.include_router(financial.router,prefix='/api/financial')
    with TestClient(app) as client: yield client,sessions
    engine.dispose()


def request(data,mode='auto'):
    result={'conversation_id':'c','idempotency_key':'live-'+data.dataset_id,'mode':mode,'dataset_id':data.dataset_id}
    if data.market_symbol:
        result['market']={'symbol':data.market_symbol,'sector_benchmark':data.sector_benchmark,'as_of':data.as_of.isoformat()}
    if data.snapshot:
        result['portfolio']={'portfolio_snapshot_id':data.snapshot.snapshot_id,'as_of':data.as_of.isoformat(),
            'user_constraints':{'min_cash_weight':.2,'max_weight_by_symbol':{'MU':.25,'CASH':.3}}}
    return result


@pytest.mark.parametrize('workflow',['market','portfolio','combined'])
def test_live_workers_reconstruct_captured_inputs_and_keep_real_source(api,workflow):
    client,sessions=api; data=fixture_data(workflow); live.save_dataset(sessions,data)
    endpoint={'market':'market-investigations','portfolio':'portfolio-reviews','combined':'combined-reviews'}[workflow]
    created=client.post('/api/financial/'+endpoint,json=request(data))
    assert created.status_code==202,created.text
    ids=[r['run_id'] for r in created.json()['runs']]
    assert len(set(ids))==(2 if workflow=='combined' else 1)
    for rid in ids:
        r=client.get('/api/financial/runs/'+rid).json()
        assert r['status']=='completed',r
        assert r['data_source']=='user'
        assert 'private-test-key' not in json.dumps(r)
        if r['mas_kind']=='portfolio_rebalance':
            assert r['validation_outcome']=='feasible',r
            assert r['artifact']['proposed_weights']['CASH']<=.3
    duplicate=client.post('/api/financial/'+endpoint,json=request(data))
    assert [r['run_id'] for r in duplicate.json()['runs']]==ids


def test_live_review_order_and_results_survive_configuration_loss(api,monkeypatch):
    client,sessions=api; data=fixture_data(); live.save_dataset(sessions,data)
    response=client.post('/api/financial/combined-reviews',json=request(data,'review')).json()
    mid,pid=response['market_run_id'],response['portfolio_run_id']
    market=client.get('/api/financial/runs/'+mid).json()
    portfolio=client.get('/api/financial/runs/'+pid).json()
    assert market['status']==portfolio['status']=='waiting_user'
    assert client.post('/api/financial/runs/'+pid+'/approve',json={'expected_version':portfolio['version']}).status_code==409
    assert client.post('/api/financial/runs/'+mid+'/approve',json={'expected_version':market['version']}).status_code==200
    portfolio=client.get('/api/financial/runs/'+pid).json()
    assert client.post('/api/financial/runs/'+pid+'/approve',json={'expected_version':portfolio['version']}).status_code==200
    assert client.get('/api/financial/runs/'+pid).json()['status']=='completed'
    # Completed results remain readable when the API key is removed.
    monkeypatch.setenv('FINANCIAL_AI_API_KEY','')
    assert client.get('/api/financial/runs/'+pid).status_code==200


def test_live_cancellation_and_worker_failure_are_terminal_without_model_config(api,monkeypatch):
    client,sessions=api; data=fixture_data(); live.save_dataset(sessions,data)
    response=client.post('/api/financial/combined-reviews',json=request(data,'review')).json()
    mid,pid=response['market_run_id'],response['portfolio_run_id']
    market=client.get('/api/financial/runs/'+mid).json()
    monkeypatch.setenv('FINANCIAL_AI_API_KEY','')
    assert client.post('/api/financial/runs/'+mid+'/cancel',json={'expected_version':market['version']}).status_code==200
    assert client.get('/api/financial/runs/'+mid).json()['status']=='cancelled'
    portfolio=client.get('/api/financial/runs/'+pid).json()
    assert portfolio['status']=='waiting_user'
    # An approval after loss fails safely through the persisted runtime, never a demo fallback.
    assert client.post('/api/financial/runs/'+pid+'/approve',json={'expected_version':portfolio['version']}).status_code==200
    final=client.get('/api/financial/runs/'+pid).json()
    assert final['status']=='failed' and final['error_code']=='financial_provider_unavailable'


@pytest.mark.parametrize('change',['conversation','symbol','as_of','snapshot','workflow','model'])
def test_live_preflight_rejects_foreign_or_changed_inputs_without_runs(api,monkeypatch,change):
    client,sessions=api; data=fixture_data(); live.save_dataset(sessions,data); body=request(data)
    if change=='conversation': body['conversation_id']='other'
    if change=='symbol': body['market']['symbol']='SPY'
    if change=='as_of': body['market']['as_of']='2026-09-30T20:05:00Z'; body['portfolio']['as_of']=body['market']['as_of']
    if change=='snapshot': body['portfolio']['portfolio_snapshot_id']='user-forged'
    if change=='workflow': data=fixture_data('portfolio'); live.save_dataset(sessions,data); body['dataset_id']=data.dataset_id
    if change=='model': monkeypatch.setenv('FINANCIAL_AI_MODEL','another-model')
    result=client.post('/api/financial/combined-reviews',json=body)
    assert result.status_code in {404,422,503},result.text
    with sessions() as s: assert s.scalar(select(func.count()).select_from(AgentRun))==0


def test_dataset_hash_detects_mutation(api):
    _,sessions=api; data=fixture_data(); live.save_dataset(sessions,data)
    with sessions() as s:
        row=s.get(FinancialDataset,data.dataset_id); row.payload={**row.payload,'workflow':'market'}; s.commit()
    with pytest.raises(ValueError,match='校验失败'): live.load_dataset(sessions,data.dataset_id)


def test_strict_holdings_requires_actual_cash_and_preserves_files(tmp_path):
    positions=tmp_path/'positions.json'; positions.write_text(json.dumps([{'symbol':'MU','shares':10,'cost_basis':1}]))
    with pytest.raises(ValueError,match='实际现金'): live.read_holdings(tmp_path)
    cash=tmp_path/'cash.json'; cash.write_text('{"balance": 2000}')
    before=positions.read_bytes(),cash.read_bytes()
    holdings,balance=live.read_holdings(tmp_path)
    assert balance==Decimal(2000) and holdings[0].quantity==10
    assert before==(positions.read_bytes(),cash.read_bytes())
    assert 'cost_basis' not in holdings[0].model_dump()


@pytest.mark.parametrize('positions,cash',[
    ([{'symbol':'0700.HK','shares':10}],{'balance':2000}),
    ([{'symbol':'MU','shares':-10}],{'balance':2000}),
    ([{'symbol':'MU','shares':10},{'symbol':'MU','shares':10}],{'balance':2000}),
    ([{'symbol':'MU','shares':10}],{'balance':-1}),
    ([{'symbol':'MU','shares':10}],{'balance':2000,'currency':'HKD'}),
])
def test_strict_holdings_refuses_invalid_or_mixed_inputs(tmp_path,positions,cash):
    (tmp_path/'positions.json').write_text(json.dumps(positions)); (tmp_path/'cash.json').write_text(json.dumps(cash))
    with pytest.raises(ValueError):live.read_holdings(tmp_path)


@pytest.mark.parametrize('text,expected',[
    ('MU不超过25%，现金至少20%',{'MU':.25}),
    ('现金20%–30%，股票总仓位最多70%',{'CASH':.3}),
    ('现金固定20%',{'CASH':.2}),
    ('MU最多30%；MU最多20%',{'MU':.2}),
])
def test_rule_parser_preserves_ratios_and_requires_confirmation(text,expected):
    draft=parse_rules(text,['MU','SOXX'])
    assert draft.constraints.max_weight_by_symbol==expected
    assert draft.requires_confirmation and not draft.unresolved


@pytest.mark.parametrize('text',['稳健一点','股票至少50%','AAPL最多20%','现金至少50%，现金最多30%','MU最多120%',''])
def test_unresolved_or_contradictory_language_cannot_be_silently_applied(text):
    assert parse_rules(text,['MU']).unresolved


def test_llm_parser_cannot_omit_vague_clause_or_disable_confirmation(configured,monkeypatch):
    from agent.financial_config import FinancialModelConfig
    fake=ScriptedFakeModel([{'kind':'result','payload':{'constraints':{'min_cash_weight':.2},
        'recognized':['现金至少20%'],'unresolved':[],'requires_confirmation':False}}])
    monkeypatch.setattr(FinancialModelConfig,'provider',lambda self:fake)
    draft=asyncio.run(parse_constraints('现金至少20%，稳健一点',['MU'],[],True))
    assert draft.requires_confirmation and any('稳健一点' in s for s in draft.unresolved)


def test_real_role_adapter_supplies_schema_without_leaking_key(configured):
    role=FinancialRoleModel(configured,'risk')
    fake=ScriptedFakeModel([{'kind':'result','payload':{'role':'risk','action':'finding','summary':'ok'}}]);role.inner=fake
    asyncio.run(role.complete([{'role':'system','content':'Risk.'},{'role':'user','content':'{}'}]))
    assert 'proposed_weights' in fake.calls[0][0]['content']
    assert 'private-test-key' not in json.dumps(fake.calls)


def test_risk_quote_age_is_explicit_and_legacy_serialization_unchanged():
    snap=demo_snapshot_loader(DEMO_SNAPSHOT_ID)
    from datetime import timedelta
    stale=snap.model_copy(update={'effective_at':DEMO_AS_OF,'quotes':tuple(q.model_copy(update={
        'effective_at':DEMO_AS_OF-timedelta(days=2),'available_at':DEMO_AS_OF}) for q in snap.quotes)})
    valued=get_portfolio_snapshot(SnapshotInput(snapshot_id=snap.snapshot_id,as_of=DEMO_AS_OF,max_age_seconds=604800),lambda _:stale)
    default=RiskInput(snapshot=valued,as_of=DEMO_AS_OF,histories=demo_histories())
    assert 'max_quote_age_seconds' not in default.model_dump()
    assert calculate_portfolio_risk(default).status=='insufficient_data'
    explicit=default.model_copy(update={'max_quote_age_seconds':604800})
    assert calculate_portfolio_risk(explicit).status=='ok'


def test_connection_status_does_not_expose_secret_or_assume_connectivity(api):
    client,_=api; response=client.get('/api/financial/connection')
    assert response.json()['configured']
    assert 'private-test-key' not in response.text and 'api_key' not in response.text


def test_prepare_uses_saved_server_dataset_and_returns_preview(api,monkeypatch):
    client,sessions=api
    monkeypatch.setattr(live,'capture_inputs',lambda *args:fixture_data())
    response=client.post('/api/financial/live/prepare',json={'conversation_id':'c','workflow':'combined','symbol':'MU'})
    assert response.status_code==200,response.text
    preview=response.json()
    assert preview['cash']=='20000' and preview['holdings'][0]['price']=='92'
    assert live.load_dataset(sessions,preview['dataset_id'],'c').workflow=='combined'


@pytest.mark.parametrize('workflow,kind,absent',[
    ('market','market_investigation','agent.portfolio_mas'),
    ('portfolio','portfolio_rebalance','agent.market_mas'),
])
def test_live_single_domain_assembly_does_not_import_peer(api,monkeypatch,workflow,kind,absent):
    import builtins
    _,sessions=api; data=fixture_data(workflow); live.save_dataset(sessions,data)
    original=builtins.__import__
    def isolated(name,*args,**kwargs):
        if name==absent or name.startswith(absent+'.'):
            raise ModuleNotFoundError('Peer is not deployed')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',isolated)
    dispatcher,_=live.live_assembly(sessions,live.PREFIX+data.dataset_id,(kind,))
    assert dispatcher.drivers.get(kind).kind==kind
