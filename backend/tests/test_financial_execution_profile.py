"""Immutable execution-profile identity and pre-claim no-write gates."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from sqlalchemy import select, event
from db.base import Base
from db.models import FinancialRun, AgentRun
from agent.shared import *
from backend.tests.test_financial_runtime import setup, NOW


def assembly(d, profile):
    return FinancialMASDispatcher(d.sessions, d.drivers, d.tools,
        clock=d.clock, execution_profile=profile)


def create(d, key='market', **changes):
    options = dict(idempotency_key=key, mode='auto', correlation_id='corr')
    options.update(changes)
    return d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW), **options)


def database(sessions):
    # Capture every persisted column, including General rows and all financial
    # versions/checkpoints/claims/budgets/audit/results/artifacts.
    with sessions() as s:
        return {table.name: [dict(row) for row in s.execute(select(table).order_by(
            *table.primary_key.columns)).mappings()] for table in Base.metadata.sorted_tables}


def calls(*drivers):
    return [len(provider.calls) for driver in drivers for provider in driver.providers]


@pytest.mark.parametrize('invalid', ['', ' ', ' leading', 'trailing ', '\tname', 'name\n', 'x' * 129, 1, True, b'configured-v1', [], {}])
def test_invalid_profile_ids_reject_without_normalizing(setup, invalid):
    d, sessions, _, _ = setup
    before = database(sessions)
    with pytest.raises(FinancialExecutionProfileError):
        assembly(d, invalid)
    assert database(sessions) == before


@pytest.mark.parametrize('profile', [None, 'x', 'x' * 128, '版本-v1', 'internal space'])
def test_valid_profiles_are_exact_and_read_only_configuration(setup, profile):
    d, _, _, _ = setup
    configured = assembly(d, profile)
    assert configured.execution_profile == profile
    with pytest.raises(AttributeError):
        configured.execution_profile = 'changed'


def test_legacy_none_creation_json_is_exactly_preserved_and_direct_execution_works(setup):
    d, sessions, _, _ = setup
    run = create(d)
    with sessions() as s:
        meta = s.get(FinancialRun, run.id)
        assert meta.creation_inputs == {
            'mas_kind': 'market_investigation', 'request': {'symbol': 'MU', 'as_of': '2026-01-01T00:00:00Z', 'lookback_trading_days': 20, 'sector_benchmark': None, 'max_llm_calls': 16},
            'mode': 'auto', 'budget': RunBudget().model_dump(mode='json'),
            'requested_correlation_id': 'corr', 'retry_parent_id': None}
        assert 'execution_profile' not in meta.creation_inputs
    assert d.snapshot(run.id)['execution_profile'] is None
    assert asyncio.run(d.start(run.id)).status == 'completed'
    assert create(d).id == run.id


def test_matching_profile_direct_execution_and_full_idempotency(setup):
    d, sessions, market, portfolio = setup
    configured = assembly(d, 'configured-v1')
    run = create(configured)
    with sessions() as s:
        assert s.get(FinancialRun, run.id).creation_inputs['execution_profile'] == 'configured-v1'
    assert configured.snapshot(run.id)['execution_profile'] == 'configured-v1'
    assert create(assembly(d, 'configured-v1')).id == run.id
    for other in (None, 'configured-v2', 'CONFIGURED-v1'):
        before = database(sessions)
        with pytest.raises(FinancialConflict):
            create(assembly(d, other))
        assert database(sessions) == before
    assert asyncio.run(configured.start(run.id)).status == 'completed'
    assert calls(market, portfolio) == [1, 1, 0, 0]
    before = database(sessions)
    assert asyncio.run(configured.start(run.id)).status == 'completed'
    assert database(sessions) == before


@pytest.mark.parametrize('stored,builder', [('configured-v1', None), (None, 'configured-v1'), ('configured-v1', 'configured-v2')])
@pytest.mark.parametrize('terminal', [False, True])
def test_start_profile_mismatch_is_explicit_preclaim_and_no_write_no_call(setup, stored, builder, terminal):
    d, sessions, market, portfolio = setup
    creator = assembly(d, stored)
    run = create(creator)
    if terminal:
        assert asyncio.run(creator.start(run.id)).status == 'completed'
    mismatched = assembly(d, builder)
    before, before_calls = database(sessions), calls(market, portfolio)
    statements = []
    engine = sessions.kw['bind']
    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(('UPDATE ', 'INSERT ', 'DELETE ')):
            statements.append(statement)
    event.listen(engine, 'before_cursor_execute', record)
    try:
        with pytest.raises(FinancialExecutionProfileError, match='mismatch'):
            asyncio.run(mismatched.start(run.id))
    finally:
        event.remove(engine, 'before_cursor_execute', record)
    assert not statements
    assert database(sessions) == before
    assert calls(market, portfolio) == before_calls


@pytest.mark.parametrize('stored,builder', [('configured-v1', None), (None, 'configured-v1'), ('configured-v1', 'configured-v2')])
def test_mismatched_retry_rejects_child_creation_and_existing_child_replay(setup, stored, builder):
    d, sessions, market, portfolio = setup
    creator = assembly(d, stored)
    parent = create(creator)
    parent = d.cancel(parent.id, parent.version)
    wrong = assembly(d, builder)
    before, before_calls = database(sessions), calls(market, portfolio)
    with pytest.raises(FinancialExecutionProfileError, match='mismatch'):
        wrong.retry(parent.id, parent.version, idempotency_key='child')
    assert database(sessions) == before
    child = creator.retry(parent.id, parent.version, idempotency_key='child')
    before = database(sessions)
    with pytest.raises(FinancialExecutionProfileError, match='mismatch'):
        wrong.retry(parent.id, parent.version, idempotency_key='child')
    assert database(sessions) == before
    assert creator.snapshot(child.id)['execution_profile'] == stored
    assert calls(market, portfolio) == before_calls


@pytest.mark.parametrize('profile', [None, 'configured-v1'])
def test_retry_inherits_identity_budgets_correlation_and_parent(setup, profile):
    d, sessions, _, _ = setup
    creator = assembly(d, profile)
    parent = create(creator, budget=RunBudget(max_hops=1, max_model_calls=2))
    parent = creator.cancel(parent.id, parent.version)
    child = creator.retry(parent.id, parent.version, idempotency_key='child')
    assert child.parent_run_id == parent.id
    snap = creator.snapshot(child.id)
    assert snap['execution_profile'] == profile and snap['correlation_id'] == 'corr'
    assert snap['budget'] == RunBudget(max_hops=1, max_model_calls=2).model_dump()
    with sessions() as s:
        meta = s.get(FinancialRun, child.id)
        assert ('execution_profile' in meta.creation_inputs) == (profile is not None)
    before = database(sessions)
    assert creator.retry(parent.id, parent.version, idempotency_key='child').id == child.id
    assert database(sessions) == before
    assert asyncio.run(creator.start(child.id)).status == 'completed'


def test_atomic_retry_parent_profile_recheck_cannot_be_bypassed(setup):
    d, sessions, market, portfolio = setup
    parent = create(assembly(d, 'configured-v1'))
    parent = d.cancel(parent.id, parent.version)
    before = database(sessions)
    # Exercise the existing reserved create seam directly, independently of
    # retry's first authority check, to verify the insertion transaction guard.
    with pytest.raises(FinancialExecutionProfileError, match='mismatch'):
        d.create('c1', MarketInvestigationRequest(symbol='MU', as_of=NOW),
            idempotency_key='child', mode='auto', correlation_id='corr',
            _retry_parent_id=parent.id, _retry_parent_version=parent.version)
    assert database(sessions) == before
    assert calls(market, portfolio) == [0, 0, 0, 0]


@pytest.mark.parametrize('second_profile', ['configured-v1', 'configured-v2', None])
def test_concurrent_creation_profile_is_part_of_full_identity(setup, second_profile):
    d, sessions, _, _ = setup
    barrier = threading.Barrier(2)
    def attempt(profile):
        barrier.wait(timeout=5)
        try:
            return create(assembly(d, profile))
        except FinancialConflict as exc:
            return exc
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(attempt, ['configured-v1', second_profile]))
    if second_profile == 'configured-v1':
        assert results[0].id == results[1].id
    else:
        assert sum(isinstance(r, FinancialConflict) for r in results) == 1
    with sessions() as s:
        rows = s.scalars(select(FinancialRun)).all()
        assert len(rows) == 1
        stored = rows[0].creation_inputs.get('execution_profile')
        assert stored in {'configured-v1', second_profile}


def test_lifecycle_and_reads_do_not_require_matching_profile(setup):
    d, _, _, _ = setup
    creator = assembly(d, 'configured-v1')
    run = create(creator, mode='review')
    assert asyncio.run(creator.start(run.id)).status == 'waiting_user'
    assert d.get_run(run.id).status == 'waiting_user'
    assert d.is_financial(run.id)
    assert d.snapshot(run.id)['execution_profile'] == 'configured-v1'
    run = d.approve(run.id, d.get_run(run.id).version)
    run = d.pause(run.id, run.version)
    run = d.resume(run.id, run.version)
    assert d.cancel(run.id, run.version).status == 'cancelled'


@pytest.mark.parametrize('builder', [None, 'synthetic-demo-v1', 'configured-v1'])
def test_fresh_process_dispatcher_obeys_persisted_profile(setup, builder):
    d, sessions, _, _ = setup
    run = create(assembly(d, 'configured-v1'))
    before = database(sessions)
    root = Path(__file__).resolve().parents[2]
    script = '''
import asyncio, json, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agent.shared import *
from backend.tests.test_financial_runtime import FakeDriver
registry = WorkflowRegistry()
market = FakeDriver('market_investigation')
registry.register(market)
dispatcher = FinancialMASDispatcher(sessionmaker(create_engine(sys.argv[1]), expire_on_commit=False),
    registry, execution_profile=json.loads(sys.argv[3]))
error = None
try:
    asyncio.run(dispatcher.start(sys.argv[2]))
except FinancialExecutionProfileError as exc:
    error = type(exc).__name__
print(json.dumps({'error': error, 'calls': sum(len(p.calls) for p in market.providers),
    'snapshot': dispatcher.snapshot(sys.argv[2])}))
'''
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(str(path) for path in (root, root / 'backend', root / 'lobster_quant'))
    result = subprocess.run([sys.executable, '-c', script, str(sessions.kw['bind'].url), run.id, json.dumps(builder)],
        cwd=root, env=env, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    observed = json.loads(result.stdout)
    if builder == 'configured-v1':
        assert observed['error'] is None and observed['calls'] == 2
        assert observed['snapshot']['status'] == 'completed'
        assert observed['snapshot']['execution_profile'] == 'configured-v1'
    else:
        assert observed['error'] == 'FinancialExecutionProfileError'
        assert observed['calls'] == 0
        assert database(sessions) == before
