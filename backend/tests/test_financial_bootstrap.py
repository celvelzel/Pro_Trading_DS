"""Fresh-process financial assembly, real worker entry and domain independence."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[2]


def process(code, tmp_path):
    env = os.environ.copy()
    env.pop("REDIS_URL", None)
    env["DATABASE_URL"] = "sqlite+aiosqlite:///" + (tmp_path / "isolated-agent.db").as_posix()
    env["PYTHONPATH"] = os.pathsep.join(str(p) for p in (ROOT, ROOT / "backend", ROOT / "lobster_quant"))
    result = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], env=env,
        cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize("enabled, absent", [
    ("market_investigation", "agent.portfolio_mas"),
    ("portfolio_rebalance", "agent.market_mas"),
])
def test_disabled_domain_is_not_imported(enabled, absent, tmp_path):
    process(f'''
        import sys
        from agent.financial import build_financial_dispatcher
        from agent.tools import default_registry
        before=set(tool.name for tool in default_registry.list())
        dispatcher=build_financial_dispatcher(lambda: None, enabled=('{enabled}',))
        assert '{absent}' not in sys.modules
        assert before == set(tool.name for tool in default_registry.list())
        assert len(before) == 7
    ''', tmp_path)


def test_worker_bootstraps_both_financial_drivers_in_fresh_process(tmp_path):
    output = process('''
        from db.base import Base
        import db.models
        from db.session import sync_engine, sync_session_factory
        from db.repositories.agent import create_conversation
        from agent.financial import build_financial_dispatcher
        from agent.financial_demo import DEMO_AS_OF, DEMO_SNAPSHOT_ID
        from agent.shared import MarketInvestigationRequest, PortfolioReviewRequest
        from workers.agent_tasks import run_agent
        Base.metadata.create_all(sync_engine())
        with sync_session_factory() as s:
            c=create_conversation(s, 'Explicit synthetic worker bootstrap test');s.commit();cid=c.id
        dispatcher=build_financial_dispatcher(sync_session_factory)
        requests=[MarketInvestigationRequest(symbol='MU',as_of=DEMO_AS_OF,sector_benchmark='SOXX'),
                  PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID,as_of=DEMO_AS_OF)]
        for index,request in enumerate(requests):
            run=dispatcher.create(cid,request,idempotency_key=str(index),mode='auto')
            result=run_agent.run(run.id)
            assert result['status']=='completed',dispatcher.snapshot(run.id)
            initial=dispatcher.snapshot(run.id)
            assert run_agent.run(run.id)['status']=='completed'
            replay=dispatcher.snapshot(run.id)
            assert initial['budget']==replay['budget']
            assert initial['checkpoint']['artifact_ids']==replay['checkpoint']['artifact_ids']
        print('fresh worker: both domains complete; duplicate delivery unchanged')
    ''', tmp_path)
    assert "both domains complete" in output


def test_non_demo_mode_requires_explicit_providers():
    from agent.financial import build_financial_dispatcher
    with pytest.raises(ValueError, match="execution profile"):
        build_financial_dispatcher(lambda: None, demo=False)
    with pytest.raises(ValueError, match="Explicit providers"):
        build_financial_dispatcher(lambda: None, demo=False, execution_profile="configured-v1")


@pytest.mark.parametrize("overrides", [
    {"providers": {}}, {"market_dependencies": object()},
    {"event_dependencies": object()}, {"portfolio_dependencies": object()},
    {"execution_profile": "custom-v1"},
])
def test_reserved_demo_profile_rejects_custom_assembly(overrides):
    from agent.financial import build_financial_dispatcher
    with pytest.raises(ValueError):
        build_financial_dispatcher(lambda: None, **overrides)


def test_configured_assembly_cannot_claim_reserved_demo_profile():
    from agent.financial import build_financial_dispatcher
    with pytest.raises(ValueError, match="non-demo execution profile"):
        build_financial_dispatcher(lambda: None, demo=False, execution_profile="synthetic-demo-v1", providers={})


@pytest.mark.parametrize("entry", ["run_agent", "resume_agent_job"])
def test_configured_source_survives_direct_execution_and_fresh_worker_rejects_substitution(entry, tmp_path):
    queued_id = process('''
        import asyncio, json
        from db.base import Base
        import db.models
        from db.session import sync_engine, sync_session_factory
        from db.repositories.agent import create_conversation
        from agent.financial import build_financial_dispatcher
        from agent.financial_demo import demo_market_dependencies, DEMO_AS_OF
        from agent.market_mas import SyntheticMarketModel
        from agent.tools.market_history import FixtureHistoryBackend, MarketDependencies, HistorySeries
        from agent.shared import MarketInvestigationRequest
        Base.metadata.create_all(sync_engine())
        history, events = demo_market_dependencies()
        series=[]
        for symbol in ('MU','SOXX','SPY'):
            data=history.history_backend.load(symbol).model_dump()
            data.update(provider='configured-test-v1',source_locator='fixture://configured-test/'+symbol)
            if symbol=='MU':
                for bar in data['bars']:
                    bar.update(open=100,high=100,low=100,close=100)
                data['bars'][-1].update(open=200,high=200,low=200,close=200)
            series.append(HistorySeries.model_validate(data))
        roles=('coordinator','price_volume','macro_sector','event','critic')
        configured=build_financial_dispatcher(sync_session_factory,enabled=('market_investigation',),
            demo=False,execution_profile='configured-test-v1',
            providers={'market_investigation':{role:SyntheticMarketModel(role) for role in roles}},
            market_dependencies=MarketDependencies(FixtureHistoryBackend(series)),event_dependencies=events)
        with sync_session_factory() as s:
            c=create_conversation(s,'Configured source must not be substituted');s.commit();cid=c.id
        request=MarketInvestigationRequest(symbol='MU',as_of=DEMO_AS_OF,sector_benchmark='SOXX')
        direct=configured.create(cid,request,idempotency_key='direct',mode='auto')
        assert asyncio.run(configured.start(direct.id)).status=='completed'
        artifact=json.loads(configured.get_run(direct.id).final_answer)
        assert next(f['value'] for f in artifact['numeric_facts'] if f['name']=='market.return_pct')==100.0
        queued=configured.create(cid,request,idempotency_key='queued',mode='auto')
        assert configured.snapshot(queued.id)['execution_profile']=='configured-test-v1'
        print(queued.id)
    ''', tmp_path).strip()
    process(f'''
        from sqlalchemy import select, func
        from db.session import sync_session_factory
        from db.models import AgentEvent, FinancialInvocation, FinancialArtifact
        from agent.shared import FinancialMASDispatcher
        from workers.agent_tasks import run_agent, resume_agent_job
        dispatcher=FinancialMASDispatcher(sync_session_factory)
        before=dispatcher.snapshot('{queued_id}')
        with sync_session_factory() as s:
            events_before=s.scalar(select(func.count()).select_from(AgentEvent).where(AgentEvent.run_id=='{queued_id}'))
        try:
            (run_agent.run('{queued_id}') if '{entry}'=='run_agent' else resume_agent_job.run('{queued_id}','unused'))
        except ValueError as exc:
            assert 'unsupported_execution_profile' in str(exc)
        else:
            raise AssertionError('Fresh worker substituted an unsupported configured source')
        assert dispatcher.snapshot('{queued_id}')==before
        with sync_session_factory() as s:
            assert s.scalar(select(func.count()).select_from(AgentEvent).where(AgentEvent.run_id=='{queued_id}'))==events_before
            assert s.scalar(select(func.count()).select_from(FinancialInvocation).where(FinancialInvocation.run_id=='{queued_id}'))==0
            assert s.scalar(select(func.count()).select_from(FinancialArtifact).where(FinancialArtifact.run_id=='{queued_id}'))==0
    ''', tmp_path)


@pytest.mark.parametrize("kind, absent", [
    ("market_investigation", "agent.portfolio_mas"),
    ("portfolio_rebalance", "agent.market_mas"),
])
@pytest.mark.parametrize("entry", ["run_agent", "resume_agent_job"])
def test_worker_delivery_with_peer_implementation_unavailable(kind, absent, entry, tmp_path):
    process(f'''
        import builtins
        from db.base import Base
        import db.models
        from db.session import sync_engine, sync_session_factory
        from db.repositories.agent import create_conversation
        from agent.financial import build_financial_dispatcher
        from agent.financial_demo import DEMO_AS_OF, DEMO_SNAPSHOT_ID
        from agent.shared import MarketInvestigationRequest, PortfolioReviewRequest
        from workers.agent_tasks import run_agent, resume_agent_job
        Base.metadata.create_all(sync_engine())
        with sync_session_factory() as s:
            c=create_conversation(s,'Standalone worker, peer unavailable');s.commit();cid=c.id
        request=(MarketInvestigationRequest(symbol='MU',as_of=DEMO_AS_OF,sector_benchmark='SOXX')
            if '{kind}'=='market_investigation' else PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID,as_of=DEMO_AS_OF))
        dispatcher=build_financial_dispatcher(sync_session_factory, enabled=('{kind}',))
        run=dispatcher.create(cid,request,idempotency_key='standalone',mode='auto')
        original_import=builtins.__import__
        def isolated_import(name,*args,**kwargs):
            if name=='{absent}' or name.startswith('{absent}.'):
                raise ModuleNotFoundError('Disabled peer implementation is unavailable')
            return original_import(name,*args,**kwargs)
        builtins.__import__=isolated_import
        result=(run_agent.run(run.id) if '{entry}'=='run_agent' else resume_agent_job.run(run.id,'unused-job'))
        assert result['status']=='completed',dispatcher.snapshot(run.id)
    ''', tmp_path)


@pytest.mark.parametrize("entry", ["run_agent", "resume_agent_job"])
@pytest.mark.parametrize("kind", ["market_investigation", "portfolio_rebalance"])
def test_worker_rejects_legacy_missing_profile_without_persistence_changes(entry, kind, tmp_path):
    process(f'''
        from db.base import Base
        import db.models
        from db.session import sync_engine,sync_session_factory
        from db.repositories.agent import create_conversation
        from agent.financial import build_financial_dispatcher
        from agent.financial_demo import DEMO_AS_OF,DEMO_SNAPSHOT_ID
        from agent.shared import FinancialMASDispatcher,MarketInvestigationRequest,PortfolioReviewRequest
        from workers.agent_tasks import run_agent,resume_agent_job
        Base.metadata.create_all(sync_engine())
        assembled=build_financial_dispatcher(sync_session_factory,enabled=('{kind}',))
        legacy=FinancialMASDispatcher(sync_session_factory,assembled.drivers,assembled.tools)
        with sync_session_factory() as s:
            c=create_conversation(s,'Legacy identity remains readable');s.commit();cid=c.id
        request=(MarketInvestigationRequest(symbol='MU',as_of=DEMO_AS_OF) if '{kind}'=='market_investigation'
            else PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID,as_of=DEMO_AS_OF))
        run=legacy.create(cid,request,idempotency_key='legacy',mode='auto')
        before=legacy.snapshot(run.id)
        assert before['execution_profile'] is None
        try:
            (run_agent.run(run.id) if '{entry}'=='run_agent' else resume_agent_job.run(run.id,'unused'))
        except ValueError as exc:
            assert 'unsupported_execution_profile' in str(exc)
        else:
            raise AssertionError('Unprofiled run silently executed with demo data')
        assert legacy.snapshot(run.id)==before
    ''', tmp_path)
