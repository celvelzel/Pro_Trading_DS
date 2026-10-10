"""SQLite + actual W2 tools; synthetic fixtures, no remote calls."""
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from db.base import Base
from db.models import Conversation, ToolCall, ToolResult, FinancialInvocation
from agent.llm import ScriptedFakeModel, ModelProviderError, ModelResponse
from agent.shared import FinancialMASDispatcher, WorkflowRegistry, MarketInvestigationRequest, RunBudget
from agent.tools.registry import ToolRegistry
from agent.tools import market_history, market_events, anomaly
from agent.market_mas import MarketCoordinator, SyntheticMarketModel
from agent.market_mas.driver import ROLES


def providers(check=None, forged=False):
    result = {}
    for role in ROLES:
        payload = {'role': role, 'action': 'challenge' if role == 'critic' else 'finding',
            'summary': 'Synthetic qualitative assessment; no causal proof',
            'missing_checks': [check] if role == 'critic' and check else [],
            'evidence_ids': ['forged'] if forged and role == 'critic' else []}
        result[role] = ScriptedFakeModel([{'kind': 'result', 'payload': payload}] * 4)
    return result


def assemble(tmp_path, *, check=None, case=0, mode='autonomous', missing=False, forged=False, yield_steps=False):
    pack = json.loads((Path(__file__).parents[2] / 'eval/fixtures/market/packs.json').read_text())
    series = [market_history.HistorySeries.model_validate(s) for s in pack['series']]
    events = [market_events.EventRecord.model_validate(e) for e in pack['cases'][case]['events']]
    tools = ToolRegistry()
    dep = market_history.MarketDependencies(market_history.FixtureHistoryBackend([] if missing else series))
    market_history.register_tools(tools, dep)
    anomaly.register_tools(tools, dep)
    market_events.register_tools(tools, market_events.EventDependencies(market_events.FixtureEventBackend(events)))
    engine = create_engine('sqlite:///' + str(tmp_path / 'market.db'))
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as session:
        session.add(Conversation(id='market'))
        session.commit()
    ps = providers(check, forged)
    driver = MarketCoordinator(ps, mode=mode, yield_after_handoff=yield_steps)
    registry = WorkflowRegistry()
    registry.register(driver)
    dispatcher = FinancialMASDispatcher(sessions, registry, tools)
    driver.budget_reader = lambda run_id: RunBudget.model_validate(dispatcher.snapshot(run_id)['budget'])
    request = MarketInvestigationRequest(symbol='DEMO', as_of=pack['cases'][case]['as_of'], sector_benchmark=series[1].symbol)
    run = dispatcher.create('market', request, mode='auto', idempotency_key='investigation')
    return dispatcher, run, sessions, driver, ps, pack


def finish(d, run):
    for _ in range(20):
        result = asyncio.run(d.start(run.id))
        if result.status in ('completed', 'failed', 'cancelled'):
            return result
    raise AssertionError('did not finish bounded execution')


@pytest.mark.parametrize('mode', ['autonomous', 'fixed', 'single'])
@pytest.mark.parametrize('summary', [
    'The announcement caused the price decline. Causality is confirmed.',
    '公告导致股价下跌，因果关系已确定。',
    'Cannot prove that the announcement caused the price decline.',
    '无法证明 X 导致 Y；先后发生不能证明因果关系。',
])
def test_model_causal_prose_is_audit_only_including_negation(tmp_path, mode, summary):
    d, run, sessions, _, ps, _ = assemble(tmp_path, mode=mode)
    for role, provider in ps.items():
        provider.responses = [ModelResponse(kind='result', payload={
            'role': role, 'action': 'finding', 'summary': summary,
            'hypotheses': [{'explanation': 'Company event association',
                            'disposition': 'supported'}]})]
    assert finish(d, run).status == 'completed'
    artifact = json.loads(d.get_run(run.id).final_answer)
    assert summary not in json.dumps(artifact, ensure_ascii=False)
    assert all(h['disposition'] == 'unverified' for h in artifact['hypotheses'])
    assert all(f['tool_result_id'] for f in artifact['numeric_facts'])
    assert 'Associations are unverified hypotheses; no confirmed causality.' in artifact['limitations']
    with sessions() as session:
        outputs = session.scalars(select(FinancialInvocation).where(
            FinancialInvocation.run_id == run.id, FinancialInvocation.kind == 'model')).all()
        assert outputs and all(row.output['summary'] == summary for row in outputs)


