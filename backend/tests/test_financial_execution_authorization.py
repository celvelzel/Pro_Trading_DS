"""ADR-0005 authority, zero-write denials and fenced absolute TTL evidence."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
import threading
import pytest
from pydantic import ValidationError
from sqlalchemy import event, select, update
from sqlalchemy.dialects import postgresql
from db.base import Base
from db.models import AgentRun, AgentEvent, FinancialRun, FinancialInvocation, FinancialArtifact, Conversation
from db.models.financial_mas import FinancialRelation
from agent.shared import *
from backend.tests.test_financial_runtime import setup, NOW, FakeDriver
from backend.tests.test_financial_execution_profile import database, calls
from backend.tests.test_cross_admission import message, admit

INDEPENDENT = FinancialExecutionAuthorization(purpose='independent')


def market(d, key='m', authorization=None, **kwargs):
    return d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
        idempotency_key=key, mode=kwargs.pop('mode', 'auto'),
        execution_authorization=authorization, **kwargs)


def pair(d, admitted=True, **kwargs):
    d.clock = lambda: NOW
    source = d.create('c1', PortfolioReviewRequest(portfolio_snapshot_id='holdings', as_of=NOW),
        idempotency_key='p', mode='auto', correlation_id='corr', execution_authorization=INDEPENDENT)
    authorization = FinancialExecutionAuthorization(purpose='cross_followup',
        source_run_id=source.id, request_message_id='request')
    target = market(d, authorization=authorization, correlation_id='corr', **kwargs)
    if admitted:
        admit(d, source, target, message(d, source, target, 'request'))
    return source, target, authorization


@contextmanager
def no_dml(sessions):
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(('UPDATE ', 'INSERT ', 'DELETE ')):
            statements.append(statement)
    engine = sessions.kw['bind']
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        yield
    finally:
        event.remove(engine, 'before_cursor_execute', capture)
    assert statements == []


@pytest.mark.parametrize('field', ['purpose', 'source_run_id', 'request_message_id'])
@pytest.mark.parametrize('bad', [b'identifier', 123, True, '', ' ', ' leading', 'trailing ', [], {}])
def test_origin_strict_before_coercion_no_writes(setup, field, bad):
    d, sessions, m, p = setup
    value = dict(purpose='cross_followup', source_run_id='source', request_message_id='request')
    value[field] = bad
    before = database(sessions)
    with no_dml(sessions), pytest.raises(ValidationError):
        market(d, authorization=value)
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]


@pytest.mark.parametrize('value', [dict(purpose='unknown'), dict(purpose='cross_followup'),
    dict(purpose='independent', source_run_id='source'),
    dict(purpose='independent', request_message_id='message'), dict(purpose='independent', extra=1)])
def test_invalid_origin_combinations(setup, value):
    d, sessions, _, _ = setup
    before = database(sessions)
    with no_dml(sessions), pytest.raises(ValidationError):
        market(d, authorization=value)
    assert database(sessions) == before


def test_none_omission_and_independent_origin_full_identity(setup):
    d, sessions, m, p = setup
    legacy = market(d)
    with sessions() as s:
        assert 'execution_authorization' not in s.get(FinancialRun, legacy.id).creation_inputs
    assert d.snapshot(legacy.id)['execution_authorization'] is None
    assert market(d).id == legacy.id
    before = database(sessions)
    with pytest.raises(FinancialConflict):
        market(d, authorization=INDEPENDENT)
    assert database(sessions) == before
    explicit = market(d, 'explicit', INDEPENDENT, correlation_id='corr')
    assert d.snapshot(explicit.id)['execution_authorization'] == INDEPENDENT.model_dump(mode='json')
    with pytest.raises(ValidationError):
        INDEPENDENT.purpose = 'cross_followup'
    assert asyncio.run(d.start(legacy.id)).status == 'completed'
    registry = WorkflowRegistry()
    registry.register(FakeDriver('market_investigation'))
    fresh = FinancialMASDispatcher(sessions, registry)
    assert asyncio.run(fresh.start(explicit.id)).status == 'completed'


@pytest.mark.parametrize('second', [None, INDEPENDENT])
def test_concurrent_origin_identity(setup, second):
    d, sessions, _, _ = setup
    barrier = threading.Barrier(2)
    def attempt(authorization):
        barrier.wait(timeout=5)
        try:
            return market(d, authorization=authorization)
        except FinancialConflict as exc:
            return exc
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(attempt, [INDEPENDENT, second]))
    if second is None:
        assert sum(isinstance(r, FinancialConflict) for r in results) == 1
    else:
        assert results[0].id == results[1].id
    with sessions() as s:
        assert len(s.scalars(select(FinancialRun)).all()) == 1


@pytest.mark.parametrize('entry', ['direct', 'queue'])
def test_creation_admission_crash_orphan_is_inert_zero_dml(setup, entry):
    d, sessions, m, p = setup
    source, target, _ = pair(d, admitted=False)
    # Fresh dispatcher represents restart; origin is read from persisted JSON.
    restarted = FinancialMASDispatcher(sessions, d.drivers, d.tools, clock=d.clock)
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError) as error:
        if entry == 'queue':
            restarted.validate_queue_eligibility(target.id)
        else:
            asyncio.run(restarted.start(target.id))
    assert error.value.code == 'financial_execution_authorization_denied'
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]
    assert asyncio.run(d.start(source.id)).status == 'completed'


@pytest.mark.parametrize('stored', [None, {}, {'purpose': 'unknown'}, {'purpose': 'cross_followup', 'source_run_id': 1, 'request_message_id': 'x'}])
def test_malformed_stored_origin_never_legacy(setup, stored):
    d, sessions, m, p = setup
    target = market(d)
    with sessions() as s:
        meta = s.get(FinancialRun, target.id)
        meta.creation_inputs = dict(meta.creation_inputs, execution_authorization=stored)
        s.commit()
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError):
        asyncio.run(d.start(target.id))
    with pytest.raises(FinancialExecutionAuthorizationError):
        d.snapshot(target.id)
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]


@pytest.mark.parametrize('field,value', [('relation_type', 'diagnostic'), ('target_run_id', 'other'),
    ('source_run_id', 'other'), ('correlation_id', 'other'), ('message_type', 'SYSTEM_UNAVAILABLE'),
    ('as_of', '2026-01-02T00:00:00Z'), ('run_id', 'other'), ('target_mas', 'portfolio_rebalance')])
def test_exact_positive_request_authority_rejects_forged_relation(setup, field, value):
    d, sessions, m, p = setup
    _, target, _ = pair(d)
    with sessions() as s:
        row = s.scalar(select(FinancialRelation))
        if field in {'relation_type', 'target_run_id', 'source_run_id', 'correlation_id'}:
            setattr(row, field, value)
        else:
            row.envelope = dict(row.envelope, **{field: value})
        s.commit()
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError):
        asyncio.run(d.start(target.id))
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]


def assert_expired(d, sessions, target, model_calls=0, tool_calls=0):
    snap = d.snapshot(target.id)
    assert snap['status'] == 'expired' and snap['error_code'] == 'cross_execution_expired'
    assert snap['budget']['model_calls'] == model_calls and snap['budget']['tool_calls'] == tool_calls
    assert snap['budget']['rounds'] == snap['budget']['hops'] == snap['budget']['followups'] == 0
    assert snap['checkpoint']['artifact_ids'] == [] and snap['final_answer'] is None
    with sessions() as s:
        assert not s.scalars(select(FinancialArtifact).where(FinancialArtifact.run_id == target.id)).all()
        events = s.scalars(select(AgentEvent).where(AgentEvent.run_id == target.id).order_by(AgentEvent.seq)).all()
        assert sum(e.event_type == 'mas.expired' for e in events) == 1
        assert not any(e.event_type in {'mas.failure', 'mas.returned', 'mas.artifact_created', 'mas.completed'} for e in events)
        assert [e.seq for e in events] == list(range(1, len(events) + 1))
    before = database(sessions)
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert database(sessions) == before


@pytest.mark.parametrize('expire_at', ['preflight', 'lock', 'cas'])
def test_claim_fresh_deadline_after_preflight_and_lock(setup, expire_at):
    d, sessions, m, p = setup
    source, target, _ = pair(d)
    d.validate_queue_eligibility(target.id)
    statements = []
    engine = sessions.kw['bind']
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
        if expire_at == 'lock' and statement.startswith('UPDATE conversations'):
            d.clock = lambda: NOW + timedelta(seconds=30)
        if expire_at == 'cas' and statement.startswith('UPDATE agent_runs'):
            d.clock = lambda: NOW + timedelta(seconds=30)
    if expire_at == 'preflight':
        d.clock = lambda: NOW + timedelta(seconds=30)
    event.listen(engine, 'before_cursor_execute', capture)
    try:
        assert asyncio.run(d.start(target.id)).status == 'expired'
    finally:
        event.remove(engine, 'before_cursor_execute', capture)
    assert_expired(d, sessions, target)
    assert calls(m, p) == [0, 0, 0, 0]
    writes = [s for s in statements if s.startswith('UPDATE ')]
    assert writes[0].startswith('UPDATE conversations')
    assert next(i for i,s in enumerate(writes) if s.startswith('UPDATE agent_runs')) > 0


@pytest.mark.parametrize('phase', ['waiting_user', 'paused', 'cancelled'])
def test_intervention_and_pending_review_beat_expiry(setup, phase):
    d, sessions, m, p = setup
    _, target, _ = pair(d, mode='review')
    run = asyncio.run(d.start(target.id))
    assert run.status == 'waiting_user'
    if phase == 'paused':
        run = d.pause(target.id, run.version)
    elif phase == 'cancelled':
        run = d.cancel(target.id, run.version)
    d.clock = lambda: NOW + timedelta(seconds=30)
    before = database(sessions)
    assert asyncio.run(d.start(target.id)).status == phase
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]
    if phase == 'waiting_user':
        d.approve(target.id, run.version)
        assert asyncio.run(d.start(target.id)).status == 'expired'
        assert_expired(d, sessions, target)


@pytest.mark.parametrize('point', ['before_reservation', 'reservation_external', 'return', 'late_failure', 'checkpoint', 'final', 'unfinished'])
def test_inflight_deadline_no_new_calls_or_late_output(setup, point):
    d, sessions, m, p = setup
    # Keep claim ownership valid at TTL: lease expiration is a distinct fence.
    d.lease_seconds = 60
    _, target, _ = pair(d)
    external_calls = []
    async def provider():
        external_calls.append('provider')
        d.clock = lambda: NOW + timedelta(seconds=30)
        if point == 'late_failure':
            raise ValueError('late provider output')
        return {'summary': 'late'}
    async def execute(ctx, state):
        if point == 'before_reservation':
            d.clock = lambda: NOW + timedelta(seconds=30)
            ctx.reserve('model', 'investigator', 'one')
        elif point in {'reservation_external', 'return', 'late_failure'}:
            ctx.reserve('model', 'investigator', 'one')
            if point == 'reservation_external':
                d.clock = lambda: NOW + timedelta(seconds=30)
            try:
                await ctx.external(provider())
            except Exception as exc:
                ctx.record_failure('one', getattr(exc, 'code', 'provider_failed'))
                raise
        elif point == 'checkpoint':
            d.clock = lambda: NOW + timedelta(seconds=30)
            ctx.checkpoint(state)
        else:
            d.clock = lambda: NOW + timedelta(seconds=30)
            if point == 'unfinished':
                return None
            return MarketInvestigationArtifact(producing_run_id=ctx.run_id, symbol='MU', as_of=NOW, status='partial')
    m.execute = execute
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert_expired(d, sessions, target, model_calls=int(point in {'reservation_external', 'return', 'late_failure'}))
    assert len(external_calls) == int(point in {'return', 'late_failure'})
    assert calls(m, p) == [0, 0, 0, 0]
    with sessions() as s:
        invocations = s.scalars(select(FinancialInvocation).where(FinancialInvocation.run_id == target.id)).all()
        assert all(row.status == 'reserved' and row.output is None for row in invocations)


@pytest.mark.parametrize('intervention', ['pause', 'cancel', 'lease'])
def test_inflight_fencing_wins_over_expiry(setup, intervention):
    d, sessions, m, _ = setup
    _, target, _ = pair(d)
    async def execute(ctx, state):
        ctx.reserve('model', 'investigator', 'one')
        if intervention == 'lease':
            with sessions() as s:
                s.get(FinancialRun, target.id).claim_token = 'new-owner'
                s.commit()
        else:
            getattr(d, intervention)(target.id, d.get_run(target.id).version)
        d.clock = lambda: NOW + timedelta(seconds=30)
        ctx.record_failure('one', 'late_failure')
    m.execute = execute
    run = asyncio.run(d.start(target.id))
    assert run.status == {'pause': 'paused', 'cancel': 'cancelled', 'lease': 'executing'}[intervention]
    with sessions() as s:
        assert not any(e.event_type in {'mas.expired', 'mas.failure', 'mas.invocation_failed'} for e in s.scalars(select(AgentEvent).where(AgentEvent.run_id == target.id)))


@pytest.mark.parametrize('seam', ['retry', 'create_none', 'create_independent', 'create_cross'])
def test_cross_retry_both_seams_spoof_rejected_zero_dml(setup, seam):
    d, sessions, m, p = setup
    _, target, authorization = pair(d)
    target = d.cancel(target.id, d.get_run(target.id).version)
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError):
        if seam == 'retry':
            d.retry(target.id, target.version, idempotency_key='child')
        else:
            chosen = {'create_none': None, 'create_independent': INDEPENDENT, 'create_cross': authorization}[seam]
            market(d, 'child', chosen, correlation_id='corr', _retry_parent_id=target.id, _retry_parent_version=target.version)
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]


def test_admitted_request_does_not_authorize_new_sibling(setup):
    d, sessions, m, p = setup
    _, target, authorization = pair(d)
    sibling = market(d, 'sibling', authorization, correlation_id='corr')
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError):
        asyncio.run(d.start(sibling.id))
    assert database(sessions) == before
    assert asyncio.run(d.start(target.id)).status == 'completed'


@pytest.mark.parametrize('kind', ['market_investigation', 'portfolio_rebalance'])
def test_independent_retry_inherits_origin(setup, kind):
    d, sessions, _, _ = setup
    request = MarketInvestigationRequest(symbol='MU', as_of=NOW) if kind == 'market_investigation' else PortfolioReviewRequest(portfolio_snapshot_id='holdings', as_of=NOW)
    parent = d.create('c1', request, idempotency_key='root', mode='auto', correlation_id='corr', execution_authorization=INDEPENDENT)
    parent = d.cancel(parent.id, parent.version)
    child = d.retry(parent.id, parent.version, idempotency_key='child')
    assert d.snapshot(child.id)['execution_authorization'] == INDEPENDENT.model_dump(mode='json')
    before = database(sessions)
    with no_dml(sessions):
        d.validate_queue_eligibility(child.id)
    assert database(sessions) == before
    assert asyncio.run(d.start(child.id)).status == 'completed'


def legacy_chain(d, depth):
    root = market(d, 'root')
    child = root
    for edge in range(depth):
        parent = d.cancel(child.id, child.version)
        child = d.retry(parent.id, parent.version, idempotency_key='edge' + str(edge))
    return root, child


@pytest.mark.parametrize('depth', [0, 1, 32, 33])
def test_legacy_queue_bounded_ancestry(setup, depth):
    d, sessions, _, _ = setup
    _, child = legacy_chain(d, depth)
    before = database(sessions)
    with no_dml(sessions):
        if depth <= 32:
            assert d.validate_queue_eligibility(child.id) is None
        else:
            with pytest.raises(FinancialExecutionAuthorizationError, match='32'):
                d.validate_queue_eligibility(child.id)
    assert database(sessions) == before
    # The queue policy is deliberately separate from legacy direct semantics.
    assert asyncio.run(d.start(child.id)).status == 'completed'


@pytest.mark.parametrize('attack', ['missing', 'cycle', 'parent_seam', 'request', 'profile', 'correlation', 'conversation', 'domain', 'origin', 'root_explicit'])
def test_legacy_ancestry_adversaries_no_mutation(setup, attack):
    d, sessions, m, p = setup
    root, child = legacy_chain(d, 1)
    with sessions() as s:
        run = s.get(AgentRun, root.id)
        meta = s.get(FinancialRun, root.id)
        if attack == 'missing':
            s.delete(meta)
        elif attack == 'cycle':
            run.parent_run_id = child.id
            meta.creation_inputs = dict(meta.creation_inputs, retry_parent_id=child.id, requested_correlation_id=meta.correlation_id)
        elif attack == 'parent_seam':
            meta.creation_inputs = dict(meta.creation_inputs, retry_parent_id='other')
        elif attack == 'request':
            meta.request = dict(meta.request, symbol='SPY')
        elif attack == 'profile':
            meta.creation_inputs = dict(meta.creation_inputs, execution_profile='other')
        elif attack == 'correlation':
            meta.correlation_id = 'other'
        elif attack == 'conversation':
            run.conversation_id = 'c2'
        elif attack == 'domain':
            meta.mas_kind = 'portfolio_rebalance'
        elif attack == 'origin':
            meta.creation_inputs = dict(meta.creation_inputs, execution_authorization=INDEPENDENT.model_dump(mode='json'))
        else:
            meta.creation_inputs = dict(meta.creation_inputs, requested_correlation_id=meta.correlation_id)
        s.commit()
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError):
        d.validate_queue_eligibility(child.id)
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]


def test_explicit_legacy_root_queue_denied_direct_preserved(setup):
    d, sessions, _, _ = setup
    run = market(d, correlation_id='corr')
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError):
        d.validate_queue_eligibility(run.id)
    assert database(sessions) == before
    assert asyncio.run(d.start(run.id)).status == 'completed'


def test_positive_authority_independent_source_lifecycle_and_restore(setup):
    d, sessions, m, _ = setup
    source, target, _ = pair(d)
    d.cancel(source.id, d.get_run(source.id).version)
    m.stop_after_first = True
    assert asyncio.run(d.start(target.id)).status == 'executing'
    assert d.snapshot(target.id)['budget']['model_calls'] == 1
    m.stop_after_first = False
    restarted = FinancialMASDispatcher(sessions, d.drivers, d.tools, clock=d.clock)
    assert asyncio.run(restarted.start(target.id)).status == 'completed'
    assert calls(m) == [1, 1]
    before = database(sessions)
    assert asyncio.run(restarted.start(target.id)).status == 'completed'
    assert database(sessions) == before


def test_lease_crash_recovery_never_extends_absolute_ttl(setup):
    d, sessions, m, p = setup
    _, target, _ = pair(d)
    with sessions() as s:
        run, meta = s.get(AgentRun, target.id), s.get(FinancialRun, target.id)
        run.status = 'executing'
        meta.claim_token = 'crashed-worker'
        meta.active_since = NOW
        meta.lease_until = NOW + timedelta(seconds=10)
        s.commit()
    d.clock = lambda: NOW + timedelta(seconds=5)
    before = database(sessions)
    assert asyncio.run(d.start(target.id)).status == 'executing'
    assert database(sessions) == before
    d.clock = lambda: NOW + timedelta(seconds=30)
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert_expired(d, sessions, target)
    assert calls(m, p) == [0, 0, 0, 0]


def test_postgresql_canonical_lock_and_claim_sql():
    lock = str(update(Conversation).where(Conversation.id == 'c1').values(updated_at=Conversation.updated_at).compile(dialect=postgresql.dialect()))
    claim = str(update(AgentRun).where(AgentRun.id == 'run', AgentRun.version == 1).values(version=2).compile(dialect=postgresql.dialect()))
    assert 'UPDATE conversations SET updated_at=conversations.updated_at' in lock
    assert 'agent_runs.version =' in claim


@pytest.mark.parametrize('boundary', ['reservation', 'return', 'failure'])
def test_actual_tool_invocation_deadline_boundaries(setup, boundary, monkeypatch):
    from agent.tools.registry import ToolSpec
    from db.models.agent import ToolCall, ToolResult
    d, sessions, m, p = setup
    d.lease_seconds = 60
    _, target, _ = pair(d)
    class Input(FinancialModel):
        value: int
    tool_calls = []
    def readonly(data):
        tool_calls.append(data.value)
        d.clock = lambda: NOW + timedelta(seconds=30)
        if boundary == 'failure':
            raise ValueError('late failure')
        return data
    d.tools.register(ToolSpec('readonly', '1', 'read only', Input, Input, readonly))
    original = RuntimeContext.reserve
    def reserve(ctx, *args, **kwargs):
        result = original(ctx, *args, **kwargs)
        if boundary == 'reservation':
            d.clock = lambda: NOW + timedelta(seconds=30)
        return result
    monkeypatch.setattr(RuntimeContext, 'reserve', reserve)
    async def execute(ctx, state):
        await ctx.tool('investigator', 'one', 'readonly', Input(value=3))
    m.execute = execute
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert_expired(d, sessions, target, tool_calls=1)
    assert tool_calls == ([] if boundary == 'reservation' else [3])
    with sessions() as session:
        assert not session.scalars(select(ToolResult)).all()
        call = session.scalar(select(ToolCall))
        assert call.status == 'running'  # Reserved audit remains; no late output.


def test_actual_specialist_reservation_to_external_start(setup, monkeypatch):
    d, sessions, m, p = setup
    d.lease_seconds = 60
    _, target, _ = pair(d)
    original = RuntimeContext.reserve
    def reserve(ctx, *args, **kwargs):
        result = original(ctx, *args, **kwargs)
        d.clock = lambda: NOW + timedelta(seconds=30)
        return result
    monkeypatch.setattr(RuntimeContext, 'reserve', reserve)
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert_expired(d, sessions, target, model_calls=1)
    assert calls(m, p) == [0, 0, 0, 0]


def test_absolute_deadline_bounds_wait_and_renewed_lease(setup, monkeypatch):
    d, sessions, m, _ = setup
    d.lease_seconds = .06
    source, target, _ = pair(d, admitted=False)
    admit(d, source, target, message(d, source, target, 'request', deadline_at=NOW + timedelta(seconds=.15)))
    elapsed = [0.0]
    d.clock = lambda: NOW + timedelta(seconds=elapsed[0])
    invocations, waits = [], []
    async def external():
        invocations.append(1)
        await asyncio.sleep(1)
    async def wait(tasks, *, timeout):
        waits.append(timeout)
        # Deterministic waiting and renewal under a current claim, independent
        # of SQLite fsync or load in other concurrently running test processes.
        await asyncio.sleep(0)
        elapsed[0] = round(elapsed[0] + .03, 2)
        return set(), set(tasks)
    monkeypatch.setattr(asyncio, 'wait', wait)
    async def execute(ctx, state):
        await ctx.external(external())
    m.execute = execute
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert invocations == [1] and len(waits) == 5
    assert all(0 < timeout <= .02 for timeout in waits)
    assert elapsed[0] == .15
    assert_expired(d, sessions, target)


@pytest.mark.parametrize('boundary', ['record_result', 'generic_failure'])
def test_late_persistence_and_generic_failure_become_expiry(setup, boundary):
    d, sessions, m, _ = setup
    d.lease_seconds = 60
    _, target, _ = pair(d)
    async def execute(ctx, state):
        ctx.reserve('model', 'investigator', 'one')
        d.clock = lambda: NOW + timedelta(seconds=30)
        if boundary == 'generic_failure':
            raise ValueError('driver failed after deadline')
        ctx.record_result('one', {'summary': 'late output'})
    m.execute = execute
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert_expired(d, sessions, target, model_calls=1)


def test_stale_lease_at_expiry_cannot_write_then_fresh_delivery_expires(setup):
    d, sessions, m, _ = setup
    _, target, _ = pair(d)
    async def execute(ctx, state):
        d.clock = lambda: NOW + timedelta(seconds=30)
        ctx.checkpoint(state)
    m.execute = execute
    assert asyncio.run(d.start(target.id)).status == 'executing'
    with sessions() as s:
        assert not s.scalars(select(AgentEvent).where(AgentEvent.run_id == target.id, AgentEvent.event_type == 'mas.expired')).all()
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert_expired(d, sessions, target)


@pytest.mark.parametrize('profile_mismatch', [False, True])
def test_guarded_profile_mismatch_and_source_profile_authority(setup, profile_mismatch):
    d, sessions, m, p = setup
    source, target, _ = pair(d)
    if profile_mismatch:
        wrong = FinancialMASDispatcher(sessions, d.drivers, d.tools, clock=d.clock, execution_profile='wrong')
        expected = FinancialExecutionProfileError
    else:
        with sessions() as s:
            meta = s.get(FinancialRun, source.id)
            meta.creation_inputs = dict(meta.creation_inputs, execution_profile='wrong')
            s.commit()
        wrong = d
        expected = FinancialExecutionAuthorizationError
    before = database(sessions)
    with no_dml(sessions), pytest.raises(expected):
        asyncio.run(wrong.start(target.id))
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]


def test_actual_reviewed_market_driver_orphan_and_admitted_execution(setup):
    from agent.financial import build_financial_dispatcher
    from agent.financial_demo import DEMO_AS_OF, DEMO_SNAPSHOT_ID
    _, sessions, _, _ = setup
    d = build_financial_dispatcher(sessions, clock=lambda: NOW)
    source = d.create('c1', PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID, as_of=DEMO_AS_OF),
        idempotency_key='p', correlation_id='corr', mode='auto', execution_authorization=INDEPENDENT)
    authorization = FinancialExecutionAuthorization(purpose='cross_followup', source_run_id=source.id, request_message_id='request')
    target = d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=DEMO_AS_OF, sector_benchmark='SOXX'),
        idempotency_key='m', correlation_id='corr', mode='auto', execution_authorization=authorization)
    from dataclasses import replace
    from agent.tools.registry import ToolRegistry
    counts = []
    counted_tools = ToolRegistry()
    for spec in d.tools.list():
        original = spec.handler
        def counted(data, original=original):
            counts.append(1)
            return original(data)
        counted_tools.register(replace(spec, handler=counted))
    d.tools = counted_tools
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError):
        asyncio.run(d.start(target.id))
    assert database(sessions) == before and counts == []
    admit(d, source, target, message(d, source, target, 'request', as_of=DEMO_AS_OF))
    assert asyncio.run(d.start(target.id)).status == 'completed'
    snap = d.snapshot(target.id)
    assert snap['budget']['model_calls'] == 5 and snap['budget']['tool_calls'] == 3
    assert len(counts) == 3 and len(snap['checkpoint']['artifact_ids']) == 1
    assert snap['budget']['hops'] == snap['budget']['followups'] == 0


@pytest.mark.parametrize('which', ['source', 'target'])
def test_cross_metadata_conversation_mismatch_denies_no_write(setup, which):
    d, sessions, m, p = setup
    source, target, _ = pair(d)
    with sessions() as s:
        s.get(FinancialRun, source.id if which == 'source' else target.id).conversation_id = 'c2'
        s.commit()
    before = database(sessions)
    with no_dml(sessions), pytest.raises(FinancialExecutionAuthorizationError):
        asyncio.run(d.start(target.id))
    assert database(sessions) == before and calls(m, p) == [0, 0, 0, 0]



def test_event_loop_scheduling_gap_cannot_start_provider_after_deadline(setup):
    d, sessions, m, p = setup
    d.lease_seconds = 60
    _, target, _ = pair(d)
    async def execute(ctx, state):
        # This callback runs after external preflight but before the scheduled
        # provider task: execution authority must be checked inside that task.
        def expire():
            d.clock = lambda: NOW + timedelta(seconds=30)
        asyncio.get_running_loop().call_soon(expire)
        await ctx.invoke('investigator', 'one', ctx.request)
    m.execute = execute
    assert asyncio.run(d.start(target.id)).status == 'expired'
    assert_expired(d, sessions, target, model_calls=1)
    assert calls(m, p) == [0, 0, 0, 0]
