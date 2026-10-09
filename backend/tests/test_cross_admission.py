"""ADR-0003 local transaction, membership and concurrent admission evidence."""
import asyncio
import threading
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from db.models import AgentRun, AgentEvent, FinancialRun, FinancialArtifact, Conversation
from db.models.financial_mas import FinancialRelation
from agent.shared import *
from backend.tests.test_financial_runtime import setup, NOW


def pair(d, *, budget=None):
    d.clock = lambda: NOW
    m = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
                 idempotency_key='m', correlation_id='corr', budget=budget, mode='auto')
    p = d.create('c1', PortfolioReviewRequest(portfolio_snapshot_id='holdings', as_of=NOW),
                 idempotency_key='p', correlation_id='corr', budget=budget, mode='auto')
    return m, p


def message(d, source, target, key='msg', kind='MARKET_EVIDENCE_REQUEST', **changes):
    source_meta, target_meta = d.snapshot(source.id), d.snapshot(target.id)
    values = dict(message_id=key, origin_mas=source_meta['mas_kind'],
        target_mas=target_meta['mas_kind'], run_id=source.id, correlation_id='corr',
        message_type=kind, as_of=NOW, created_at=NOW,
        deadline_at=NOW + timedelta(seconds=30), idempotency_key=key,
        budget=RunBudget(max_hops=min(source_meta['budget']['max_hops'], target_meta['budget']['max_hops']),
                         max_followups=min(source_meta['budget']['max_followups'], target_meta['budget']['max_followups'])))
    values.update(changes)
    return CrossMASEnvelope(**values)


def admit(d, source, target, env, **versions):
    return d.admit_cross_message(source.id, target.id,
        expected_source_version=versions.get('source_version', d.get_run(source.id).version),
        expected_target_version=versions.get('target_version', d.get_run(target.id).version), envelope=env)


def state(d, sessions):
    with sessions() as s:
        ids = list(s.scalars(select(FinancialRun.run_id)))
        relations = [(r.id, r.envelope) for r in s.scalars(select(FinancialRelation))]
        events = [(e.run_id, e.seq, e.event_type, e.payload) for e in s.scalars(select(AgentEvent).order_by(AgentEvent.run_id, AgentEvent.seq))]
    return sorted((i, d.snapshot(i)) for i in ids), relations, events


def artifact(d, market):
    async def produce(ctx, state):
        return MarketInvestigationArtifact(producing_run_id=ctx.run_id, symbol=ctx.request.symbol,
            as_of=ctx.request.as_of, status='partial', limitations=['offline'])
    d.drivers.get('market_investigation').execute = produce
    assert asyncio.run(d.start(market.id)).status == 'completed'
    return ArtifactRef(artifact_id=d.snapshot(market.id)['checkpoint']['artifact_ids'][0])


@pytest.mark.parametrize('recipient_terminal', ['completed', 'cancelled'])
def test_one_followup_reverse_reply_and_exact_historical_replay(setup, recipient_terminal):
    d, sessions, _, _ = setup
    m, p = pair(d)
    ready = message(d, m, p, 'initial', 'MARKET_EVIDENCE_READY', payload_ref=artifact(d, m))
    admit(d, m, p, ready)
    followup = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
        idempotency_key='followup', correlation_id='corr', mode='auto')
    request = message(d, p, followup, 'request')
    admit(d, p, followup, request)
    assert d.snapshot(m.id)['budget']['hops'] == 1
    assert d.snapshot(p.id)['budget']['hops'] == 1
    assert d.snapshot(p.id)['budget']['followups'] == 1
    response = message(d, followup, p, 'response', 'MARKET_EVIDENCE_READY',
        causation_id='request', payload_ref=artifact(d, followup))
    result = admit(d, followup, p, response)
    assert d.snapshot(followup.id)['budget']['hops'] == 0
    if recipient_terminal == 'completed':
        assert asyncio.run(d.start(p.id)).status == 'completed'
    else:
        d.cancel(p.id, d.get_run(p.id).version)
    d.clock = lambda: NOW + timedelta(days=1)
    before = state(d, sessions)
    assert admit(d, followup, p, response, source_version=1, target_version=1) == result
    assert state(d, sessions) == before
    for run in (m, p, followup):
        with sessions() as s:
            seqs = list(s.scalars(select(AgentEvent.seq).where(AgentEvent.run_id == run.id).order_by(AgentEvent.seq)))
            assert seqs == list(range(1, len(seqs) + 1))