@pytest.mark.parametrize('explanation', [
    'The announcement caused the price decline.', '公告确定导致下跌。',
])
def test_causal_assertion_cannot_replace_bounded_hypothesis(tmp_path, explanation):
    d, run, _, _, ps, _ = assemble(tmp_path, mode='single')
    ps['coordinator'].responses = [ModelResponse(kind='result', payload={
        'role': 'coordinator', 'action': 'finding', 'summary': 'unsupported claim',
        'hypotheses': [{'explanation': explanation, 'disposition': 'supported'}]})]
    assert finish(d, run).status == 'failed'
    assert not d.get_run(run.id).final_answer


def test_roles_actual_tools_and_resolvable_numeric_audit(tmp_path):
    d, run, sessions, driver, ps, _ = assemble(tmp_path)
    assert finish(d, run).status == 'completed'
    artifact = json.loads(d.get_run(run.id).final_answer)
    assert len(artifact['numeric_facts']) >= 4
    assert all(len(ps[r].calls) == 1 for r in ROLES)
    assert len({ps[r].calls[0][0]['content'] for r in ROLES}) == 5
    assert driver.specialists.get('critic').allowed_tools == frozenset()
    with sessions() as session:
        for fact in artifact['numeric_facts']:
            row = session.get(ToolResult, fact['tool_result_id'])
            assert row and session.get(ToolCall, row.tool_call_id).run_id == run.id
            assert row.data[fact['name'].split('.')[1]] == fact['value']
    assert all(h['disposition'] == 'unverified' for h in artifact['hypotheses'])


@pytest.mark.parametrize('close,expected_return,expected_excess,expected_strength', [
    (200., 100., 75., .6),
    (50., -50., -75., -.6),
    (100., 0., -25., -.2),
])
def test_actual_tool_artifact_preserves_metric_values_and_units(
        tmp_path, close, expected_return, expected_excess, expected_strength):
    d, run, sessions, _, _, pack = assemble(tmp_path)
    series = [market_history.HistorySeries.model_validate(s) for s in pack['series']]
    asset = series[0]
    benchmark = series[1]
    # Independent known paths: asset return +100/-50/0 percent, benchmark +25.
    for source, latest in ((asset, close), (benchmark, 125.)):
        for bar in source.bars[:21]:
            price = latest if bar is source.bars[20] else 100.
            for field in ('open', 'high', 'low', 'close'):
                setattr(bar, field, price)
            bar.volume = 250. if bar is source.bars[20] else 100.
    market_benchmark = benchmark.model_copy(deep=True, update={'symbol': 'SPY'})
    tools = ToolRegistry()
    dep = market_history.MarketDependencies(
        market_history.FixtureHistoryBackend([asset, benchmark, market_benchmark]))
    market_history.register_tools(tools, dep)
    anomaly.register_tools(tools, dep)
    tools.register(d.tools.get('get_event_evidence'))
    d.tools = tools
    assert finish(d, run).status == 'completed'
    artifact = json.loads(d.get_run(run.id).final_answer)
    facts = {fact['name']: fact for fact in artifact['numeric_facts']}
    expected = {'return_pct': (expected_return, 'percent'),
                'excess_return_pct': (expected_excess, 'percentage_points'),
                'volume_ratio_20': (2.5, 'ratio'),
                'relative_strength': (expected_strength, 'ratio')}
    assert set(facts) == {f'{check}.{field}' for check in ('market', 'sector') for field in expected}
    with sessions() as session:
        for check in ('market', 'sector'):
            for field, (value, unit) in expected.items():
                fact = facts[f'{check}.{field}']
                assert fact['value'] == pytest.approx(value)
                assert fact['unit'] == unit
                result = session.get(ToolResult, fact['tool_result_id'])
                assert session.get(ToolCall, result.tool_call_id).run_id == run.id
                output = anomaly.MarketAnomalyOutput.model_validate(result.data)
                assert getattr(output, field) == fact['value']
                assert fact['evidence_id'] == output.result_ref


