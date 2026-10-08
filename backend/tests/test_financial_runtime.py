"""Offline DB/provider gates for the domain-neutral financial runtime."""
import asyncio
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from db.base import Base
from db.models import Conversation, AgentRun, AgentEvent, FinancialRun, FinancialInvocation, FinancialArtifact, ToolCall, ToolResult
from agent.llm import ScriptedFakeModel
from agent.shared import *
from agent.tools.registry import ToolRegistry, ToolSpec

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeDriver:
    def __init__(self, kind, stop_after_first=False):
        self.kind = kind
        self.stop_after_first = stop_after_first
        self.specialists = SpecialistRegistry()
        self.providers = []
        for role in ('investigator', 'critic'):
            provider = ScriptedFakeModel([{'kind': 'result', 'payload': {'role': role, 'action': 'finding', 'summary': role + ' independent result'}}])
            self.providers.append(provider)
            self.specialists.register(SpecialistSpec(role, provider, 'role: ' + role, frozenset({'readonly'})))

    async def execute(self, ctx, state):
        for role in ('investigator', 'critic'):
            if any(result.role == role for result in state.results):
                continue
            result = await ctx.invoke(role, role + ':1', ctx.request)
            state.results.append(result)
            ctx.checkpoint(state)
            if self.stop_after_first:
                return None
        if self.kind == 'market_investigation':
            return MarketInvestigationArtifact(producing_run_id=ctx.run_id, symbol=ctx.request.symbol, as_of=ctx.request.as_of, status='partial', limitations=['offline fake evidence'])
        return PortfolioProposalArtifact(producing_run_id=ctx.run_id, snapshot_id=ctx.request.portfolio_snapshot_id, as_of=ctx.request.as_of, current_weights={'CASH': 1}, proposed_weights={}, constraint_check=ConstraintCheck(status='unknown', unknowns=['offline']), status='insufficient_data')