@pytest.mark.parametrize('counter,ceiling', [('hops', 0), ('followups', 0), ('hops', 1)])
def test_lowered_zero_one_budgets_and_full_rollback(setup, counter, ceiling):
    d, sessions, _, _ = setup
    m, p = pair(d, budget=RunBudget(**{'max_' + counter: ceiling}))
    if ceiling == 1:
        # One charged transfer exhausts a correlation-wide hop, even though
        # the request sender has not itself used a hop.
        admit(d, m, p, message(d, m, p, 'ready', 'MARKET_EVIDENCE_READY', payload_ref=artifact(d, m)))
        m = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
            idempotency_key='m2', correlation_id='corr', mode='auto', budget=RunBudget(max_hops=1))
    before = state(d, sessions)
    with pytest.raises(BudgetExhausted):
        admit(d, p, m, message(d, p, m))
    assert state(d, sessions) == before


@pytest.mark.parametrize('change', [
    {'message_id': ' '}, {'run_id': 'other'}, {'correlation_id': 'other'},
    {'as_of': NOW + timedelta(days=1)}, {'created_at': NOW + timedelta(seconds=1)},
    {'created_at': NOW - timedelta(seconds=10), 'deadline_at': NOW},
    {'message_type': 'PORTFOLIO_IMPACT_REQUEST'}, {'causation_id': 'missing'},
    {'payload_ref': ArtifactRef(artifact_id='missing')},
    {'budget': RunBudget(hops=3)},
])
def test_forged_requests_are_atomic(setup, change):
    d, sessions, _, _ = setup
    m, p = pair(d)
    env = message(d, p, m, **change)
    before = state(d, sessions)
    with pytest.raises((ValueError, FinancialConflict)):
        admit(d, p, m, env)
    assert state(d, sessions) == before


def test_reserved_legacy_type_duplicate_ids_key_and_changed_payload(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    env = message(d, p, m, kind='SYSTEM_UNAVAILABLE')
    with pytest.raises(ValueError):
        d.link_runs(p.id, m.id, version=p.version, relation_type='cross_admitted', idempotency_key=env.idempotency_key, envelope=env)
    d.link_runs(p.id, m.id, version=p.version, relation_type='diagnostic', idempotency_key=env.idempotency_key, envelope=env)
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        admit(d, p, m, env)
    duplicate = env.model_copy(update={'idempotency_key': 'new-key'})
    for method in ('admit', 'legacy'):
        with pytest.raises(FinancialConflict):
            if method == 'admit':
                admit(d, p, m, duplicate)
            else:
                d.link_runs(p.id, m.id, version=d.get_run(p.id).version, relation_type='diagnostic', idempotency_key='new-key', envelope=duplicate)
    assert state(d, sessions) == before
    admitted = message(d, p, m, 'admitted', kind='SYSTEM_UNAVAILABLE')
    admit(d, p, m, admitted)
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        admit(d, p, m, admitted.model_copy(update={'target_agent': 'changed'}))
    assert state(d, sessions) == before


@pytest.mark.parametrize('change', [
    {'created_at': NOW - timedelta(seconds=1)},
    {'deadline_at': NOW + timedelta(seconds=31)},
    {'causation_id': 'diagnostic'}, {'causation_id': 'transfer'},
])
def test_response_causation_time_and_type_guards(setup, change):
    d, sessions, _, _ = setup
    m, p = pair(d)
    diagnostic = message(d, p, m, 'diagnostic', 'SYSTEM_UNAVAILABLE')
    d.link_runs(p.id, m.id, version=p.version, relation_type='diagnostic', idempotency_key='diagnostic', envelope=diagnostic)
    admit(d, p, m, message(d, p, m, 'request'))
    ref = artifact(d, m)
    admit(d, m, p, message(d, m, p, 'transfer', 'MARKET_EVIDENCE_READY', payload_ref=ref))
    env = message(d, m, p, 'response', 'MARKET_EVIDENCE_READY', causation_id='request', payload_ref=ref)
    before = state(d, sessions)
    with pytest.raises((ValueError, FinancialConflict)):
        admit(d, m, p, env.model_copy(update=change))
    assert state(d, sessions) == before


def test_wrong_reverse_endpoints_and_terminal_recipient(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    admit(d, p, m, message(d, p, m, 'request'))
    m2 = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW), idempotency_key='m2', correlation_id='corr')
    before = state(d, sessions)
    with pytest.raises(ValueError):
        admit(d, m2, p, message(d, m2, p, 'response', 'SYSTEM_UNAVAILABLE', causation_id='request'))
    assert state(d, sessions) == before
    d.cancel(p.id, d.get_run(p.id).version)
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        admit(d, m, p, message(d, m, p, 'unavailable', 'SYSTEM_UNAVAILABLE'))
    assert state(d, sessions) == before


