"""Real reviewed W4/W5 drivers, W2/W3 tools and disposable persisted SQLite."""
import asyncio
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from agent.financial import build_financial_dispatcher
from agent.financial_demo import (DEMO_AS_OF, DEMO_SNAPSHOT_ID, demo_snapshot_loader,
    demo_market_dependencies, demo_histories, demo_classifications)
from agent.integration import CrossMASRequest, CrossMASRouter
from agent.llm import ScriptedFakeModel
from agent.portfolio_mas import PortfolioDriver, PortfolioDependencies, SyntheticPortfolioModel
from agent.market_mas import SyntheticMarketModel
from agent.shared import (ArtifactStore, BudgetExhausted, CrossMASEnvelope,
    FinancialConflict, MarketInvestigationRequest, PortfolioReviewRequest, RunBudget,
    WorkflowRegistry, FinancialMASDispatcher)
from db.base import Base
from db.models import (Conversation, AgentRun, AgentEvent, FinancialArtifact,
    FinancialInvocation, ToolResult, ToolCall)


@pytest.fixture
def assembly(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'cross.db'),
        connect_args={'check_same_thread': False, 'timeout': 20})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all([Conversation(id='c'), Conversation(id='other')])
        db.commit()
    now = [DEMO_AS_OF]
    def make(enabled=('market_investigation', 'portfolio_rebalance'), loader=demo_snapshot_loader, market_provider=None):
        router = None
        kwargs = {}
        profile = 'synthetic-demo-v1'
        if market_provider is not None:
            profile = 'configured-test-synthetic-cross-v1'
            history, events = demo_market_dependencies()
            providers = {'market_investigation': {r: SyntheticMarketModel(r) for r in
                ('coordinator', 'price_volume', 'macro_sector', 'event', 'critic')},
                'portfolio_rebalance': {r: SyntheticPortfolioModel(r) for r in
                ('coordinator', 'opportunity', 'risk', 'constraint', 'verifier')}}
            providers['market_investigation']['price_volume'] = market_provider
            kwargs = dict(demo=False, execution_profile=profile, providers=providers,
                market_dependencies=history, event_dependencies=events,
                portfolio_dependencies=PortfolioDependencies(demo_snapshot_loader,
                    lambda snapshot, as_of: demo_histories(), demo_classifications()))
        d = build_financial_dispatcher(sessions, enabled=enabled, clock=lambda: now[0],
            portfolio_artifact_resolver=lambda *args: router.artifact_resolver(*args), **kwargs)
        router = CrossMASRouter(d, ArtifactStore(sessions), loader,
            execution_profile=profile, clock=lambda: now[0], ttl_seconds=30)
        return d, router
    d, router = make()
    yield d, router, sessions, now, make
    engine.dispose()


def inputs(mode='auto', workflow='combined', key='combined', **kwargs):
    return CrossMASRequest(conversation_id='c', idempotency_key=key, mode=mode,
        market=MarketInvestigationRequest(symbol='MU', sector_benchmark='SOXX', as_of=DEMO_AS_OF)
            if workflow != 'portfolio' else None,
        portfolio=PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID,
            as_of=DEMO_AS_OF, user_constraints={'max_weight_by_symbol': {'MU': .25}, 'min_cash_weight': .2})
            if workflow != 'market' else None, **kwargs)


def completed_artifact(d, run_id):
    snapshot = d.snapshot(run_id)
    assert snapshot['status'] == 'completed', snapshot
    return json.loads(snapshot['final_answer'])


def prepare(d, router, **kwargs):
    pair = router.create(inputs(**kwargs))
    assert asyncio.run(d.start(pair.market_run_id)).status == 'completed'
    relation = router.transfer(pair.market_run_id, pair.portfolio_run_id)
    return pair, relation