@pytest.mark.parametrize('check,expected', [('history', 'get_market_history'), ('events', 'get_event_evidence'), ('sector', 'calculate_market_anomaly')])
def test_evidence_challenge_changes_next_actual_tool(tmp_path, check, expected):
    d, run, sessions, _, ps, _ = assemble(tmp_path, check=check)
    assert finish(d, run).status == 'completed'
    with sessions() as session:
        invocation = session.scalar(select(FinancialInvocation).where(FinancialInvocation.invocation_key == f'check:1:{check}'))
        assert invocation is not None
        calls = session.scalars(select(ToolCall)).all()
        assert len(calls) == 5
        assert calls[3].tool_name == expected
    assert len(ps['critic'].calls) == 3
    assert d.snapshot(run.id)['budget']['rounds'] == 3


def test_restored_checkpoints_do_not_rebill_and_keep_refs(tmp_path):
    d, run, sessions, driver, ps, _ = assemble(tmp_path, check='history', yield_steps=True)
    assert asyncio.run(d.start(run.id)).status == 'executing'
    registry = WorkflowRegistry()
    replacement = MarketCoordinator(ps, yield_after_handoff=True)
    registry.register(replacement)
    restored = FinancialMASDispatcher(sessions, registry, d.tools)
    replacement.budget_reader = lambda run_id: RunBudget.model_validate(restored.snapshot(run_id)['budget'])
    assert finish(restored, run).status == 'completed'
    budget = restored.snapshot(run.id)['budget']
    assert budget['model_calls'] == 9 and budget['tool_calls'] == 5
    assert finish(restored, run).status == 'completed'
    assert restored.snapshot(run.id)['budget'] == budget


def test_new_counterevidence_drives_critic_check(tmp_path):
    d, run, sessions, driver, _, _ = assemble(tmp_path)
    class EvidenceCritic:
        async def complete(self, messages, **kwargs):
            task = json.loads(messages[1]['content'].removeprefix('<task_data>').removesuffix('</task_data>'))
            events = [e for e in task['evidence'] if e['source_type'] != 'market_tool']
            return ModelResponse(kind='result', payload={'role': 'critic', 'action': 'challenge',
                'summary': 'Event association competes with sector explanation; check independent price history.',
                'missing_checks': ['history'] if events else [],
                'hypotheses': [{'explanation': 'Company event association',
                    'against_ids': [events[0]['id']] if events else [], 'disposition': 'contradicted'}]})
    object.__setattr__(driver.specialists.get('critic'), 'provider', EvidenceCritic())
    assert finish(d, run).status == 'completed'
    artifact = json.loads(d.get_run(run.id).final_answer)
    assert next(h for h in artifact['hypotheses'] if h['explanation'] == 'Company event association')['against_ids']
    with sessions() as s:
        assert s.scalar(select(FinancialInvocation).where(FinancialInvocation.invocation_key == 'check:1:history'))
    # Same critic policy/tools/budget, no counterevidence: no adaptive history call.
    empty_dir = tmp_path / 'empty'
    empty_dir.mkdir()
    baseline, base_run, base_sessions, base_driver, _, _ = assemble(empty_dir, case=7)
    object.__setattr__(base_driver.specialists.get('critic'), 'provider', EvidenceCritic())
    assert finish(baseline, base_run).status == 'completed'
    with base_sessions() as s:
        assert s.scalar(select(FinancialInvocation).where(FinancialInvocation.invocation_key == 'check:1:history')) is None
        assert len(s.scalars(select(ToolCall)).all()) == 3


def test_failed_actual_tool_is_explicit_partial(tmp_path):
    d, run, _, _, _, _ = assemble(tmp_path)
    class BrokenHistory:
        def load(self, symbol):
            raise ValueError('synthetic dependency failure')
    # Replace the injected tool registry with actual W2 handlers on a broken dependency.
    tools = ToolRegistry()
    dep = market_history.MarketDependencies(BrokenHistory())
    market_history.register_tools(tools, dep)
    anomaly.register_tools(tools, dep)
    market_events.register_tools(tools, market_events.EventDependencies())
    d.tools = tools
    assert finish(d, run).status == 'completed'
    artifact = json.loads(d.get_run(run.id).final_answer)
    assert artifact['numeric_facts'] == []
    assert 'market: tool failed' in artifact['limitations']


def test_missing_data_degrades_without_numbers(tmp_path):
    d, run, _, _, _, _ = assemble(tmp_path, missing=True)
    assert finish(d, run).status == 'completed'
    artifact = json.loads(d.get_run(run.id).final_answer)
    assert artifact['status'] == 'insufficient_evidence' and artifact['numeric_facts'] == []
    assert any('unavailable' in x for x in artifact['limitations'])