@pytest.fixture
def setup(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'runtime.db'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as s:
        s.add_all([Conversation(id='c1'), Conversation(id='c2')])
        s.commit()
    registry = WorkflowRegistry()
    market, portfolio = FakeDriver('market_investigation'), FakeDriver('portfolio_rebalance')
    registry.register(market)
    registry.register(portfolio)
    dispatcher = FinancialMASDispatcher(sessions, registry)
    yield dispatcher, sessions, market, portfolio
    engine.dispose()


def market_run(dispatcher, mode='auto', key='market', budget=None):
    return dispatcher.create('c1', MarketInvestigationRequest(symbol=' mu ', as_of=NOW), mode=mode, idempotency_key=key, budget=budget)


def test_independent_two_specialist_handoffs_and_duplicate(setup):
    d, sessions, market, portfolio = setup
    m = market_run(d)
    p = d.create('c1', PortfolioReviewRequest(portfolio_snapshot_id='saved-holdings', as_of=NOW), mode='auto', idempotency_key='portfolio')
    assert m.id != p.id
    assert asyncio.run(d.start(m.id)).status == 'completed'
    assert asyncio.run(d.start(p.id)).status == 'completed'
    completed_version = d.get_run(m.id).version
    assert asyncio.run(d.start(m.id)).version == completed_version
    assert market_run(d).id == m.id
    with sessions() as s:
        assert len(s.scalars(select(FinancialInvocation)).all()) == 4
        assert len(s.scalars(select(FinancialArtifact)).all()) == 2
        for run in (m, p):
            seqs = list(s.scalars(select(AgentEvent.seq).where(AgentEvent.run_id == run.id).order_by(AgentEvent.seq)))
            assert seqs == list(range(1, len(seqs) + 1))
    assert len(market.providers[0].calls) == len(market.providers[1].calls) == 1
    assert market.providers[0].calls[0][0]['content'] != market.providers[1].calls[0][0]['content']
    assert d.snapshot(m.id)['budget']['model_calls'] == 2
    ref = d.snapshot(m.id)['checkpoint']['artifact_ids'][0]
    store = ArtifactStore(sessions)
    assert store.get(ref, conversation_id='c1', as_of=NOW, symbols=['MU']).symbol == 'MU'
    with pytest.raises(KeyError):
        store.get(ref, conversation_id='c2')
    with pytest.raises(ValueError):
        store.get(ref, conversation_id='c1', as_of=NOW + timedelta(days=1))


def test_checkpoint_restart_does_not_repeat_persisted_specialist(setup):
    d, sessions, market, _ = setup
    market.stop_after_first = True
    run = market_run(d)
    assert asyncio.run(d.start(run.id)).status == 'executing'
    replacement = FakeDriver('market_investigation')
    registry = WorkflowRegistry()
    registry.register(replacement)
    restarted = FinancialMASDispatcher(sessions, registry)
    assert asyncio.run(restarted.start(run.id)).status == 'completed'
    assert replacement.providers[0].calls == []
    assert len(replacement.providers[1].calls) == 1
    assert restarted.snapshot(run.id)['budget']['model_calls'] == 2


@pytest.mark.parametrize('phase', ['queued', 'planning', 'waiting_user', 'executing', 'paused'])
def test_cancel_every_nonterminal(setup, phase):
    d, sessions, _, _ = setup
    run = market_run(d)
    with sessions() as s:
        s.get(AgentRun, run.id).status = phase
        s.commit()
    assert d.cancel(run.id, d.get_run(run.id).version).status == 'cancelled'
    assert asyncio.run(d.start(run.id)).status == 'cancelled'


@pytest.mark.parametrize('phase', ['queued', 'planning', 'waiting_user', 'executing'])
def test_pause_preserves_phase_and_stale_intervention(setup, phase):
    d, sessions, _, _ = setup
    run = market_run(d)
    with sessions() as s:
        s.get(AgentRun, run.id).status = phase
        s.commit()
    paused = d.pause(run.id, run.version)
    with pytest.raises(FinancialConflict):
        d.cancel(run.id, run.version)
    resumed = d.resume(run.id, paused.version)
    assert resumed.status == phase


def test_review_excludes_waiting_time_and_approval(setup):
    d, _, _, _ = setup
    now = [NOW]
    d.clock = lambda: now[0]
    run = market_run(d, mode='review')
    waiting = asyncio.run(d.start(run.id))
    assert waiting.status == 'waiting_user'
    now[0] += timedelta(days=5)
    assert d.snapshot(run.id)['active_seconds'] == 0
    approved = d.approve(run.id, waiting.version)
    assert approved.status == 'executing'
    assert asyncio.run(d.start(run.id)).status == 'completed'


def test_budget_reservations_count_failures_and_rounds(setup):
    d, sessions, market, _ = setup
    run = market_run(d, budget=RunBudget(max_model_calls=1))
    result = asyncio.run(d.start(run.id))
    assert result.status == 'failed' and result.error_code == 'budget_exhausted'
    assert d.snapshot(run.id)['budget']['model_calls'] == 1
    assert len(market.providers[1].calls) == 0
    child = d.retry(run.id, result.version, idempotency_key='retry1')
    assert child.id != run.id and child.parent_run_id == run.id
    assert d.retry(run.id, result.version, idempotency_key='retry1').id == child.id
    with pytest.raises(FinancialConflict):
        d.retry(run.id, result.version, idempotency_key='market')
    assert d.get_run(run.id).parent_run_id is None


def test_worker_fenced_after_cancel_during_external_call(setup):
    d, sessions, market, _ = setup
    class CancellingProvider:
        async def complete(self, messages, *, request_id=None):
            from agent.llm import ModelResponse
            current = d.get_run(run.id)
            d.cancel(run.id, current.version)
            return ModelResponse(kind='result', payload={'role': 'investigator', 'action': 'finding', 'summary': 'stale'})
    market.specialists._roles['investigator'] = SpecialistSpec('investigator', CancellingProvider(), 'investigator')
    run = market_run(d)
    assert asyncio.run(d.start(run.id)).status == 'cancelled'
    with sessions() as s:
        invocation = s.scalar(select(FinancialInvocation))
        assert invocation.output is None
        assert s.scalar(select(FinancialArtifact)) is None


def test_simultaneous_claims_only_one_executes(setup):
    d, sessions, market, _ = setup
    run = market_run(d)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: asyncio.run(d.start(run.id)), range(2)))
    assert d.get_run(run.id).status == 'completed'
    assert sum(len(p.calls) for p in market.providers) == 2