@pytest.mark.parametrize('workflow', ['market', 'portfolio', 'combined'])
def test_three_actual_workflows_artifacts_audits_and_no_writes(assembly, workflow):
    d, router, sessions, _, _ = assembly
    original = sha256(demo_snapshot_loader(DEMO_SNAPSHOT_ID).model_dump_json().encode()).hexdigest()
    pair = router.create(inputs(workflow=workflow))
    asyncio.run(router.advance(pair))
    artifact_ids = []
    for run_id in (pair.market_run_id, pair.portfolio_run_id):
        if run_id:
            result = completed_artifact(d, run_id)
            artifact_ids.extend(d.snapshot(run_id)['checkpoint']['artifact_ids'])
            assert result['producing_run_id'] == run_id
            with sessions() as db:
                assert db.get(AgentRun, run_id).parent_run_id is None
                events = db.scalars(select(AgentEvent).where(AgentEvent.run_id == run_id).order_by(AgentEvent.seq)).all()
                assert [e.seq for e in events] == list(range(1, len(events) + 1))
                actual = {r.id for r in db.scalars(select(ToolResult).join(ToolCall).where(ToolCall.run_id == run_id))}
                assert actual
                if 'numeric_facts' in result:
                    assert result['numeric_facts']
                    assert {f['tool_result_id'] for f in result['numeric_facts']} <= actual
                    assert all(e['source_type'] == 'market_tool' or e['source_locator'].startswith('fixture://financial-demo/v1/') for e in result['evidence'])
                else:
                    assert result['status'] == 'feasible'
                    assert result['constraint_check']['status'] == 'pass'
                    assert set(result['evidence_ids']) <= actual
                    assert result['simulation']['tool_result_id'] in actual
    if workflow == 'combined':
        assert pair.market_run_id != pair.portfolio_run_id
        snapshots = [d.snapshot(r) for r in (pair.market_run_id, pair.portfolio_run_id)]
        assert {s['correlation_id'] for s in snapshots} == {pair.correlation_id}
        assert {s['execution_profile'] for s in snapshots} == {'synthetic-demo-v1'}
        assert snapshots[0]['budget']['hops'] == 1 and snapshots[1]['budget']['hops'] == 0
        with sessions() as db:
            roles = db.scalars(select(FinancialInvocation).where(FinancialInvocation.run_id == pair.portfolio_run_id,
                FinancialInvocation.kind == 'model')).all()
            assert len(roles) == 5
        assert router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio).producing_run_id == pair.market_run_id
    assert original == sha256(demo_snapshot_loader(DEMO_SNAPSHOT_ID).model_dump_json().encode()).hexdigest()
    with sessions() as db:
        assert len(db.scalars(select(FinancialArtifact)).all()) == len(artifact_ids)


def test_creation_parallel_independence_and_cancel(assembly):
    d, router, sessions, _, _ = assembly
    with ThreadPoolExecutor(max_workers=2) as pool:
        pairs = list(pool.map(lambda _: router.create(inputs()), range(2)))
    assert pairs[0] == pairs[1]
    pair = pairs[0]
    d.cancel(pair.market_run_id, d.snapshot(pair.market_run_id)['version'])
    asyncio.run(router.advance(pair))
    assert d.snapshot(pair.market_run_id)['status'] == 'cancelled'
    assert completed_artifact(d, pair.portfolio_run_id)['status'] == 'feasible'
    with sessions() as db:
        assert len(db.scalars(select(AgentRun)).all()) == 2
    with pytest.raises(FinancialConflict):
        router.create(inputs(mode='review'))


@pytest.mark.parametrize('enabled', [('market_investigation',), ('portfolio_rebalance',)])
def test_undeployed_peer_keeps_actual_domain_completion(assembly, enabled):
    _, _, _, _, make = assembly
    d, router = make(enabled)
    pair = router.create(inputs())
    assert len(pair.limitations) == 1
    asyncio.run(router.advance(pair))
    assert completed_artifact(d, pair.market_run_id or pair.portfolio_run_id)


