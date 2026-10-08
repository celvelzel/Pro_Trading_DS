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
    request = MarketInvestigationRequest(symbol='DEMO', as_of=pack['cases'][case]['as_of'], sector_benchmark=series[1].symbol)
    run = dispatcher.create('market', request, mode='auto', idempotency_key='investigation')
    return dispatcher, run, sessions, driver, ps, pack


def finish(d, run):
    for _ in range(20):
        result = asyncio.run(d.start(run.id))
        if result.status in ('completed', 'failed', 'cancelled'):
            return result
    raise AssertionError('did not finish bounded execution')


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