def test_crash_lease_recovery_uses_cached_invocation(setup):
    d, sessions, market, _ = setup
    run = market_run(d)
    token = 'dead-worker'
    with d._mutation(run.id) as (_, row, meta):
        row.status = 'executing'
        meta.claim_token = token
        meta.lease_until = NOW + timedelta(seconds=125)
        meta.active_since = NOW
    d.clock = lambda: NOW
    ctx = RuntimeContext(d, run.id, token, market)
    asyncio.run(ctx.invoke('investigator', 'investigator:1', ctx.request))
    # Restart after abandoned lease, within active budget (short test lease).
    with sessions() as s:
        s.get(FinancialRun, run.id).lease_until = NOW - timedelta(seconds=1)
        s.commit()
    assert asyncio.run(d.start(run.id)).status == 'completed'
    assert len(market.providers[0].calls) == 1


def test_active_deadline_persists_and_pause_excludes_time(setup):
    d, sessions, market, _ = setup
    now = [NOW]
    d.clock = lambda: now[0]
    run = market_run(d, budget=RunBudget(max_active_seconds=10))
    with d._mutation(run.id) as (_, row, meta):
        row.status = 'executing'
        meta.active_since = NOW
    now[0] += timedelta(seconds=4)
    paused = d.pause(run.id, d.get_run(run.id).version)
    now[0] += timedelta(days=1)
    assert d.snapshot(run.id)['active_seconds'] == 4
    d.resume(run.id, paused.version)
    with sessions() as s:
        meta = s.get(FinancialRun, run.id)
        meta.active_since = now[0] - timedelta(seconds=7)
        s.commit()
    assert asyncio.run(d.start(run.id)).error_code == 'budget_exhausted'
    assert not market.providers[0].calls


def test_unfinished_delivery_does_not_reset_active_deadline(setup):
    d, _, market, _ = setup
    now = [NOW]
    d.clock = lambda: now[0]
    market.stop_after_first = True
    run = market_run(d, budget=RunBudget(max_active_seconds=10))
    assert asyncio.run(d.start(run.id)).status == 'executing'
    now[0] += timedelta(seconds=11)
    assert asyncio.run(d.start(run.id)).error_code == 'budget_exhausted'


def test_readonly_tool_permissions_audit_and_cache(setup):
    d, sessions, market, _ = setup
    class ToolInput(FinancialModel):
        value: int
    calls = []
    d.tools.register(ToolSpec('readonly', '1', 'read only', ToolInput, ToolInput, lambda data: calls.append(data.value) or data))
    d.tools.register(ToolSpec('write', '1', 'write', ToolInput, ToolInput, lambda data: data, side_effect=True, read_only=False))
    async def execute(ctx, state):
        first = await ctx.tool('investigator', 'tool1', 'readonly', ToolInput(value=3))
        second = await ctx.tool('investigator', 'tool1', 'readonly', ToolInput(value=3))
        assert first == second
        with pytest.raises(FinancialConflict):
            await ctx.tool('investigator', 'tool1', 'readonly', ToolInput(value=4))
        with pytest.raises(PermissionError):
            await ctx.tool('investigator', 'write', 'write', ToolInput(value=3))
        ctx.consume_budget('rounds')
        return MarketInvestigationArtifact(producing_run_id=ctx.run_id, symbol='MU', as_of=NOW, status='partial')
    market.execute = execute
    run = market_run(d)
    assert asyncio.run(d.start(run.id)).status == 'completed'
    assert calls == [3]
    with sessions() as s:
        assert len(s.scalars(select(ToolCall)).all()) == 1
        assert len(s.scalars(select(ToolResult)).all()) == 1
    assert d.snapshot(run.id)['budget']['tool_calls'] == 1