@pytest.mark.parametrize('budget', [RunBudget(max_hops=0), RunBudget(max_followups=0)])
def test_lowered_zero_budget_degrades_and_never_followups(assembly, budget):
    d, router, _, _, _ = assembly
    pair = router.create(inputs(market_budget=budget, portfolio_budget=budget))
    if budget.max_hops == 0:
        asyncio.run(router.advance(pair))
        assert completed_artifact(d, pair.portfolio_run_id)['status'] == 'feasible'
        assert router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio) is None
    else:
        asyncio.run(d.start(pair.market_run_id))
        router.transfer(pair.market_run_id, pair.portfolio_run_id)
    with pytest.raises((BudgetExhausted, FinancialConflict)):
        router.request_further_evidence(pair.portfolio_run_id, inputs().market, idempotency_key='extra', mode='auto')


def test_one_followup_matched_zero_hop_reply_duplicate_and_history_immutable(assembly):
    d, router, sessions, _, _ = assembly
    pair, initial = prepare(d, router)
    before = d.snapshot(pair.market_run_id)
    with sessions() as db:
        artifact = db.get(FinancialArtifact, before['checkpoint']['artifact_ids'][0])
        digest, payload = artifact.content_hash, artifact.payload
    request = router.request_further_evidence(pair.portfolio_run_id, inputs().market,
        idempotency_key='extra', mode='auto')
    assert request == router.request_further_evidence(pair.portfolio_run_id, inputs().market,
        idempotency_key='extra', mode='auto')
    follow = request['target_run_id']
    assert follow != pair.market_run_id
    asyncio.run(router.advance(router.restore(pair.portfolio_run_id)))
    assert completed_artifact(d, follow)['numeric_facts']
    assert completed_artifact(d, pair.portfolio_run_id)['status'] == 'feasible'
    replies = [r for r in d.relations(follow) if r['relation_type'] == 'cross_admitted'
        and r['envelope'].get('causation_id') == request['envelope']['message_id']]
    assert len(replies) == 1 and replies[0]['envelope']['message_type'] == 'MARKET_EVIDENCE_READY'
    assert router.transfer(follow, pair.portfolio_run_id, request_relation=request) == replies[0]
    assert sum(d.snapshot(r)['budget']['hops'] for r in (pair.market_run_id, pair.portfolio_run_id, follow)) == 2
    assert sum(d.snapshot(r)['budget']['followups'] for r in (pair.market_run_id, pair.portfolio_run_id, follow)) == 1
    with pytest.raises(FinancialConflict):
        router.request_further_evidence(pair.portfolio_run_id, inputs().market, idempotency_key='loop', mode='auto')
    assert router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio).producing_run_id == follow
    with sessions() as db:
        row = db.get(FinancialArtifact, before['checkpoint']['artifact_ids'][0])
        assert row.content_hash == digest and row.payload == payload
        assert db.get(AgentRun, follow).parent_run_id is None


def test_unselected_expiry_degrades_but_exact_replay_does_not_extend(assembly):
    d, router, _, now, _ = assembly
    pair, relation = prepare(d, router)
    now[0] += timedelta(seconds=31)
    assert router.transfer(pair.market_run_id, pair.portfolio_run_id) == relation
    assert router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio) is None
    asyncio.run(router.advance(pair))
    assert completed_artifact(d, pair.portfolio_run_id)['status'] == 'feasible'