def race(functions):
    barrier = threading.Barrier(len(functions))
    def call(fn):
        barrier.wait(timeout=5)
        try:
            return fn()
        except (FinancialConflict, BudgetExhausted, ValueError) as exc:
            return exc
    with ThreadPoolExecutor(len(functions)) as pool:
        return list(pool.map(call, functions))


def test_competing_admissions_and_ready_unavailable_resolution_race(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    versions = dict(source_version=p.version, target_version=m.version)
    results = race([lambda: admit(d, p, m, message(d, p, m, 'a'), **versions),
                    lambda: admit(d, p, m, message(d, p, m, 'b'), **versions)])
    assert sum(isinstance(r, dict) for r in results) == 1
    request_id = next(r['envelope']['message_id'] for r in results if isinstance(r, dict))
    ref = artifact(d, m)
    versions = dict(source_version=d.get_run(m.id).version, target_version=d.get_run(p.id).version)
    ready = message(d, m, p, 'ready', 'MARKET_EVIDENCE_READY', payload_ref=ref, causation_id=request_id)
    unavailable = message(d, m, p, 'unavailable', 'SYSTEM_UNAVAILABLE', causation_id=request_id)
    results = race([lambda: admit(d, m, p, ready, **versions), lambda: admit(d, m, p, unavailable, **versions)])
    assert sum(isinstance(r, dict) for r in results) == 1
    before = state(d, sessions)
    losing = unavailable if any(isinstance(r, dict) and r['envelope']['message_type'] == 'MARKET_EVIDENCE_READY' for r in results) else ready
    with pytest.raises(FinancialConflict):
        admit(d, m, p, losing)
    assert state(d, sessions) == before


@pytest.mark.parametrize('counter', ['hops', 'followups'])
def test_third_member_reservation_races_admission(setup, counter):
    d, sessions, market, _ = setup
    m, p = pair(d, budget=RunBudget(max_hops=1))
    third = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
        idempotency_key='third', correlation_id='corr', mode='auto')
    with d._mutation(third.id) as (_, run, meta):
        run.status = 'executing'
        meta.claim_token = 'claim'
        meta.lease_until = NOW + timedelta(seconds=30)
        meta.active_since = NOW
    ctx = RuntimeContext(d, third.id, 'claim', market)
    def consume():
        ctx.consume_budget(counter)
        return {'reserved': True}
    results = race([consume, lambda: admit(d, p, m, message(d, p, m))])
    assert sum(isinstance(r, dict) for r in results) == 1
    assert sum(d.snapshot(r.id)['budget'][counter] for r in (m, p, third)) == 1


@pytest.mark.parametrize('retry_join', [False, True])
def test_lower_ceiling_membership_prevents_work_but_preserves_resolution(setup, retry_join):
    d, sessions, _, _ = setup
    m, p = pair(d)
    request = message(d, p, m, 'request')
    admit(d, p, m, request)
    low = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
        idempotency_key='low', correlation_id='corr', budget=RunBudget(max_hops=0, max_followups=0))
    if retry_join:
        # A retry keeps its parent's correlation and lowered ceilings.
        low = d.cancel(low.id, d.get_run(low.id).version)
        child = d.retry(low.id, low.version, idempotency_key='retry-low')
        assert d.snapshot(child.id)['correlation_id'] == 'corr'
        assert d.snapshot(child.id)['budget']['max_hops'] == 0
    before = state(d, sessions)
    with pytest.raises(BudgetExhausted):
        admit(d, p, m, message(d, p, m, 'more'))
    assert state(d, sessions) == before
    response = message(d, m, p, 'resolution', 'SYSTEM_UNAVAILABLE', causation_id='request')
    admit(d, m, p, response)
    assert d.snapshot(p.id)['budget']['hops'] == 1
    assert d.snapshot(m.id)['budget']['hops'] == 0


