"""Synthetic SQLite integration through public runtime and actual W3 tools."""
import asyncio
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from agent.llm import ScriptedFakeModel, ModelResponse
from agent.portfolio_mas import PortfolioDriver, PortfolioDependencies, SyntheticPortfolioModel
from agent.shared import FinancialMASDispatcher, WorkflowRegistry, PortfolioReviewRequest, RunBudget
from agent.tools import portfolio_snapshot as s, portfolio_risk as r, allocation as a
from agent.tools.registry import ToolRegistry
from db.base import Base
from db.models import Conversation, FinancialInvocation, FinancialArtifact, ToolResult, ToolCall

NOW = datetime(2026, 1, 8, tzinfo=timezone.utc)
ROLES = ('coordinator', 'opportunity', 'risk', 'constraint', 'verifier')


def snapshot(missing_price=False, cash='200', empty=False):
    return s.SnapshotRecord(snapshot_id='saved', source='synthetic:immutable', effective_at=NOW,
        cash=cash, currency='USD', snapshot_kind='demo',
        holdings=() if empty else (s.Holding(symbol='MU', quantity='8', currency='USD'),),
        quotes=() if missing_price or empty else (s.ValuationQuote(symbol='MU', price='100', currency='USD', effective_at=NOW, available_at=NOW, source='synthetic:quotes'),))


def history(record, as_of):
    return (r.AssetHistory(symbol='MU', currency='USD', source='synthetic:calendar-and-prices',
        adjustment='total_return', exchange_timezone='UTC', bars=tuple(
            r.HistoryBar(date=(NOW-timedelta(days=3-i)).date(), price=str(p),
                         close_at=NOW-timedelta(days=3-i), available_at=NOW-timedelta(days=3-i))
            for i,p in enumerate([90, 95, 93, 100]))),)