@pytest.mark.parametrize('attack', ['conversation', 'as_of', 'scope', 'schema', 'future', 'expired', 'causation'])
def test_invalid_envelopes_and_scoped_consumption_rejected_without_counter_change(assembly, attack):
    d, router, _, now, make = assembly
    pair, relation = prepare(d, router)
    original = CrossMASEnvelope.model_validate(relation['envelope'])
    bad = original.model_copy(deep=True, update={'message_id': 'bad-' + attack, 'idempotency_key': 'bad-' + attack})
    if attack == 'conversation':
        with pytest.raises(ValueError):
            router.artifact_resolver(pair.portfolio_run_id, 'other', inputs().portfolio)
        return
    if attack == 'scope':
        _, router = make(loader=lambda _: demo_snapshot_loader(DEMO_SNAPSHOT_ID).model_copy(update={'holdings': ()}))
        with pytest.raises(ValueError):
            router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio)
        assert not any(r['relation_type'] == 'artifact_selection' for r in d.relations(pair.portfolio_run_id))
        return
    if attack == 'as_of': bad.as_of += timedelta(days=1)
    if attack == 'schema': bad.payload_ref = bad.payload_ref.model_copy(update={'schema_version': 2})
    if attack == 'future':
        bad.created_at = now[0] + timedelta(seconds=1)
    if attack == 'expired':
        now[0] += timedelta(seconds=31)
    if attack == 'causation': bad.causation_id = 'unknown'
    before = [d.snapshot(r) for r in (pair.market_run_id, pair.portfolio_run_id)]
    with pytest.raises((ValueError, FinancialConflict)):
        router.admit(pair.market_run_id, pair.portfolio_run_id, bad,
            expected_source_version=before[0]['version'], expected_target_version=before[1]['version'])
    assert before == [d.snapshot(r) for r in (pair.market_run_id, pair.portfolio_run_id)]


def test_stale_dual_cas_and_concurrent_duplicate_transfer(assembly):
    d, router, _, _, _ = assembly
    pair, relation = prepare(d, router)
    source, target = d.snapshot(pair.market_run_id), d.snapshot(pair.portfolio_run_id)
    envelope = CrossMASEnvelope.model_validate(relation['envelope']).model_copy(
        update={'message_id': 'stale', 'idempotency_key': 'stale'})
    with pytest.raises(FinancialConflict):
        router.admit(pair.market_run_id, pair.portfolio_run_id, envelope,
            expected_source_version=source['version'], expected_target_version=target['version'] - 1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: router.transfer(pair.market_run_id, pair.portfolio_run_id), range(2)))
    assert results == [relation, relation]
    assert d.snapshot(pair.market_run_id)['budget']['hops'] == 1


def test_review_approval_and_market_checkpoint_restore(assembly):
    d, router, sessions, _, _ = assembly
    pair = router.create(inputs(mode='review'))
    asyncio.run(router.advance(pair))
    assert d.snapshot(pair.market_run_id)['status'] == d.snapshot(pair.portfolio_run_id)['status'] == 'waiting_user'
    for run_id in (pair.market_run_id, pair.portfolio_run_id):
        d.approve(run_id, d.snapshot(run_id)['version'])
    # Actual reviewed Market driver checkpoint hook; assembly remains immutable.
    d.drivers.get('market_investigation').yield_after_handoff = True
    asyncio.run(router.advance(pair, max_deliveries=1))
    assert d.snapshot(pair.market_run_id)['checkpoint']['state']['phase'] == 'role:0'
    # Portfolio independently completes instead of waiting on Market checkpoints.
    assert completed_artifact(d, pair.portfolio_run_id)['status'] == 'feasible'
    fresh = build_financial_dispatcher(sessions, enabled=('market_investigation',), clock=d.clock)
    replacement = CrossMASRouter(fresh, ArtifactStore(sessions), demo_snapshot_loader,
        execution_profile='synthetic-demo-v1', clock=d.clock)
    restored = replacement.restore(pair.market_run_id)
    assert restored.market_run_id == pair.market_run_id and restored.portfolio_run_id == pair.portfolio_run_id
    asyncio.run(replacement.advance(restored))
    assert completed_artifact(fresh, pair.market_run_id)['numeric_facts']