def test_forged_reference_fails_without_artifact(tmp_path):
    d, run, _, _, _, _ = assemble(tmp_path, forged=True)
    assert finish(d, run).status == 'failed'
    assert d.snapshot(run.id)['checkpoint']['artifact_ids'] == []


@pytest.mark.parametrize('case', range(10))
def test_temporal_and_injection_fixture_boundary(tmp_path, case):
    d, run, _, _, _, pack = assemble(tmp_path, case=case)
    assert finish(d, run).status == 'completed'
    artifact = json.loads(d.get_run(run.id).final_answer)
    cutoff = datetime.fromisoformat(pack['cases'][case]['as_of'])
    for evidence in artifact['evidence']:
        assert datetime.fromisoformat(evidence['published_at']) <= cutoff
        assert datetime.fromisoformat(evidence['available_at']) <= cutoff
    assert all(h['disposition'] == 'unverified' for h in artifact['hypotheses'])


def test_cancel_preserves_no_final_artifact(tmp_path):
    d, run, _, _, _, _ = assemble(tmp_path, yield_steps=True)
    asyncio.run(d.start(run.id))
    assert d.cancel(run.id, d.get_run(run.id).version).status == 'cancelled'
    assert finish(d, run).status == 'cancelled'
    assert not d.snapshot(run.id)['checkpoint']['artifact_ids']


def test_timeout_provider_and_budget_fail_closed(tmp_path):
    d, run, _, driver, _, _ = assemble(tmp_path)
    class Timeout:
        async def complete(self, messages, **kwargs):
            raise ModelProviderError('dependency_timeout', 'synthetic timeout')
    object.__setattr__(driver.specialists.get('coordinator'), 'provider', Timeout())
    assert finish(d, run).error_code == 'dependency_timeout'
    assert not d.snapshot(run.id)['checkpoint']['artifact_ids']
    # A separate non-timeout driver establishes the request's independent budget ceiling.
    object.__setattr__(driver.specialists.get('coordinator'), 'provider', providers()['coordinator'])
    other = d.create('market', MarketInvestigationRequest(symbol='DEMO', as_of='2026-09-29T20:10:00Z', max_llm_calls=1), mode='auto', idempotency_key='budget')
    assert finish(d, other).status == 'failed'


@pytest.mark.parametrize('mode,calls', [('fixed', 5), ('single', 1)])
def test_baseline_hooks_same_tools_no_dynamic_calls(tmp_path, mode, calls):
    d, run, _, _, _, _ = assemble(tmp_path, mode=mode, check='history')
    assert finish(d, run).status == 'completed'
    assert d.snapshot(run.id)['budget']['model_calls'] == calls
    assert d.snapshot(run.id)['budget']['rounds'] == 1


def test_lowered_round_budget_includes_initial_investigation(tmp_path):
    d, _, sessions, _, _, _ = assemble(tmp_path, check='history')
    run = d.create('market', MarketInvestigationRequest(symbol='DEMO',
        as_of='2026-09-29T20:10:00Z', sector_benchmark='SECTOR'),
        mode='auto', idempotency_key='one-round', budget=RunBudget(max_rounds=1))
    assert finish(d, run).status == 'completed'
    assert d.snapshot(run.id)['budget']['rounds'] == 1
    with sessions() as s:
        assert s.scalar(select(FinancialInvocation).where(
            FinancialInvocation.run_id == run.id,
            FinancialInvocation.invocation_key == 'check:1:history')) is None