def test_invalid_financial_contracts():
    with pytest.raises(ValueError):
        MarketInvestigationRequest(symbol=' ', as_of=NOW)
    with pytest.raises(ValueError):
        MarketInvestigationRequest(symbol='MU', as_of=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        AllocationConstraints(max_weight_by_symbol={'MU': float('nan')})
    with pytest.raises(ValueError):
        RunBudget(max_model_calls=17)
    with pytest.raises(ValueError):
        ConstraintCheck(status='pass', unknowns=['sector'])


@pytest.mark.parametrize('field', ['max_weight_by_symbol', 'max_sector_weight'])
def test_constraint_key_collisions_and_blank_names_rejected(field):
    with pytest.raises(ValueError):
        AllocationConstraints(**{field: {'A': 0.1, ' a ': 1}})
    with pytest.raises(ValueError):
        AllocationConstraints(**{field: {' ': 0.1}})
    assert getattr(AllocationConstraints(**{field: {' a ': 0.1}}), field) == {'A': 0.1}


def test_weight_key_collisions_rejected_before_discarding_values():
    with pytest.raises(ValueError):
        SpecialistResult(role='opportunity', action='proposal', summary='test', proposed_weights={'MU': 0.1, 'mu': 0.8})
    with pytest.raises(ValueError):
        PortfolioState(proposed_weights={' ': 0.1})
    with pytest.raises(ValueError):
        PortfolioProposalArtifact(producing_run_id='run', snapshot_id='snapshot', as_of=NOW,
            current_weights={'CASH': 0.1, 'cash': 0.9}, proposed_weights={},
            constraint_check=ConstraintCheck(status='unknown'), status='insufficient_data')


def test_expired_is_terminal(setup):
    d, sessions, _, _ = setup
    run = market_run(d)
    with sessions() as s:
        s.get(AgentRun, run.id).status = 'expired'
        s.commit()
    for action in (d.cancel, d.pause, d.resume, d.approve):
        with pytest.raises(FinancialConflict):
            action(run.id, run.version)
    assert asyncio.run(d.start(run.id)).version == run.version
    child = d.retry(run.id, run.version, idempotency_key='retry-expired')
    assert child.id != run.id


def test_model_failure_attempt_is_reserved_before_call(setup):
    d, _, market, _ = setup
    class Failure:
        async def complete(self, messages, *, request_id=None):
            assert d.snapshot(run.id)['budget']['model_calls'] == 1
            raise RuntimeError('provider private diagnostic')
    market.specialists._roles['investigator'] = SpecialistSpec('investigator', Failure(), 'role')
    run = market_run(d)
    result = asyncio.run(d.start(run.id))
    assert result.status == 'failed'
    assert d.snapshot(run.id)['budget']['model_calls'] == 1
    assert 'private' not in str(d.snapshot(run.id))


@pytest.mark.parametrize('counter', ['rounds', 'hops', 'followups'])
def test_coordination_budget_exhaustion(setup, counter):
    d, _, market, _ = setup
    async def execute(ctx, state):
        maximum = getattr(RunBudget(), 'max_' + counter)
        for _ in range(maximum + 1):
            ctx.consume_budget(counter)
    market.execute = execute
    run = market_run(d)
    assert asyncio.run(d.start(run.id)).error_code == 'budget_exhausted'
    assert d.snapshot(run.id)['budget'][counter] == getattr(RunBudget(), 'max_' + counter)


def test_relation_cas_scope_timepoint_kind_and_idempotency(setup):
    d, _, _, _ = setup
    d.clock = lambda: NOW
    request = MarketInvestigationRequest(symbol='MU', as_of=NOW)
    m = d.create('c1', request, mode='auto', idempotency_key='market-link', correlation_id='corr')
    p = d.create('c1', PortfolioReviewRequest(portfolio_snapshot_id='holdings', as_of=NOW), mode='auto', idempotency_key='portfolio-link', correlation_id='corr')
    envelope = CrossMASEnvelope(message_id='message', origin_mas='market_investigation', target_mas='portfolio_rebalance', run_id=m.id, correlation_id='corr', message_type='MARKET_EVIDENCE_REQUEST', as_of=NOW, created_at=NOW, deadline_at=NOW + timedelta(seconds=30), idempotency_key='relation', budget=RunBudget())
    linked = d.link_runs(m.id, p.id, version=m.version, relation_type='cross_request', idempotency_key='relation', envelope=envelope)
    assert linked['relation_id'] == d.relations(p.id)[0]['relation_id']
    with pytest.raises(FinancialConflict):
        d.link_runs(m.id, p.id, version=m.version, relation_type='cross_request', idempotency_key='relation', envelope=envelope)
    current = d.get_run(m.id).version
    assert d.link_runs(m.id, p.id, version=current, relation_type='cross_request', idempotency_key='relation', envelope=envelope) == linked
    assert d.get_run(m.id).version == current
    with pytest.raises(FinancialConflict):
        d.link_runs(m.id, p.id, version=current, relation_type='changed', idempotency_key='relation', envelope=envelope)
    other = d.create('c2', PortfolioReviewRequest(portfolio_snapshot_id='holdings', as_of=NOW), mode='auto', idempotency_key='other', correlation_id='corr')
    with pytest.raises(ValueError):
        d.link_runs(m.id, other.id, version=current, relation_type='combined', idempotency_key='bad-scope')
    with pytest.raises(ValueError):
        d.link_runs(m.id, m.id, version=current, relation_type='combined', idempotency_key='self')
    expired = envelope.model_copy(update={'idempotency_key': 'expired', 'deadline_at': NOW - timedelta(seconds=1), 'created_at': NOW - timedelta(seconds=5)})
    with pytest.raises(ValueError):
        d.link_runs(m.id, p.id, version=current, relation_type='cross_request', idempotency_key='expired', envelope=expired)


def test_relation_artifact_ref_preserves_immutable_scope(setup):
    d, _, _, _ = setup
    d.clock = lambda: NOW
    m = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW), mode='auto', idempotency_key='market-ref', correlation_id='corr')
    p = d.create('c1', PortfolioReviewRequest(portfolio_snapshot_id='holdings', as_of=NOW), mode='auto', idempotency_key='portfolio-ref', correlation_id='corr')
    asyncio.run(d.start(m.id))
    artifact_id = d.snapshot(m.id)['checkpoint']['artifact_ids'][0]
    envelope = CrossMASEnvelope(message_id='message', origin_mas='market_investigation', target_mas='portfolio_rebalance', run_id=m.id, correlation_id='corr', message_type='MARKET_EVIDENCE_READY', payload_ref=ArtifactRef(artifact_id=artifact_id), as_of=NOW, created_at=NOW, deadline_at=NOW + timedelta(seconds=30), idempotency_key='ready', budget=RunBudget())
    linked = d.link_runs(m.id, p.id, version=d.get_run(m.id).version, relation_type='evidence_transfer', idempotency_key='ready', envelope=envelope)
    assert linked['envelope']['payload_ref']['artifact_id'] == artifact_id
    bad = envelope.model_copy(update={'idempotency_key': 'bad-ref', 'payload_ref': ArtifactRef(artifact_id='missing')})
    with pytest.raises(ValueError):
        d.link_runs(m.id, p.id, version=d.get_run(m.id).version, relation_type='evidence_transfer', idempotency_key='bad-ref', envelope=bad)