def test_portfolio_checkpoint_selected_context_replays_after_ttl_expiry(assembly):
    d, router, sessions, now, _ = assembly
    pair, _ = prepare(d, router)
    old = d.drivers.get('portfolio_rebalance')
    providers = {r: SyntheticPortfolioModel(r) for r in ('coordinator', 'opportunity', 'risk', 'constraint', 'verifier')}
    providers['coordinator'] = ScriptedFakeModel([
        {'kind': 'result', 'payload': {'role': 'coordinator', 'action': 'proposal', 'summary': 'synthetic rejected', 'proposed_weights': {'MU': 1, 'CASH': 0}}},
        {'kind': 'result', 'payload': {'role': 'coordinator', 'action': 'proposal', 'summary': 'synthetic repaired', 'proposed_weights': {'MU': .2, 'SOXX': .2, 'SPY': .1, 'TLT': .1, 'CASH': .4}}}])
    workflows = WorkflowRegistry()
    workflows.register(PortfolioDriver(providers, old.dependencies, artifact_resolver=router.artifact_resolver, yield_after_revision=True))
    checkpoint_d = FinancialMASDispatcher(sessions, workflows, d.tools,
        execution_profile='synthetic-demo-v1', clock=lambda: now[0])
    assert asyncio.run(checkpoint_d.start(pair.portfolio_run_id)).status == 'executing'
    assert checkpoint_d.snapshot(pair.portfolio_run_id)['checkpoint']['state']['phase'] == 'revision_ready'
    assert len([r for r in d.relations(pair.portfolio_run_id) if r['relation_type'] == 'artifact_selection']) == 1
    before_relations = d.relations(pair.portfolio_run_id)
    before_hops = sum(d.snapshot(r)['budget']['hops'] for r in (pair.market_run_id, pair.portfolio_run_id))
    now[0] += timedelta(seconds=31)
    fresh = {r: SyntheticPortfolioModel(r) for r in providers}
    fresh['coordinator'] = ScriptedFakeModel([{'kind': 'result', 'payload': {'role': 'coordinator', 'action': 'proposal',
        'summary': 'synthetic repaired', 'proposed_weights': {'MU': .2, 'SOXX': .2, 'SPY': .1, 'TLT': .1, 'CASH': .4}}}])
    next_workflows = WorkflowRegistry()
    restored_router = CrossMASRouter(checkpoint_d, ArtifactStore(sessions), demo_snapshot_loader,
        execution_profile='synthetic-demo-v1', clock=lambda: now[0])
    next_workflows.register(PortfolioDriver(fresh, old.dependencies, artifact_resolver=restored_router.artifact_resolver))
    restored = FinancialMASDispatcher(sessions, next_workflows, d.tools,
        execution_profile='synthetic-demo-v1', clock=lambda: now[0])
    assert asyncio.run(restored.start(pair.portfolio_run_id)).status == 'completed'
    assert completed_artifact(restored, pair.portfolio_run_id)['status'] == 'feasible'
    assert restored.snapshot(pair.portfolio_run_id)['budget']['rounds'] == 2
    assert all(len(p.calls) == 1 for p in fresh.values())
    assert d.relations(pair.portfolio_run_id) == before_relations
    assert sum(d.snapshot(r)['budget']['hops'] for r in (pair.market_run_id, pair.portfolio_run_id)) == before_hops


def test_failed_real_market_budget_keeps_portfolio_completion(assembly):
    d, router, _, _, _ = assembly
    pair = router.create(inputs(market_budget=RunBudget(max_model_calls=1)))
    asyncio.run(router.advance(pair))
    assert d.snapshot(pair.market_run_id)['status'] == 'failed'
    assert d.snapshot(pair.market_run_id)['error_code'] == 'budget_exhausted'
    assert completed_artifact(d, pair.portfolio_run_id)['status'] == 'feasible'
    assert any(r['relation_type'] == 'cross_admitted' and r['envelope']['message_type'] == 'SYSTEM_UNAVAILABLE'
        for r in d.relations(pair.portfolio_run_id))