def test_preexisting_outstanding_cycle_and_terminal_edge_filter(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    # Malformed/future graph is seeded solely to verify the generic cycle guard.
    old = message(d, m, p, 'old')
    with sessions() as s:
        s.add(FinancialRelation(id='old', conversation_id='c1', source_run_id=m.id,
            target_run_id=p.id, correlation_id='corr', relation_type='cross_admitted',
            idempotency_key='old', envelope=old.model_dump(mode='json')))
        s.commit()
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        admit(d, p, m, message(d, p, m))
    assert state(d, sessions) == before


def test_cancellation_race_and_independent_version_rollback(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    results = race([lambda: admit(d, p, m, message(d, p, m), source_version=p.version, target_version=m.version),
                    lambda: d.cancel(m.id, m.version)])
    assert sum(not isinstance(r, Exception) for r in results) == 1
    # A stale second CAS must roll back the first CAS irrespective of ID sort.
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        admit(d, p, m, message(d, p, m, 'stale', 'SYSTEM_UNAVAILABLE'), source_version=0)
    assert state(d, sessions) == before


def test_conversation_lock_sql_and_timestamp_preservation(setup):
    d, sessions, _, _ = setup
    with sessions() as s:
        before = s.get(Conversation, 'c1').updated_at
    pair(d)
    with sessions() as s:
        assert s.get(Conversation, 'c1').updated_at == before
    class Capture:
        def execute(self, statement, **kwargs):
            self.sql = str(statement.compile(dialect=postgresql.dialect()))
            return SimpleNamespace(rowcount=1)
    capture = Capture()
    d._lock_conversation(capture, 'c1')
    assert 'UPDATE conversations SET updated_at=conversations.updated_at' in capture.sql


def test_opposing_admissions_share_canonical_lock(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    request = message(d, p, m, 'request')
    diagnostic = message(d, m, p, 'diagnostic', 'SYSTEM_UNAVAILABLE')
    results = race([
        lambda: admit(d, p, m, request, source_version=p.version, target_version=m.version),
        lambda: admit(d, m, p, diagnostic, source_version=m.version, target_version=p.version)])
    assert sum(isinstance(r, dict) for r in results) == 1
    assert sum(isinstance(r, FinancialConflict) for r in results) == 1


@pytest.mark.parametrize('first_writer', ['join', 'admission'])
def test_join_and_admission_are_ordered_at_membership_commit(setup, monkeypatch, first_writer):
    d, sessions, _, _ = setup
    m, p = pair(d)
    request = message(d, p, m, 'request')
    locked, attempted, release = threading.Event(), threading.Event(), threading.Event()
    original = d._lock_conversation
    leader_id = []
    def lock(session, conversation_id):
        if threading.get_ident() != leader_id[0]:
            attempted.set()
        original(session, conversation_id)
        if threading.get_ident() == leader_id[0]:
            locked.set()
            assert release.wait(timeout=5)
    monkeypatch.setattr(d, '_lock_conversation', lock)
    def join():
        return d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
            idempotency_key='joining', correlation_id='corr', budget=RunBudget(max_hops=0))
    def charge():
        try:
            return admit(d, p, m, request)
        except BudgetExhausted as exc:
            return exc
    first, second = (join, charge) if first_writer == 'join' else (charge, join)
    def lead():
        leader_id.append(threading.get_ident())
        return first()
    with ThreadPoolExecutor(2) as pool:
        leading = pool.submit(lead)
        assert locked.wait(timeout=5)
        trailing = pool.submit(second)
        assert attempted.wait(timeout=5)
        release.set()
        a, b = leading.result(timeout=5), trailing.result(timeout=5)
    charge_result = b if first_writer == 'join' else a
    assert isinstance(charge_result, BudgetExhausted) == (first_writer == 'join')
    assert d.snapshot(p.id)['budget']['hops'] == (0 if first_writer == 'join' else 1)
    with pytest.raises(BudgetExhausted):
        admit(d, p, m, message(d, p, m, 'later'))


def test_legacy_and_admission_duplicate_ids_race(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    legacy = message(d, p, m, 'legacy', 'SYSTEM_UNAVAILABLE', message_id='shared-id')
    admitted = message(d, m, p, 'admitted', 'SYSTEM_UNAVAILABLE', message_id='shared-id')
    results = race([
        lambda: d.link_runs(p.id, m.id, version=p.version, relation_type='diagnostic',
                            idempotency_key='legacy', envelope=legacy),
        lambda: admit(d, m, p, admitted, source_version=m.version, target_version=p.version)])
    assert sum(isinstance(r, dict) for r in results) == 1
    with sessions() as s:
        assert len(s.scalars(select(FinancialRelation)).all()) == 1


def test_audit_failure_rolls_back_both_cas_and_reservations(setup, monkeypatch):
    d, sessions, _, _ = setup
    m, p = pair(d)
    before = state(d, sessions)
    original = d._event
    def fail_recipient(session, run, meta, event_type, payload):
        if event_type == 'cross_mas.received':
            raise RuntimeError('injected second audit failure')
        original(session, run, meta, event_type, payload)
    monkeypatch.setattr(d, '_event', fail_recipient)
    with pytest.raises(RuntimeError, match='second audit'):
        admit(d, p, m, message(d, p, m))
    assert state(d, sessions) == before


def test_unavailable_is_zero_cost_and_does_not_resolve_without_cause(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    admit(d, p, m, message(d, p, m, 'request'))
    admit(d, m, p, message(d, m, p, 'diagnostic', 'SYSTEM_UNAVAILABLE'))
    admit(d, m, p, message(d, m, p, 'resolution', 'SYSTEM_UNAVAILABLE', causation_id='request'))
    assert d.snapshot(m.id)['budget']['hops'] == 0
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        admit(d, m, p, message(d, m, p, 'again', 'SYSTEM_UNAVAILABLE', causation_id='request'))
    assert state(d, sessions) == before


@pytest.mark.parametrize('fault', ['missing', 'foreign', 'schema', 'timepoint'])
def test_ready_immutable_artifact_validation_and_rollback(setup, fault):
    d, sessions, _, _ = setup
    m, p = pair(d)
    ref = artifact(d, m)
    if fault == 'missing':
        ref = ArtifactRef(artifact_id='missing')
    elif fault == 'foreign':
        other = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
            idempotency_key='other', correlation_id='corr', mode='auto')
        ref = artifact(d, other)
    elif fault == 'schema':
        # ArtifactRef has a fixed schema; persisted metadata is untrusted on read.
        with sessions() as s:
            s.get(FinancialArtifact, ref.artifact_id).schema_version = 2
            s.commit()
    else:
        with sessions() as s:
            s.get(FinancialArtifact, ref.artifact_id).as_of = NOW + timedelta(days=1)
            s.commit()
    before = state(d, sessions)
    with pytest.raises(ValueError):
        admit(d, m, p, message(d, m, p, 'ready', 'MARKET_EVIDENCE_READY', payload_ref=ref))
    assert state(d, sessions) == before


def test_terminal_sender_request_and_zero_budget_terminal_diagnostic(setup):
    d, sessions, _, _ = setup
    m, p = pair(d, budget=RunBudget(max_hops=0, max_followups=0))
    d.cancel(p.id, p.version)
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        admit(d, p, m, message(d, p, m))
    assert state(d, sessions) == before
    admit(d, p, m, message(d, p, m, 'unavailable', 'SYSTEM_UNAVAILABLE'))
    assert d.snapshot(p.id)['budget']['hops'] == 0


def test_direction_and_envelope_ceiling_cannot_replace_authoritative_budget(setup):
    d, sessions, _, _ = setup
    m, p = pair(d, budget=RunBudget(max_hops=1))
    for env in (message(d, m, p, 'wrong-direction'),
                message(d, p, m, 'excessive', budget=RunBudget())):
        before = state(d, sessions)
        with pytest.raises(ValueError):
            admit(d, p if env.run_id == p.id else m, m if env.run_id == p.id else p, env)
        assert state(d, sessions) == before
    # Advertising zero consumed counters cannot authorize a second follow-up.
    admit(d, p, m, message(d, p, m, 'first'))
    before = state(d, sessions)
    with pytest.raises(BudgetExhausted):
        admit(d, p, m, message(d, p, m, 'second'))
    assert state(d, sessions) == before


def test_wait_graph_ignores_terminal_intermediate_members(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    m2 = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW), idempotency_key='m2', correlation_id='corr')
    p2 = d.create('c1', PortfolioReviewRequest(portfolio_snapshot_id='other', as_of=NOW), idempotency_key='p2', correlation_id='corr')
    # Pre-existing generic path m -> p2 -> m2 -> p would close a cycle.
    with sessions() as s:
        for i, (source, target) in enumerate(((m, p2), (p2, m2), (m2, p))):
            env = message(d, source, target, 'old-' + str(i))
            s.add(FinancialRelation(id='old-' + str(i), conversation_id='c1', source_run_id=source.id,
                target_run_id=target.id, correlation_id='corr', relation_type='cross_admitted',
                idempotency_key=env.idempotency_key, envelope=env.model_dump(mode='json')))
        s.commit()
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        admit(d, p, m, message(d, p, m, 'cycle'))
    assert state(d, sessions) == before
    d.cancel(m2.id, d.get_run(m2.id).version)
    admit(d, p, m, message(d, p, m, 'after-terminal'))


def test_wait_graph_ignores_resolved_request_edges(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    old = message(d, m, p, 'old')
    with sessions() as s:
        s.add(FinancialRelation(id='old', conversation_id='c1', source_run_id=m.id,
            target_run_id=p.id, correlation_id='corr', relation_type='cross_admitted',
            idempotency_key='old', envelope=old.model_dump(mode='json')))
        s.commit()
    admit(d, p, m, message(d, p, m, 'resolution', 'SYSTEM_UNAVAILABLE', causation_id='old'))
    admit(d, p, m, message(d, p, m, 'new-request'))


def test_second_sorted_cas_failure_rolls_back_first_cas(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    before = state(d, sessions)
    versions = dict(source_version=p.version, target_version=m.version)
    versions['source_version' if p.id > m.id else 'target_version'] = 0
    with pytest.raises(FinancialConflict):
        admit(d, p, m, message(d, p, m), **versions)
    assert state(d, sessions) == before


def test_exact_competing_replay_reserves_once(setup):
    d, sessions, _, _ = setup
    m, p = pair(d)
    env = message(d, p, m)
    results = race([lambda: admit(d, p, m, env, source_version=p.version, target_version=m.version),
                    lambda: admit(d, p, m, env, source_version=p.version, target_version=m.version)])
    assert results[0] == results[1]
    assert d.snapshot(p.id)['budget']['hops'] == 1
    assert d.snapshot(p.id)['budget']['followups'] == 1
    with sessions() as s:
        assert len(s.scalars(select(FinancialRelation)).all()) == 1
        assert len(s.scalars(select(AgentEvent).where(AgentEvent.event_type == 'cross_mas.admitted')).all()) == 1
        assert len(s.scalars(select(AgentEvent).where(AgentEvent.event_type == 'cross_mas.received')).all()) == 1


def test_retry_authority_locked_and_concurrent_membership_replay(setup, monkeypatch):
    d, sessions, _, _ = setup
    m, p = pair(d)
    cancelled = d.cancel(m.id, m.version)
    calls = []
    original = d._lock_conversation
    def lock(session, conversation_id):
        original(session, conversation_id)
        calls.append(conversation_id)
    monkeypatch.setattr(d, '_lock_conversation', lock)
    before = state(d, sessions)
    with pytest.raises(FinancialConflict):
        d.retry(m.id, 0, idempotency_key='stale')
    assert calls == ['c1']
    assert state(d, sessions) == before
    results = race([lambda: d.retry(m.id, cancelled.version, idempotency_key='retry'),
                    lambda: d.retry(m.id, cancelled.version, idempotency_key='retry')])
    assert all(isinstance(r, AgentRun) for r in results)
    assert results[0].id == results[1].id
    assert results[0].parent_run_id == m.id
    assert d.snapshot(results[0].id)['correlation_id'] == 'corr'
    with sessions() as s:
        members = s.scalars(select(FinancialRun).where(FinancialRun.correlation_id == 'corr')).all()
        assert len(members) == 3
        events = s.scalars(select(AgentEvent).where(AgentEvent.run_id == results[0].id)).all()
        assert [e.event_type for e in events] == ['mas.created', 'mas.retry_linked']


@pytest.mark.parametrize('contains_target', [True, False])
def test_optional_request_artifact_is_source_owned_and_market_symbol_scoped(setup, contains_target):
    d, sessions, _, _ = setup
    m, p = pair(d)
    # A persisted source snapshot is seeded to exercise the frozen envelope's
    # optional artifact reference independently of final business completion.
    payload = PortfolioProposalArtifact(producing_run_id=p.id, snapshot_id='holdings', as_of=NOW,
        current_weights={'CASH': 0.5, 'MU' if contains_target else 'OTHER': 0.5},
        proposed_weights={}, constraint_check=ConstraintCheck(status='unknown'), status='insufficient_data')
    with sessions() as s:
        row = ArtifactStore.put_in_transaction(s, s.get(AgentRun, p.id), s.get(FinancialRun, p.id), 'snapshot', payload)
        s.commit()
        ref = ArtifactRef(artifact_id=row.id)
    before = state(d, sessions)
    env = message(d, p, m, payload_ref=ref)
    if contains_target:
        admit(d, p, m, env)
    else:
        with pytest.raises(ValueError, match='target symbol'):
            admit(d, p, m, env)
        assert state(d, sessions) == before