def test_lease_renewal_keeps_long_call_owned(setup):
    d, _, market, _ = setup
    d.lease_seconds = 0.5
    class SlowProvider:
        async def complete(self, messages, *, request_id=None):
            from agent.llm import ModelResponse
            await asyncio.sleep(1.1)
            return ModelResponse(kind='result', payload={'role': 'investigator', 'action': 'finding', 'summary': 'renewed'})
    market.specialists._roles['investigator'] = SpecialistSpec('investigator', SlowProvider(), 'role')
    run = market_run(d)
    assert asyncio.run(d.start(run.id)).status == 'completed'


def test_immutable_artifact_rejects_replacement(setup):
    d, sessions, _, _ = setup
    run = market_run(d)
    asyncio.run(d.start(run.id))
    artifact_id = d.snapshot(run.id)['checkpoint']['artifact_ids'][0]
    artifact = ArtifactStore(sessions).get(artifact_id, conversation_id='c1')
    with sessions() as session:
        row = session.get(AgentRun, run.id)
        meta = session.get(FinancialRun, run.id)
        assert ArtifactStore.put_in_transaction(session, row, meta, 'final', artifact).id == artifact_id
        with pytest.raises(ValueError):
            ArtifactStore.put_in_transaction(session, row, meta, 'final', artifact.model_copy(update={'limitations': ['changed']}))
    assert ArtifactStore(sessions).get(artifact_id, conversation_id='c1') == artifact
