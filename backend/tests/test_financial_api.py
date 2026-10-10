"""Real typed API, synthetic drivers and disposable SQLite, without a broker."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from agent.financial_demo import DEMO_AS_OF, DEMO_SNAPSHOT_ID
from api.routes import financial
from db.base import Base
from db.models import (Conversation, AgentRun, AgentEvent, FinancialRun,
    FinancialArtifact, FinancialInvocation)
from workers import agent_tasks


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path / 'api.db'),
        connect_args={'check_same_thread': False, 'timeout': 20})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as session:
        session.add(Conversation(id='c'))
        session.commit()
    monkeypatch.setattr(financial, 'sync_session_factory', sessions)
    monkeypatch.setattr(agent_tasks, 'sync_session_factory', sessions)
    monkeypatch.delenv('REDIS_URL', raising=False)
    app = FastAPI()
    app.include_router(financial.router, prefix='/api/financial')
    with TestClient(app) as client:
        yield client, sessions
    engine.dispose()


def body(workflow='combined', mode='auto', key='run'):
    result = dict(conversation_id='c', idempotency_key=key, mode=mode)
    if workflow != 'portfolio':
        result['market'] = dict(symbol='MU', sector_benchmark='SOXX', as_of=DEMO_AS_OF.isoformat())
    if workflow != 'market':
        result['portfolio'] = dict(portfolio_snapshot_id=DEMO_SNAPSHOT_ID,
            as_of=DEMO_AS_OF.isoformat(), user_constraints={'max_weight_by_symbol': {'MU': .25}})
    return result


ENDPOINTS = dict(market='market-investigations', portfolio='portfolio-reviews', combined='combined-reviews')


def create(client, workflow='combined', **kwargs):
    response = client.post('/api/financial/' + ENDPOINTS[workflow], json=body(workflow, **kwargs))
    assert response.status_code == 202, response.text
    return response.json()


def result(client, run_id):
    response = client.get('/api/financial/runs/' + run_id)
    assert response.status_code == 200, response.text
    return response.json()


def action(client, run_id, name, version=None):
    version = result(client, run_id)['version'] if version is None else version
    return client.post(f'/api/financial/runs/{run_id}/{name}', json={'expected_version': version})


def test_market_api_exposes_typed_hypotheses_without_model_causal_prose(api, monkeypatch):
    from agent.market_mas import SyntheticMarketModel
    original = SyntheticMarketModel.complete
    claim = '公告确定导致股价下跌。'

    async def complete(self, *args, **kwargs):
        response = await original(self, *args, **kwargs)
        return response.model_copy(update={'payload': {**response.payload, 'summary': claim}})

    monkeypatch.setattr(SyntheticMarketModel, 'complete', complete)
    client, sessions = api
    run_id = create(client, 'market')['runs'][0]['run_id']
    data = result(client, run_id)
    assert data['status'] == 'completed'
    assert data['artifact']['schema_version'] == 1
    assert claim not in json.dumps(data, ensure_ascii=False)
    assert all(h['disposition'] == 'unverified' for h in data['artifact']['hypotheses'])
    with sessions() as session:
        rows = session.scalars(select(FinancialInvocation).where(
            FinancialInvocation.run_id == run_id, FinancialInvocation.kind == 'model')).all()
        assert rows and all(row.output['summary'] == claim for row in rows)


@pytest.mark.parametrize('workflow', ENDPOINTS)
@pytest.mark.parametrize('mode', ['auto', 'review'])
def test_three_workflows_real_ids_initial_dispatch_and_idempotency(api, workflow, mode):
    client, sessions = api
    created = create(client, workflow, mode=mode)
    ids = [row['run_id'] for row in created['runs']]
    assert len(ids) == (2 if workflow == 'combined' else 1)
    assert len(set(ids)) == len(ids)
    for run_id in ids:
        data = result(client, run_id)
        assert data['status'] == ('completed' if mode == 'auto' else 'waiting_user')
        assert data['conversation_id'] == 'c'
        assert data['correlation_id'] == created['correlation_id']
        assert data['mode'] == mode
        assert ('checkpoint' not in data and 'final_answer' not in data)
        if mode == 'auto':
            assert data['artifact']['producing_run_id'] == run_id
            assert data['artifact_ref']['schema_version'] == 1
            assert data['validation_outcome'] == data['artifact']['status']
        else:
            assert data['artifact'] is None and data['validation_outcome'] == 'pending'
            with sessions() as session:
                assert session.scalar(select(AgentEvent).where(AgentEvent.run_id == run_id,
                    AgentEvent.event_type == 'mas.review_required'))
    before = {run_id: result(client, run_id) for run_id in ids}
    replay = create(client, workflow, mode=mode)
    assert [r['run_id'] for r in replay['runs']] == ids
    assert {run_id: result(client, run_id) for run_id in ids} == before
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(FinancialRun)) == len(ids)


@pytest.mark.parametrize('case', ['wrong_scope', 'market_hops', 'portfolio_hops', 'wrong_snapshot',
    'wrong_time', 'direct_artifact', 'wrong_endpoint', 'extra_profile', 'unknown_conversation',
    'market_counter', 'portfolio_counter'])
def test_invalid_creation_rejected_before_writes(api, case):
    client, sessions = api
    payload = body()
    endpoint = 'combined-reviews'
    expected = 422
    if case == 'wrong_scope': payload['market']['symbol'] = 'OTHER'
    elif case == 'market_hops': payload['market_budget'] = {'max_hops': 0}
    elif case == 'portfolio_hops': payload['portfolio_budget'] = {'max_hops': 0}
    elif case == 'wrong_snapshot': payload['portfolio']['portfolio_snapshot_id'] = 'real-holdings'
    elif case == 'wrong_time':
        payload['market']['as_of'] = payload['portfolio']['as_of'] = '2026-09-28T20:05:00Z'
    elif case == 'direct_artifact': payload['portfolio']['market_artifact_id'] = 'forged'
    elif case == 'wrong_endpoint': endpoint = 'market-investigations'
    elif case == 'extra_profile': payload['execution_profile'] = 'live'
    elif case == 'market_counter': payload['market_budget'] = {'model_calls': 1}
    elif case == 'portfolio_counter': payload['portfolio_budget'] = {'model_calls': 1}
    else: payload['conversation_id'] = 'missing'; expected = 404
    response = client.post('/api/financial/' + endpoint, json=payload)
    assert response.status_code == expected, response.text
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
        assert session.scalar(select(func.count()).select_from(FinancialRun)) == 0


def test_combined_review_ordering_per_run_cas_and_actual_market_consumption(api, monkeypatch):
    from agent.portfolio_mas import SyntheticPortfolioModel
    complete = SyntheticPortfolioModel.complete
    received = []
    async def observe(self, messages, **kwargs):
        received.extend(messages)
        return await complete(self, messages, **kwargs)
    monkeypatch.setattr(SyntheticPortfolioModel, 'complete', observe)
    client, sessions = api
    pair = create(client, mode='review')
    market, portfolio = pair['market_run_id'], pair['portfolio_run_id']
    portfolio_before = result(client, portfolio)
    assert action(client, portfolio, 'approve').status_code == 409
    assert result(client, portfolio) == portfolio_before
    assert action(client, market, 'approve').status_code == 200
    assert result(client, market)['status'] == 'completed'
    assert result(client, portfolio)['status'] == 'waiting_user'
    assert action(client, portfolio, 'approve').status_code == 200
    assert result(client, portfolio)['status'] == 'completed'
    assert 'market_evidence_unavailable' not in result(client, portfolio)['limitations']
    assert 'SYSTEM_UNAVAILABLE' not in result(client, portfolio)['limitations']
    dispatcher, _ = financial._assembly(())
    relations = dispatcher.relations(portfolio)
    ready = next(r for r in relations if r['envelope'].get('message_type') == 'MARKET_EVIDENCE_READY')
    selection = next(r for r in relations if r['relation_type'] == 'artifact_selection')
    assert selection['envelope']['causation_id'] == ready['envelope']['message_id']
    artifact = result(client, market)['artifact']
    with sessions() as session:
        outputs = list(session.scalars(select(FinancialInvocation.output).where(
            FinancialInvocation.run_id == portfolio)))
    # The immutable Market evidence entered the actual Portfolio specialists' work.
    assert artifact['producing_run_id'] in json.dumps(received)
    assert all(e['id'] in json.dumps(received) for e in artifact['evidence'])
    assert outputs


def test_stale_version_and_pause_resume_only_submitted_run(api):
    client, _ = api
    pair = create(client, mode='review')
    market, portfolio = pair['market_run_id'], pair['portfolio_run_id']
    old = result(client, market)['version']
    peer = result(client, portfolio)
    assert action(client, market, 'pause', old).status_code == 200
    assert action(client, market, 'resume', old).status_code == 409
    assert result(client, market)['status'] == 'paused'
    assert result(client, portfolio) == peer
    assert action(client, market, 'resume').status_code == 200
    assert result(client, market)['status'] == 'waiting_user'
    assert result(client, portfolio) == peer
    assert action(client, portfolio, 'pause').status_code == 200
    assert action(client, portfolio, 'resume').status_code == 409
    assert result(client, portfolio)['status'] == 'paused'


@pytest.mark.parametrize('cancelled', ['market', 'portfolio'])
@pytest.mark.parametrize('mode', ['review', 'auto'])
def test_both_cancel_directions_reconcile_peer_without_approval(api, monkeypatch, cancelled, mode):
    client, _ = api
    saved = financial._dispatch
    monkeypatch.setattr(financial, '_dispatch', lambda *args: None)
    pair = create(client, mode=mode)
    monkeypatch.setattr(financial, '_dispatch', saved)
    own = pair[cancelled + '_run_id']
    peer = pair[('portfolio' if cancelled == 'market' else 'market') + '_run_id']
    assert action(client, own, 'cancel').status_code == 200
    assert result(client, own)['status'] == 'cancelled'
    assert result(client, peer)['status'] == ('waiting_user' if mode == 'review' else 'completed')
    dispatcher, _ = financial._assembly(())
    if cancelled == 'market':
        assert any(r['envelope'].get('message_type') == 'SYSTEM_UNAVAILABLE' for r in dispatcher.relations(peer))
        assert 'SYSTEM_UNAVAILABLE' in result(client, peer)['limitations']
        assert 'SYSTEM_UNAVAILABLE' not in result(client, own)['limitations']
        if mode == 'auto': assert 'market_evidence_unavailable' in result(client, peer)['limitations']
    else:
        assert 'SYSTEM_UNAVAILABLE' not in result(client, peer)['limitations']
    with api[1]() as session:
        assert not list(session.scalars(select(AgentEvent).where(AgentEvent.run_id == peer,
            AgentEvent.event_type == 'mas.approve')))


def test_broker_exception_falls_back_and_repeat_create_redrives_existing_ids(api, monkeypatch):
    client, _ = api
    monkeypatch.setenv('REDIS_URL', 'redis://unavailable:6379/0')
    calls = []
    def failure(run_id):
        calls.append(run_id)
        raise ConnectionError('broker unavailable')
    monkeypatch.setattr(agent_tasks.run_financial_pair, 'delay', failure)
    pair = create(client)
    assert all(result(client, row['run_id'])['status'] == 'completed' for row in pair['runs'])
    assert create(client)['runs'] == [{**row, 'status': result(client, row['run_id'])['status'],
        'version': result(client, row['run_id'])['version']} for row in pair['runs']]
    assert calls == [pair['market_run_id']] * 2


def test_publish_failure_after_delivery_replays_without_duplicate_work(api, monkeypatch):
    client, sessions = api
    monkeypatch.setenv('REDIS_URL', 'redis://unavailable:6379/0')
    def delivered_then_failed(run_id):
        agent_tasks.run_financial_pair.run(run_id)
        raise ConnectionError('publisher acknowledgement lost')
    monkeypatch.setattr(agent_tasks.run_financial_pair, 'delay', delivered_then_failed)
    pair = create(client)
    with sessions() as session:
        count = session.scalar(select(func.count()).select_from(FinancialInvocation))
    before = {row['run_id']: result(client, row['run_id']) for row in pair['runs']}
    create(client)
    assert {run_id: result(client, run_id) for run_id in before} == before
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(FinancialInvocation)) == count


@pytest.mark.parametrize('mode', ['review', 'auto'])
def test_optional_transfer_failure_allows_bounded_portfolio_with_explicit_limitation(api, monkeypatch, mode):
    client, _ = api
    from agent.integration import CrossMASRouter
    def unavailable(*args, **kwargs):
        raise ValueError('optional transfer unavailable')
    monkeypatch.setattr(CrossMASRouter, 'transfer', unavailable)
    pair = create(client, mode=mode)
    if mode == 'review':
        assert action(client, pair['market_run_id'], 'approve').status_code == 200
    assert result(client, pair['market_run_id'])['status'] == 'completed'
    if mode == 'review':
        assert action(client, pair['portfolio_run_id'], 'approve').status_code == 200
    portfolio = result(client, pair['portfolio_run_id'])
    assert portfolio['status'] == 'completed'
    assert 'market_evidence_unavailable' in portfolio['limitations']
    dispatcher, _ = financial._assembly(())
    assert not any(r['relation_type'] == 'cross_admitted' and r['target_run_id'] == pair['portfolio_run_id']
        and r['envelope'].get('message_type') == 'SYSTEM_UNAVAILABLE'
        for r in dispatcher.relations(pair['portfolio_run_id']))
    assert 'SYSTEM_UNAVAILABLE' not in portfolio['limitations']


def test_public_result_openapi_discriminates_exact_artifacts_by_mas_kind(api):
    schema = api[0].app.openapi()['paths']['/api/financial/runs/{run_id}']['get']['responses']['200']['content']['application/json']['schema']
    assert schema['discriminator']['propertyName'] == 'mas_kind'
    assert set(schema['discriminator']['mapping']) == {'market_investigation', 'portfolio_rebalance'}


def test_repeat_create_recovers_accepted_but_undelivered_pair(api, monkeypatch):
    client, _ = api
    saved = financial._dispatch
    monkeypatch.setattr(financial, '_dispatch', lambda *args: None)
    pair = create(client)
    assert result(client, pair['market_run_id'])['status'] == 'queued'
    monkeypatch.setattr(financial, '_dispatch', saved)
    replay = create(client)
    assert replay['market_run_id'] == pair['market_run_id']
    assert replay['portfolio_run_id'] == pair['portfolio_run_id']
    assert result(client, pair['portfolio_run_id'])['status'] == 'completed'


@pytest.mark.parametrize('field', ['run_id', 'mas_kind', 'schema_version', 'conversation_id', 'as_of', 'payload_producer'])
def test_result_rejects_corrupt_or_foreign_artifact_ownership(api, field):
    client, sessions = api
    created = create(client, 'market')
    run_id = created['market_run_id']
    with sessions() as session:
        row = session.scalar(select(FinancialArtifact).where(FinancialArtifact.run_id == run_id))
        if field == 'run_id': row.run_id = 'other'
        elif field == 'mas_kind': row.mas_kind = 'portfolio_rebalance'
        elif field == 'schema_version': row.schema_version = 2
        elif field == 'conversation_id': row.conversation_id = 'other'
        elif field == 'as_of': row.as_of = DEMO_AS_OF.replace(day=28)
        else: row.payload = {**row.payload, 'producing_run_id': 'other'}
        session.commit()
    assert client.get('/api/financial/runs/' + run_id).status_code == 409


@pytest.mark.parametrize('status', ['feasible', 'infeasible', 'insufficient_data'])
def test_all_portfolio_artifact_outcomes_are_typed(api, status):
    client, sessions = api
    pair = create(client, 'portfolio')
    run_id = pair['portfolio_run_id']
    with sessions() as session:
        row = session.scalar(select(FinancialArtifact).where(FinancialArtifact.run_id == run_id))
        row.payload = {**row.payload, 'status': status}
        session.commit()
    data = result(client, run_id)
    assert data['validation_outcome'] == status == data['artifact']['status']


def test_unknown_run_and_invalid_action_body(api):
    client, _ = api
    assert client.get('/api/financial/runs/missing').status_code == 404
    assert client.post('/api/financial/runs/missing/approve', json={'expected_version': 1}).status_code == 404
    pair = create(client, 'market', mode='review')
    assert client.post('/api/financial/runs/' + pair['market_run_id'] + '/approve',
        json={'expected_version': 0}).status_code == 422


def test_api_cannot_approve_an_unconfigured_execution_profile(api):
    client, sessions = api
    pair = create(client, 'market', mode='review')
    run_id = pair['market_run_id']
    before = result(client, run_id)
    with sessions() as session:
        meta = session.get(FinancialRun, run_id)
        meta.creation_inputs = {**meta.creation_inputs, 'execution_profile': 'configured-not-deployed'}
        session.commit()
    assert action(client, run_id, 'approve').status_code == 409
    assert result(client, run_id) == before


def test_pair_worker_restores_from_either_actual_member_id(api):
    client, _ = api
    pair = create(client)
    before = {row['run_id']: result(client, row['run_id']) for row in pair['runs']}
    for member in before:
        restored = agent_tasks.run_financial_pair.run(member)
        assert restored['market_run_id'] == pair['market_run_id']
        assert restored['portfolio_run_id'] == pair['portfolio_run_id']
    assert {run_id: result(client, run_id) for run_id in before} == before


def test_general_api_creation_shape_and_no_redis_behavior_remain_unchanged(api, monkeypatch):
    from api.routes import agent
    from agent.orchestrator import AgentOrchestrator
    from agent.llm import ScriptedFakeModel
    client, sessions = api
    monkeypatch.setattr(agent, 'sync_session_factory', sessions)
    monkeypatch.setattr(agent, '_orchestrator', lambda: AgentOrchestrator(sessions, ScriptedFakeModel([])))
    client.app.include_router(agent.router, prefix='/api/agent')
    response = client.post('/api/agent/runs', json={'conversation_id': 'c', 'goal': 'General regression', 'mode': 'review'})
    assert response.status_code == 202, response.text
    data = response.json()
    assert data['status'] == 'created' and data['goal'] == 'General regression'
    assert 'id' in data and 'run_id' not in data and 'mas_kind' not in data
    assert client.get('/api/agent/runs/' + data['id']).json() == data
    assert client.get('/api/financial/runs/' + data['id']).status_code == 404
    with sessions() as session:
        assert session.get(FinancialRun, data['id']) is None


def test_pair_worker_real_fresh_interpreter_registration_restore_and_consumption(tmp_path):
    root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.pop('REDIS_URL', None)
    env['DATABASE_URL'] = 'sqlite+aiosqlite:///' + (tmp_path / 'fresh.db').as_posix()
    env['PYTHONPATH'] = os.pathsep.join(str(p) for p in (root, root / 'backend', root / 'lobster_quant'))
    code = '''
from db.base import Base
import db.models
from db.session import sync_engine, sync_session_factory
from db.models import Conversation
from agent.financial import build_financial_dispatcher
from agent.financial_demo import DEMO_AS_OF, DEMO_SNAPSHOT_ID, demo_snapshot_loader
from agent.integration import CrossMASRequest, CrossMASRouter
from agent.shared import ArtifactStore, MarketInvestigationRequest, PortfolioReviewRequest
from workers.celery_app import celery_app
Base.metadata.create_all(sync_engine())
with sync_session_factory() as s:
    s.add(Conversation(id='fresh'));s.commit()
d=build_financial_dispatcher(sync_session_factory)
r=CrossMASRouter(d,ArtifactStore(sync_session_factory),demo_snapshot_loader,execution_profile='synthetic-demo-v1')
p=r.create(CrossMASRequest(conversation_id='fresh',idempotency_key='fresh',mode='auto',
    market=MarketInvestigationRequest(symbol='MU',as_of=DEMO_AS_OF),
    portfolio=PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID,as_of=DEMO_AS_OF)))
celery_app.loader.import_default_modules()
task=celery_app.tasks['backend.workers.agent_tasks.run_financial_pair']
for member in (p.portfolio_run_id,p.market_run_id):
    result=task.run(member)
    assert result['market_run_id']==p.market_run_id
    assert result['portfolio_run_id']==p.portfolio_run_id
assert d.snapshot(p.market_run_id)['status']=='completed'
assert d.snapshot(p.portfolio_run_id)['status']=='completed'
assert any(x['relation_type']=='artifact_selection' for x in d.relations(p.portfolio_run_id))
print('fresh pair task: two actual IDs restored, completed and Market artifact consumed')
'''
    output = subprocess.run([sys.executable, '-c', code], env=env, cwd=tmp_path,
        capture_output=True, text=True, timeout=60)
    assert output.returncode == 0, output.stdout + output.stderr
    assert 'Market artifact consumed' in output.stdout


def followup_pair(client, monkeypatch, *, portfolio_mode, market_mode):
    saved = financial._dispatch
    monkeypatch.setattr(financial, '_dispatch', lambda *args: None)
    portfolio = create(client, 'portfolio', mode=portfolio_mode)['portfolio_run_id']
    monkeypatch.setattr(financial, '_dispatch', saved)
    dispatcher, route = financial._assembly()
    from agent.shared import MarketInvestigationRequest
    relation = route.request_further_evidence(portfolio,
        MarketInvestigationRequest(symbol='MU', as_of=DEMO_AS_OF),
        idempotency_key='followup', mode=market_mode)
    return portfolio, relation['target_run_id'], dispatcher


@pytest.mark.parametrize('cancelled', ['market', 'portfolio'])
@pytest.mark.parametrize('portfolio_mode', ['review', 'auto'])
@pytest.mark.parametrize('market_mode', ['review', 'auto'])
def test_followup_cancel_both_directions_saved_modes_and_duplicate_delivery(api, monkeypatch,
        cancelled, portfolio_mode, market_mode):
    client, sessions = api
    portfolio, market, dispatcher = followup_pair(client, monkeypatch,
        portfolio_mode=portfolio_mode, market_mode=market_mode)
    own, peer = (market, portfolio) if cancelled == 'market' else (portfolio, market)
    peer_mode = portfolio_mode if cancelled == 'market' else market_mode
    stale = result(client, own)['version']
    assert action(client, own, 'cancel', stale).status_code == 200
    assert result(client, own)['status'] == 'cancelled'
    assert result(client, peer)['mode'] == peer_mode
    assert result(client, peer)['status'] == ('waiting_user' if peer_mode == 'review' else 'completed')
    with sessions() as session:
        events = list(session.scalars(select(AgentEvent).where(AgentEvent.run_id.in_([own, peer]))))
        assert not any(e.event_type == 'mas.approve' for e in events)
        count = len(events)
    before = {run_id: dispatcher.snapshot(run_id) for run_id in (own, peer)}
    # Both stale and fresh-version repeats refuse to create another cancellation.
    assert action(client, own, 'cancel', stale).status_code == 409
    assert action(client, own, 'cancel').status_code == 409
    agent_tasks.run_financial_pair.run(peer)
    agent_tasks.run_financial_pair.run(peer)
    assert {run_id: dispatcher.snapshot(run_id) for run_id in before} == before
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AgentEvent).where(
            AgentEvent.run_id.in_([own, peer]))) == count
    if cancelled == 'market':
        assert any(r['envelope'].get('message_type') == 'SYSTEM_UNAVAILABLE'
            and r['source_run_id'] == market and r['target_run_id'] == portfolio
            for r in dispatcher.relations(portfolio))


@pytest.mark.parametrize('cancelled', ['market', 'portfolio'])
def test_followup_cancel_with_terminal_peer_does_not_dispatch(api, monkeypatch, cancelled):
    client, _ = api
    portfolio, market, dispatcher = followup_pair(client, monkeypatch,
        portfolio_mode='review', market_mode='review')
    own, peer = (market, portfolio) if cancelled == 'market' else (portfolio, market)
    dispatcher.cancel(peer, dispatcher.snapshot(peer)['version'])
    peer_before = dispatcher.snapshot(peer)
    scheduled = []
    monkeypatch.setattr(financial, '_dispatch', lambda *args: scheduled.append(args))
    assert action(client, own, 'cancel').status_code == 200
    assert scheduled == []
    assert dispatcher.snapshot(peer) == peer_before
    assert dispatcher.snapshot(own)['status'] == 'cancelled'


@pytest.mark.parametrize('corruption', ['source', 'message', 'direction'])
def test_followup_cancel_rejects_wrong_request_authority_before_cas(api, monkeypatch, corruption):
    from db.models.financial_mas import FinancialRelation
    client, sessions = api
    portfolio, market, dispatcher = followup_pair(client, monkeypatch,
        portfolio_mode='review', market_mode='review')
    with sessions() as session:
        row = session.scalar(select(FinancialRelation).where(FinancialRelation.target_run_id == market))
        if corruption == 'source': row.source_run_id = 'foreign'
        elif corruption == 'message': row.envelope = {**row.envelope, 'message_id': 'forged-message'}
        else: row.source_run_id, row.target_run_id = market, portfolio
        session.commit()
    before = dispatcher.snapshot(market)
    scheduled = []
    monkeypatch.setattr(financial, '_dispatch', lambda *args: scheduled.append(args))
    assert action(client, market, 'cancel').status_code == 409
    assert dispatcher.snapshot(market) == before
    assert scheduled == []


@pytest.mark.parametrize('initial_market_terminal', ['completed', 'cancelled'])
@pytest.mark.parametrize('followup_mode', ['review', 'auto'])
def test_cancel_combined_portfolio_skips_terminal_initial_market_and_delivers_only_followup(
        api, monkeypatch, initial_market_terminal, followup_mode):
    from agent.shared import MarketInvestigationRequest
    client, _ = api
    saved = financial._dispatch
    monkeypatch.setattr(financial, '_dispatch', lambda *args: None)
    combined = create(client, mode='review')
    monkeypatch.setattr(financial, '_dispatch', saved)
    initial, portfolio = combined['market_run_id'], combined['portfolio_run_id']
    dispatcher, route = financial._assembly()
    assert agent_tasks.run_agent.run(portfolio)['status'] == 'waiting_user'
    if initial_market_terminal == 'completed':
        assert agent_tasks.run_agent.run(initial)['status'] == 'waiting_user'
        dispatcher.approve(initial, dispatcher.snapshot(initial)['version'])
        assert agent_tasks.run_agent.run(initial)['status'] == 'completed'
    else:
        dispatcher.cancel(initial, dispatcher.snapshot(initial)['version'])
    relation = route.request_further_evidence(portfolio,
        MarketInvestigationRequest(symbol='MU', as_of=DEMO_AS_OF),
        idempotency_key='combined-followup', mode=followup_mode)
    followup = relation['target_run_id']
    initial_before = dispatcher.snapshot(initial)
    scheduled = []
    def observe(run_id, paired, background):
        scheduled.append((run_id, paired))
        saved(run_id, paired, background)
    monkeypatch.setattr(financial, '_dispatch', observe)
    assert action(client, portfolio, 'cancel').status_code == 200
    assert scheduled == [(followup, True)]
    assert dispatcher.snapshot(initial) == initial_before
    assert dispatcher.snapshot(portfolio)['status'] == 'cancelled'
    assert result(client, followup)['status'] == ('waiting_user' if followup_mode == 'review' else 'completed')
    with api[1]() as session:
        assert not list(session.scalars(select(AgentEvent).where(AgentEvent.run_id == followup,
            AgentEvent.event_type == 'mas.approve')))
    before = {member: dispatcher.snapshot(member) for member in (initial, portfolio, followup)}
    agent_tasks.run_financial_pair.run(followup)
    assert {member: dispatcher.snapshot(member) for member in before} == before