def test_peer_timeout_does_not_wait_or_abort_portfolio(assembly):
    _, _, _, _, make = assembly
    class SlowProvider:
        async def complete(self, messages, *, request_id=None):
            await asyncio.sleep(10)
    d, router = make(market_provider=SlowProvider())
    pair = router.create(inputs())
    asyncio.run(router.advance(pair, max_deliveries=1, peer_timeout=.2))
    # Give the independent actual Portfolio driver a normal delivery budget.
    asyncio.run(d.start(pair.portfolio_run_id))
    assert completed_artifact(d, pair.portfolio_run_id)['status'] == 'feasible'
    assert d.snapshot(pair.market_run_id)['status'] != 'completed'
    assert d.snapshot(pair.market_run_id)['execution_profile'] == 'configured-test-synthetic-cross-v1'


def test_parallel_real_drivers_cancel_market_without_cancelling_portfolio(assembly):
    _, _, _, _, make = assembly
    entered = asyncio.Event()
    class WaitingProvider:
        async def complete(self, messages, *, request_id=None):
            entered.set()
            await asyncio.sleep(10)
    d, router = make(market_provider=WaitingProvider())
    pair = router.create(inputs())
    async def scenario():
        market = asyncio.create_task(d.start(pair.market_run_id))
        portfolio = asyncio.create_task(d.start(pair.portfolio_run_id))
        await asyncio.wait_for(entered.wait(), 2)
        d.cancel(pair.market_run_id, d.snapshot(pair.market_run_id)['version'])
        await portfolio
        market.cancel()
        await asyncio.gather(market, return_exceptions=True)
    asyncio.run(scenario())
    assert d.snapshot(pair.market_run_id)['status'] == 'cancelled'
    assert completed_artifact(d, pair.portfolio_run_id)['status'] == 'feasible'


def test_concurrent_further_requests_have_only_one_authorized_delivery(assembly):
    d, router, _, _, _ = assembly
    pair, _ = prepare(d, router)
    def request(key):
        try:
            return router.request_further_evidence(pair.portfolio_run_id, inputs().market,
                idempotency_key=key, mode='auto')
        except (FinancialConflict, BudgetExhausted):
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        requests = list(pool.map(request, ['race-a', 'race-b']))
    admitted = [r for r in requests if r is not None]
    assert len(admitted) == 1
    asyncio.run(router.advance(pair))
    assert completed_artifact(d, admitted[0]['target_run_id'])['numeric_facts']
    assert d.snapshot(pair.portfolio_run_id)['budget']['followups'] == 1


def test_diagnostic_ready_is_never_authorization(assembly):
    d, router, _, _, _ = assembly
    pair = router.create(inputs())
    asyncio.run(d.start(pair.market_run_id))
    source, target = d.snapshot(pair.market_run_id), d.snapshot(pair.portfolio_run_id)
    from agent.shared import ArtifactRef
    envelope = router._envelope(source, target, 'diagnostic-only', 'MARKET_EVIDENCE_READY',
        ref=ArtifactRef(artifact_id=source['checkpoint']['artifact_ids'][0]))
    d.link_runs(pair.market_run_id, pair.portfolio_run_id, version=source['version'],
        relation_type='diagnostic', idempotency_key='diagnostic-only', envelope=envelope)
    assert router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio) is None


def test_receiver_cancel_wins_first_selection_cas(assembly):
    d, router, _, _, _ = assembly
    pair, _ = prepare(d, router)
    def cancellation_during_scope(snapshot_id):
        d.cancel(pair.portfolio_run_id, d.snapshot(pair.portfolio_run_id)['version'])
        return demo_snapshot_loader(snapshot_id)
    router.snapshot_loader = cancellation_during_scope
    with pytest.raises(FinancialConflict):
        router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio)
    assert d.snapshot(pair.portfolio_run_id)['status'] == 'cancelled'
    assert not any(r['relation_type'] == 'artifact_selection' for r in d.relations(pair.portfolio_run_id))
    assert router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio) is None


def test_expiry_at_selection_commit_rejects_without_receipt(assembly, monkeypatch):
    d, router, _, now, _ = assembly
    pair, _ = prepare(d, router)
    original = d.link_runs
    def expire_before_transaction(*args, **kwargs):
        now[0] += timedelta(seconds=31)
        return original(*args, **kwargs)
    monkeypatch.setattr(d, 'link_runs', expire_before_transaction)
    with pytest.raises(ValueError):
        router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio)
    assert not any(r['relation_type'] == 'artifact_selection' for r in d.relations(pair.portfolio_run_id))