@pytest.mark.parametrize('clear,ceiling,expected', [(True, 7, 7), (False, 7, 7), (False, 6, 5)])
def test_current_challenge_and_effective_budget_before_next_tool(tmp_path, clear, ceiling, expected):
    d, _, sessions, driver, _, _ = assemble(tmp_path, check='history')
    if clear:
        object.__setattr__(driver.specialists.get('critic'), 'provider', ScriptedFakeModel([
            {'kind': 'result', 'payload': {'role': 'critic', 'action': 'challenge', 'summary': 'Check missing history', 'missing_checks': ['history']}},
            {'kind': 'result', 'payload': {'role': 'critic', 'action': 'verdict', 'summary': 'History checked; request resolved', 'missing_checks': []}}]))
    run = d.create('market', MarketInvestigationRequest(symbol='DEMO',
        as_of='2026-09-29T20:10:00Z', sector_benchmark='SECTOR'), mode='auto',
        idempotency_key='effective-limit', budget=RunBudget(max_model_calls=ceiling))
    assert finish(d, run).status == 'completed'
    budget = d.snapshot(run.id)['budget']
    assert budget['model_calls'] == expected
    assert budget['tool_calls'] == (4 if expected == 7 else 3)
    with sessions() as s:
        assert s.scalar(select(FinancialInvocation).where(FinancialInvocation.run_id == run.id,
            FinancialInvocation.invocation_key == 'check:2:history')) is None
    artifact = json.loads(d.get_run(run.id).final_answer)
    if clear:
        assert 'history' not in artifact['limitations']


def test_missing_budget_reader_defers_without_spending_followup(tmp_path):
    d, run, _, driver, _, _ = assemble(tmp_path, check='history')
    driver.budget_reader = None
    assert finish(d, run).status == 'completed'
    assert d.snapshot(run.id)['budget']['model_calls'] == 5
    assert 'Effective budget reader unavailable; adaptive checks deferred' in json.loads(d.get_run(run.id).final_answer)['limitations']


def test_successful_followup_retires_same_check_data_warning(tmp_path):
    d, run, _, driver, _, pack = assemble(tmp_path, check='events')
    records = [market_events.EventRecord.model_validate(e) for e in pack['cases'][0]['events']]
    class NewlyAvailableEvents:
        def __init__(self):
            self.calls = 0
        def load(self, symbol):
            self.calls += 1
            return [] if self.calls == 1 else records
    # Reassemble only the registered event dependency; actual W2 handler retained.
    original_tools = d.tools
    tools = ToolRegistry()
    for name in ('get_market_history', 'calculate_market_anomaly'):
        tools.register(original_tools.get(name))
    market_events.register_tools(tools, market_events.EventDependencies(NewlyAvailableEvents()))
    d.tools = tools
    driver.max_rounds = 2
    assert finish(d, run).status == 'completed'
    artifact = json.loads(d.get_run(run.id).final_answer)
    assert not any(warning.startswith('events:') for warning in artifact['limitations'])
    assert any(e['source_type'] != 'market_tool' for e in artifact['evidence'])


@pytest.mark.parametrize('case', [0, 6, 7])
def test_reusable_synthetic_policy_separate_calls_and_contexts(tmp_path, case):
    d, run, sessions, driver, _, _ = assemble(tmp_path, case=case)
    for role in ROLES:
        object.__setattr__(driver.specialists.get(role), 'provider', SyntheticMarketModel(role))
    assert finish(d, run).status == 'completed'
    with sessions() as s:
        calls = s.scalars(select(FinancialInvocation).where(FinancialInvocation.kind == 'model')).all()
        assert set(c.role for c in calls) == set(ROLES)
    assert json.loads(d.get_run(run.id).final_answer)['status'] == 'partial'