def assemble(tmp_path, *, record=None, providers=None, classes=True, history_loader=history, mode='full', yield_revision=False, resolver=None):
    record = record or snapshot()
    source = tmp_path / 'holdings.json'
    source.write_text(record.model_dump_json(), encoding='utf-8')
    digest = sha256(source.read_bytes()).hexdigest()
    def loader(key):
        assert key == 'saved'
        return s.SnapshotRecord.model_validate_json(source.read_text(encoding='utf-8'))
    deps = PortfolioDependencies(loader, history_loader, {'MU': a.AssetClassification(asset_class='equity', sector='technology', source='synthetic:classification')} if classes else {})
    providers = providers or {role:SyntheticPortfolioModel(role) for role in ROLES}
    driver = PortfolioDriver(providers, deps, mode=mode, yield_after_revision=yield_revision, artifact_resolver=resolver)
    engine = create_engine('sqlite:///' + str(tmp_path/'runtime.db'), connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as db:
        db.add(Conversation(id='c'))
        db.commit()
    workflows = WorkflowRegistry()
    workflows.register(driver)
    tools = ToolRegistry()
    s.register_tools(tools, {'snapshot_loader':loader})
    r.register_tools(tools)
    a.register_tools(tools)
    d = FinancialMASDispatcher(sessions, workflows, tools)
    return d, driver, sessions, source, digest, providers


def run(d, constraints=None, budget=None, artifact=None):
    value = d.create('c', PortfolioReviewRequest(portfolio_snapshot_id='saved', as_of=NOW,
        user_constraints=constraints or {}, market_artifact_id=artifact), idempotency_key='portfolio', mode='auto', budget=budget)
    return value, asyncio.run(d.start(value.id))


def artifact(d, value):
    return json.loads(d.get_run(value.id).final_answer)


def test_standalone_feasible_independent_calls_audit_and_immutable(tmp_path):
    d, driver, sessions, source, digest, providers = assemble(tmp_path)
    value, completed = run(d, {'min_cash_weight': .2, 'max_sector_weight': {'technology': .8}, 'weight_tolerance': 1e-9})
    assert completed.status == 'completed', completed.error_code
    result = artifact(d, value)
    assert result['status'] == 'feasible'
    assert result['snapshot_id'] == 'saved' and result['current_weights']['MU'] == .8
    assert result['proposed_weights']['CASH'] == 1
    assert all(len(providers[role].calls) == 1 for role in ROLES)
    assert len({providers[role].calls[0][0]['content'] for role in ROLES}) == 5
    with sessions() as db:
        persisted = {row.id for row in db.scalars(select(ToolResult))}
        assert set(result['evidence_ids']) <= persisted
        assert result['risk_comparison']['before']['tool_result_id'] in persisted
        assert result['risk_comparison']['after']['tool_result_id'] in persisted
        assert result['simulation']['tool_result_id'] in persisted
        checks = db.scalars(select(ToolCall).where(ToolCall.tool_name.in_(['validate_allocation','generate_feasible_candidates']))).all()
        assert all(float(call.input_data['constraints']['weight_tolerance']) == 1e-9 for call in checks)
        assert all(call.input_data['constraints']['max_sector_weight'] == {'TECHNOLOGY': '0.8'} for call in checks)
        count = len(db.scalars(select(FinancialInvocation)).all())
    assert sha256(source.read_bytes()).hexdigest() == digest
    assert asyncio.run(d.start(value.id)).status == 'completed'
    with sessions() as db:
        assert len(db.scalars(select(FinancialArtifact)).all()) == 1
        assert len(db.scalars(select(FinancialInvocation)).all()) == count
    assert driver.specialists.get('verifier').allowed_tools == frozenset()


@pytest.mark.parametrize('case,expected', [('infeasible','infeasible'), ('missing','insufficient_data'), ('classification','insufficient_data'), ('zero_cash','feasible'), ('cash_only','feasible'), ('no_calendar','insufficient_data')])
def test_status_boundaries(tmp_path, case, expected):
    record = snapshot(missing_price=case=='missing', cash='0' if case=='zero_cash' else '200', empty=case in {'cash_only','no_calendar'})
    d, _, _, source, digest, providers = assemble(tmp_path, record=record, classes=case!='classification', history_loader=(lambda *_:()) if case=='no_calendar' else history)
    constraints = {'min_cash_weight':.5, 'max_weight_by_symbol':{'CASH':.2}} if case=='infeasible' else {'max_weight_by_symbol':{'CASH':.1}, 'max_equity_weight':1} if case=='classification' else {}
    value, completed = run(d, constraints)
    assert completed.status == 'completed', completed.error_code
    assert artifact(d, value)['status'] == expected
    assert all(providers[role].calls for role in ROLES)
    assert sha256(source.read_bytes()).hexdigest() == digest


def scripted(role, weights=None, action='finding', missing=None):
    return {'kind':'result', 'payload': {'role':role, 'action':action, 'summary':'Synthetic test', 'proposed_weights':weights or {}, 'missing_checks':missing or []}}


def test_actual_revision_and_restart_without_rebilling(tmp_path):
    providers = {role:SyntheticPortfolioModel(role) for role in ROLES}
    providers['coordinator'] = ScriptedFakeModel([scripted('coordinator', {'MU':1, 'CASH':0}), scripted('coordinator', {'MU':.5,'CASH':.5})])
    d, driver, sessions, source, digest, _ = assemble(tmp_path, providers=providers, yield_revision=True)
    value, unfinished = run(d, {'max_weight_by_symbol': {'MU': .6}})
    assert unfinished.status == 'executing', unfinished.error_code
    assert d.snapshot(value.id)['checkpoint']['state']['phase'] == 'revision_ready'
    assert d.snapshot(value.id)['checkpoint']['state']['proposed_weights']['MU'] == 1
    fresh = {role:SyntheticPortfolioModel(role) for role in ROLES}
    fresh['coordinator'] = ScriptedFakeModel([scripted('coordinator', {'MU':.5,'CASH':.5})])
    replacement = PortfolioDriver(fresh, driver.dependencies)
    workflows = WorkflowRegistry()
    workflows.register(replacement)
    restarted = FinancialMASDispatcher(sessions, workflows, d.tools)
    assert asyncio.run(restarted.start(value.id)).status == 'completed'
    result = artifact(restarted, value)
    assert result['status'] == 'feasible' and result['proposed_weights']['MU'] == .5
    assert result['risk_comparison']['before']['concentration'] == .8
    assert result['risk_comparison']['after']['concentration'] == .5
    assert all(len(fresh[role].calls) == 1 for role in ROLES)
    assert restarted.snapshot(value.id)['budget']['rounds'] == 2
    with sessions() as db:
        keys = [row.invocation_key for row in db.scalars(select(FinancialInvocation))]
        assert len(keys) == len(set(keys))
    assert sha256(source.read_bytes()).hexdigest() == digest


@pytest.mark.parametrize('attack', ['constraint_bypass', 'no_quote', 'verifier_reject', 'malformed'])
def test_unverified_malicious_proposal_never_feasible(tmp_path, attack):
    providers = {role:SyntheticPortfolioModel(role) for role in ROLES}
    weights = {'MU':1,'CASH':0} if attack=='constraint_bypass' else {'EVIL':.5,'CASH':.5} if attack=='no_quote' else {'MU':-1,'CASH':2} if attack=='malformed' else {'MU':.5,'CASH':.5}
    providers['coordinator'] = ScriptedFakeModel([scripted('coordinator',weights)]*2)
    providers['verifier'] = ScriptedFakeModel([scripted('verifier',action='reject' if attack=='verifier_reject' else 'approve')]*2)
    d, *_ = assemble(tmp_path, providers=providers)
    value, completed = run(d, {'max_weight_by_symbol':{'MU':.6}})
    assert completed.status == 'completed', completed.error_code
    assert artifact(d, value)['status'] == 'insufficient_data'


@pytest.mark.parametrize('mode,calls', [('full',5), ('fixed',5), ('no_verifier',4), ('single',1)])
def test_baselines_identical_tools_data_budget(tmp_path, mode, calls):
    d, _, sessions, *_ = assemble(tmp_path, mode=mode)
    value, completed = run(d)
    assert completed.status == 'completed'
    assert artifact(d,value)['status'] == 'feasible'
    budget = d.snapshot(value.id)['budget']
    assert budget['model_calls'] == calls and budget['tool_calls'] == 6
    assert budget['max_model_calls'] == 16 and budget['max_tool_calls'] == 20


def test_fixed_pipeline_is_single_pass_and_retains_verifier(tmp_path):
    providers = {role:SyntheticPortfolioModel(role) for role in ROLES}
    providers['coordinator'] = ScriptedFakeModel([
        scripted('coordinator', {'MU':1, 'CASH':0})])
    d, _, sessions, _, _, _ = assemble(tmp_path, providers=providers, mode='fixed')
    value, completed = run(d, {'max_weight_by_symbol': {'MU': .6}})
    assert completed.status == 'completed'
    result = artifact(d, value)
    budget = d.snapshot(value.id)['budget']
    assert result['status'] == 'insufficient_data'
    assert budget['rounds'] == 1 and budget['model_calls'] == 5
    with sessions() as db:
        roles = {row.role for row in db.scalars(select(FinancialInvocation).where(
            FinancialInvocation.run_id == value.id, FinancialInvocation.kind == 'model'))}
    assert roles == {'coordinator', 'opportunity', 'risk', 'constraint', 'verifier'}


def test_cancel_during_role_and_deadline(tmp_path):
    d, driver, sessions, *_ = assemble(tmp_path)
    value = d.create('c', PortfolioReviewRequest(portfolio_snapshot_id='saved',as_of=NOW), idempotency_key='cancel',mode='auto')
    class Cancel:
        async def complete(self, messages, *, request_id=None):
            current = d.get_run(value.id)
            d.cancel(value.id,current.version)
            return ModelResponse.model_validate(scripted('opportunity'))
    from agent.shared import SpecialistSpec
    driver.specialists._roles['opportunity'] = SpecialistSpec('opportunity',Cancel(),'cancel fixture')
    assert asyncio.run(d.start(value.id)).status == 'cancelled'
    with sessions() as db:
        assert not db.scalars(select(FinancialArtifact)).all()
    other = d.create('c',PortfolioReviewRequest(portfolio_snapshot_id='saved',as_of=NOW),idempotency_key='timeout',mode='auto',budget=RunBudget(max_active_seconds=.001))
    assert asyncio.run(d.start(other.id)).status in {'expired','failed'}


def test_optional_market_unavailable_independent_and_bad_resolver_scope(tmp_path):
    d, *_ = assemble(tmp_path, resolver=lambda *_:None)
    value, result = run(d, artifact='absent')
    assert result.status == 'completed'
    assert artifact(d,value)['status'] == 'feasible'
    assert any('Market artifact unavailable' in text for text in artifact(d,value)['limitations'])


def test_pause_mid_revision_restores_cached_contexts(tmp_path):
    providers = {role:SyntheticPortfolioModel(role) for role in ROLES}
    d, driver, sessions, *_ = assemble(tmp_path, providers=providers)
    value = d.create('c',PortfolioReviewRequest(portfolio_snapshot_id='saved',as_of=NOW,
        user_constraints={'max_weight_by_symbol':{'MU':.6}}),idempotency_key='mid-revision',mode='auto')
    class PauseDuringRevision:
        def __init__(self):
            self.calls = 0
        async def complete(self,messages,*,request_id=None):
            self.calls += 1
            if self.calls == 2:
                current = d.get_run(value.id)
                d.pause(value.id,current.version)
            return ModelResponse.model_validate(scripted('coordinator',{'MU':1,'CASH':0} if self.calls == 1 else {'MU':.5,'CASH':.5}))
    from agent.shared import SpecialistSpec
    original = driver.specialists.get('coordinator')
    driver.specialists._roles['coordinator'] = SpecialistSpec('coordinator',PauseDuringRevision(),original.system_prompt,original.allowed_tools)
    paused = asyncio.run(d.start(value.id))
    assert paused.status == 'paused'
    assert d.snapshot(value.id)['checkpoint']['state']['phase'] == 'round1'
    d.resume(value.id,paused.version)
    fresh = {role:SyntheticPortfolioModel(role) for role in ROLES}
    fresh['coordinator'] = ScriptedFakeModel([scripted('coordinator',{'MU':.5,'CASH':.5})])
    workflows = WorkflowRegistry()
    workflows.register(PortfolioDriver(fresh,driver.dependencies))
    restarted = FinancialMASDispatcher(sessions,workflows,d.tools)
    completed = asyncio.run(restarted.start(value.id))
    assert completed.status == 'completed', completed.error_code
    assert artifact(restarted,value)['status'] == 'feasible'
    assert fresh['opportunity'].calls == []  # completed round1 call survives restart
    assert len(fresh['coordinator'].calls) == 1  # only interrupted call retries
    assert restarted.snapshot(value.id)['budget']['rounds'] == 2


def test_resolver_receives_immutable_request_and_scope_guard(tmp_path):
    from agent.shared import MarketInvestigationArtifact
    seen = []
    def resolver(run_id,conversation_id,request):
        seen.append((run_id,conversation_id,request.market_artifact_id))
        return MarketInvestigationArtifact(producing_run_id='peer',symbol='EVIL',as_of=NOW,status='partial')
    d, *_ = assemble(tmp_path,resolver=resolver)
    value, completed = run(d)
    assert completed.status == 'completed'
    assert seen == [(value.id,'c',None)]
    assert artifact(d,value)['status'] == 'feasible'
    assert any('outside authorized scope' in text for text in artifact(d,value)['limitations'])


def test_optional_resolver_timeout_preserves_standalone(tmp_path):
    def unavailable(*_):
        raise TimeoutError('peer unavailable')
    d, _, _, _, _, providers = assemble(tmp_path,resolver=unavailable)
    value, completed = run(d)
    assert completed.status == 'completed', completed.error_code
    result = artifact(d,value)
    assert result['status'] == 'feasible'
    assert all(providers[role].calls for role in ROLES)
    assert any('Market artifact unavailable' in text for text in result['limitations'])
    assert not any('peer unavailable' in text for text in result['limitations'])


@pytest.mark.parametrize('async_adapter', [False, True])
def test_failed_history_adapter_is_insufficient_data(tmp_path,async_adapter):
    def broken(*_):
        raise RuntimeError('private provider details')
    async def async_broken(*_):
        await asyncio.sleep(0)
        raise TimeoutError('private provider details')
    d, _, _, _, _, providers = assemble(tmp_path,history_loader=async_broken if async_adapter else broken)
    value, completed = run(d)
    assert completed.status == 'completed', completed.error_code
    result = artifact(d,value)
    assert result['status'] == 'insufficient_data'
    assert 'history_adapter_unavailable_or_invalid' in result['limitations']
    assert all(providers[role].calls for role in ROLES)


def test_async_history_and_resolver_supported(tmp_path):
    async def async_history(record,as_of):
        await asyncio.sleep(0)
        return history(record,as_of)
    async def async_resolver(*_):
        await asyncio.sleep(0)
        return None
    d, *_ = assemble(tmp_path,history_loader=async_history,resolver=async_resolver)
    value, completed = run(d)
    assert completed.status == 'completed'
    assert artifact(d,value)['status'] == 'feasible'


@pytest.mark.parametrize('action', ['cancel', 'deadline'])
def test_slow_history_does_not_block_event_loop_or_hide_intervention(tmp_path,action):
    entered = threading.Event()
    released = threading.Event()
    def slow(record,as_of):
        entered.set()
        released.wait(2)
        return history(record,as_of)
    d, _, sessions, _, _, providers = assemble(tmp_path,history_loader=slow)
    value = d.create('c',PortfolioReviewRequest(portfolio_snapshot_id='saved',as_of=NOW),
        idempotency_key=action,mode='auto',budget=RunBudget(max_active_seconds=.4 if action=='deadline' else 5))
    async def exercise():
        started = time.monotonic()
        task = asyncio.create_task(d.start(value.id))
        while not entered.is_set():
            assert time.monotonic()-started < 1
            await asyncio.sleep(.005)
        # This callback executes while synchronous history remains blocked.
        assert not released.is_set()
        if action == 'cancel':
            current = d.get_run(value.id)
            d.cancel(value.id,current.version)
            assert d.get_run(value.id).status == 'cancelled'
            released.set()
        result = await task
        elapsed = time.monotonic()-started
        released.set()  # release worker before asyncio.run's executor shutdown
        return result,elapsed
    completed,elapsed = asyncio.run(exercise())
    assert completed.status == ('cancelled' if action=='cancel' else 'failed')
    if action == 'deadline':
        assert completed.error_code == 'budget_exhausted'  # frozen W1 active deadline semantics
    assert elapsed < 1, 'runtime delivery must stop before blocking loader completes'
    assert all(not providers[role].calls for role in ROLES)
    with sessions() as db:
        assert not db.scalars(select(FinancialArtifact)).all()


def test_dependency_runtime_budget_guard_is_not_missing_data(tmp_path):
    from agent.shared import BudgetExhausted
    def interrupted(*_):
        raise BudgetExhausted('adapter interruption fixture')
    d, _, sessions, _, _, providers = assemble(tmp_path,resolver=interrupted)
    _, completed = run(d)
    assert completed.status == 'failed' and completed.error_code == 'budget_exhausted'
    assert all(not providers[role].calls for role in ROLES)
    with sessions() as db:
        assert not db.scalars(select(FinancialArtifact)).all()