def test_new_receiver_cannot_reuse_expired_selected_context(assembly):
    d, router, _, now, _ = assembly
    pair, relation = prepare(d, router)
    assert router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio)
    now[0] += timedelta(seconds=31)
    receiver = d.create('c', inputs().portfolio, idempotency_key='new-independent-receiver',
        mode='auto', correlation_id=pair.correlation_id)
    assert router.artifact_resolver(receiver.id, 'c', inputs().portfolio) is None
    old = CrossMASEnvelope.model_validate(relation['envelope']).model_copy(
        update={'message_id': 'expired-for-new', 'idempotency_key': 'expired-for-new'})
    with pytest.raises(ValueError):
        router.admit(pair.market_run_id, receiver.id, old,
            expected_source_version=d.snapshot(pair.market_run_id)['version'],
            expected_target_version=d.snapshot(receiver.id)['version'])
    assert not d.relations(receiver.id)


def test_router_profile_guard_and_wrong_holdings_timepoint(assembly):
    d, router, sessions, _, make = assembly
    with pytest.raises(ValueError):
        CrossMASRouter(d, ArtifactStore(sessions), demo_snapshot_loader, execution_profile='other-profile')
    pair, _ = prepare(d, router)
    _, bad_router = make(loader=lambda _: demo_snapshot_loader(DEMO_SNAPSHOT_ID).model_copy(
        update={'effective_at': DEMO_AS_OF + timedelta(seconds=1)}))
    with pytest.raises(ValueError):
        bad_router.artifact_resolver(pair.portfolio_run_id, 'c', inputs().portfolio)


@pytest.mark.parametrize('workflow,blocked', [('market', 'portfolio_mas'), ('portfolio', 'market_mas')])
def test_fresh_process_domain_assembly_when_peer_import_disabled(tmp_path, workflow, blocked):
    script = '''
import builtins, asyncio
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'agent.BLOCKED' or name.startswith('agent.BLOCKED.'):
        raise ImportError('peer deliberately undeployed')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.base import Base
from db.models import Conversation
from agent.financial import build_financial_dispatcher
from agent.financial_demo import DEMO_AS_OF, DEMO_SNAPSHOT_ID, demo_snapshot_loader
from agent.integration import CrossMASRouter, CrossMASRequest
from agent.shared import ArtifactStore, MarketInvestigationRequest, PortfolioReviewRequest
engine = create_engine('sqlite:///DBPATH')
Base.metadata.create_all(engine)
sessions = sessionmaker(engine, expire_on_commit=False)
with sessions() as db:
    db.add(Conversation(id='c')); db.commit()
kind = 'KIND'
d = build_financial_dispatcher(sessions, enabled=(kind,))
r = CrossMASRouter(d, ArtifactStore(sessions), demo_snapshot_loader, execution_profile='synthetic-demo-v1')
request = CrossMASRequest(conversation_id='c', idempotency_key='isolated', mode='auto',
    market=MarketInvestigationRequest(symbol='MU', as_of=DEMO_AS_OF, sector_benchmark='SOXX'),
    portfolio=PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID, as_of=DEMO_AS_OF))
pair = r.create(request)
asyncio.run(r.advance(pair))
assert d.snapshot(pair.market_run_id or pair.portfolio_run_id)['status'] == 'completed'
print('isolated actual domain PASS')
'''.replace('BLOCKED', blocked).replace('KIND', 'market_investigation' if workflow == 'market' else 'portfolio_rebalance').replace('DBPATH', str(tmp_path / 'isolated.db').replace('\\', '/'))
    result = subprocess.run([sys.executable, '-c', script], env=os.environ.copy(),
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'isolated actual domain PASS' in result.stdout