@pytest.mark.parametrize('crash_key,exhausted', [(key, False) for key in [
    'market:initial', 'coordinator:initial', 'price_volume:initial',
    'macro_sector:initial', 'event:initial', 'critic:initial',
    'check:1:history', 'coordinator:round:1', 'critic:round:1',
]] + [('coordinator:initial', True)])
def test_actual_legacy_driver_upgrade_result_before_checkpoint(tmp_path, monkeypatch, crash_key, exhausted):
    import subprocess
    import sys
    import types
    from datetime import timezone
    from agent.shared.dispatch import RuntimeContext

    # Immutable pre-unit-fix blob, rather than a simulated legacy checkpoint.
    source = subprocess.check_output(['git', 'cat-file', 'blob',
        'f0e408e6f06b79b7ba5e55c3f96bfab2fdf165fd'], text=True)
    module = types.ModuleType('market_legacy_upgrade_fixture')
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(source, '<legacy-market-driver>', 'exec'), module.__dict__)
    d, run, sessions, _, ps, _ = assemble(tmp_path, check='history', yield_steps=True)
    if exhausted:
        run = d.create('market', MarketInvestigationRequest(symbol='DEMO',
            as_of='2026-09-29T20:10:00Z', sector_benchmark='SECTOR'),
            mode='auto', idempotency_key='upgrade-exhausted',
            budget=RunBudget(max_model_calls=1))
    clock = [datetime(2026, 10, 9, tzinfo=timezone.utc)]
    d.clock = lambda: clock[0]
    legacy = module.MarketCoordinator(ps, yield_after_handoff=True)
    legacy.budget_reader = lambda rid: RunBudget.model_validate(d.snapshot(rid)['budget'])
    registry = WorkflowRegistry()
    registry.register(legacy)
    d.drivers = registry
    class Crash(BaseException):
        pass
    original = RuntimeContext.record_result
    def crash(self, key, output):
        original(self, key, output)
        if key == crash_key:
            raise Crash()
    monkeypatch.setattr(RuntimeContext, 'record_result', crash)
    with pytest.raises(Crash):
        finish(d, run)
    before = d.snapshot(run.id)
    with sessions() as session:
        history = {row.invocation_key: (row.input_hash, row.output, row.attempts)
            for row in session.scalars(select(FinancialInvocation)).all()}
    clock[0] += timedelta(seconds=31)
    current = MarketCoordinator(ps, yield_after_handoff=True)
    registry = WorkflowRegistry()
    registry.register(current)
    restored = FinancialMASDispatcher(sessions, registry, d.tools, clock=d.clock)
    current.budget_reader = lambda rid: RunBudget.model_validate(restored.snapshot(rid)['budget'])
    if exhausted:
        monkeypatch.setattr(RuntimeContext, 'record_result', original)
        calls = sum(len(p.calls) for p in ps.values())
        result = finish(restored, run)
        assert result.status == 'failed' and result.final_answer is None
        assert not restored.snapshot(run.id)['checkpoint']['artifact_ids']
        assert restored.snapshot(run.id)['budget']['model_calls'] == 1
        assert sum(len(p.calls) for p in ps.values()) == calls == 1
        assert asyncio.run(restored.start(run.id)).status == 'failed'
        with sessions() as session:
            for key, expected in history.items():
                row = session.scalar(select(FinancialInvocation).where(
                    FinancialInvocation.run_id == run.id, FinancialInvocation.invocation_key == key))
                assert (row.input_hash, row.output, row.attempts) == expected
        return
    # A second crash after corrected success proves v2 restart does not rebill.
    corrected_key = crash_key + ':units:v2'
    def crash_corrected(self, key, output):
        original(self, key, output)
        if key == corrected_key:
            raise Crash()
    monkeypatch.setattr(RuntimeContext, 'record_result', crash_corrected)
    if crash_key not in ('market:initial', 'check:1:history'):
        with pytest.raises(Crash):
            finish(restored, run)
        corrected_budget = restored.snapshot(run.id)['budget']
        corrected_calls = sum(len(p.calls) for p in ps.values())
        clock[0] += timedelta(seconds=31)
        monkeypatch.setattr(RuntimeContext, 'record_result', original)
        assert asyncio.run(restored.start(run.id)).status == 'executing'
        assert restored.snapshot(run.id)['budget'] == corrected_budget
        assert sum(len(p.calls) for p in ps.values()) == corrected_calls
    else:
        monkeypatch.setattr(RuntimeContext, 'record_result', original)
    assert finish(restored, run).status == 'completed'
    artifact = json.loads(restored.get_run(run.id).final_answer)
    assert all(f['unit'] == 'percent' for f in artifact['numeric_facts']
               if f['name'].endswith('.return_pct'))
    assert restored.snapshot(run.id)['budget']['model_calls'] == 9 + (
        crash_key not in ('market:initial', 'check:1:history'))
    assert restored.snapshot(run.id)['budget']['tool_calls'] == 5
    with sessions() as session:
        for key, expected in history.items():
            row = session.scalar(select(FinancialInvocation).where(
                FinancialInvocation.run_id == run.id, FinancialInvocation.invocation_key == key))
            assert (row.input_hash, row.output, row.attempts) == expected
        for fact in artifact['numeric_facts']:
            output = session.get(ToolResult, fact['tool_result_id'])
            assert output.data[fact['name'].split('.')[1]] == fact['value']
    # The persisted legacy checkpoint was not mutated by normalization.
    if before['checkpoint']['state']['numeric_facts']:
        assert before['checkpoint']['state']['numeric_facts'][0]['unit'] == 'percentage_points'
