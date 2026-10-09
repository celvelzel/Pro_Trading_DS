"""Fresh queue processes must preserve durable intent and admitted deadlines."""
import pytest

from backend.tests.test_financial_bootstrap import process


@pytest.mark.parametrize("entry", ["run_agent", "resume_agent_job"])
@pytest.mark.parametrize("case", ["orphan", "legacy_ambiguous", "expired", "independent", "legacy_retry"])
def test_real_worker_execution_authority(entry, case, tmp_path):
    process(f'''
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import select
        from db.base import Base
        import db.models
        from db.session import sync_engine, sync_session_factory
        from db.repositories.agent import create_conversation
        from agent.financial import build_financial_dispatcher
        from agent.financial_demo import DEMO_AS_OF, DEMO_SNAPSHOT_ID
        from agent.shared import (FinancialExecutionAuthorization,
            FinancialExecutionAuthorizationError, MarketInvestigationRequest,
            PortfolioReviewRequest, CrossMASEnvelope, RunBudget)
        from workers.agent_tasks import run_agent, resume_agent_job
        from agent.market_mas.synthetic import SyntheticMarketModel
        from agent.tools.executor import ToolExecutor
        calls={{'models':0,'tools':0}}
        original_model=SyntheticMarketModel.complete
        original_tool=ToolExecutor.execute
        async def observed_model(self,*args,**kwargs):
            calls['models']+=1
            return await original_model(self,*args,**kwargs)
        async def observed_tool(self,*args,**kwargs):
            calls['tools']+=1
            return await original_tool(self,*args,**kwargs)
        SyntheticMarketModel.complete=observed_model
        ToolExecutor.execute=observed_tool
        Base.metadata.create_all(sync_engine())
        with sync_session_factory() as s:
            c=create_conversation(s,'Synthetic authorization queue evidence')
            s.commit(); cid=c.id
        d=build_financial_dispatcher(sync_session_factory)
        request=MarketInvestigationRequest(symbol='MU',as_of=DEMO_AS_OF,sector_benchmark='SOXX')
        options={{}}
        if '{case}' in ('orphan','expired'):
            source=d.create(cid,PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID,
                as_of=DEMO_AS_OF),idempotency_key='source',mode='auto',correlation_id='corr',
                execution_authorization=FinancialExecutionAuthorization(purpose='independent'))
            options=dict(correlation_id='corr',execution_authorization=
                FinancialExecutionAuthorization(purpose='cross_followup',
                    source_run_id=source.id,request_message_id='request'))
        elif '{case}'=='legacy_ambiguous':
            options=dict(correlation_id='explicit-legacy')
        elif '{case}'=='independent':
            options=dict(correlation_id='explicit-independent',execution_authorization=
                FinancialExecutionAuthorization(purpose='independent'))
        target=d.create(cid,request,idempotency_key='target',mode='auto',**options)
        if '{case}'=='expired':
            then=datetime.now(timezone.utc)-timedelta(minutes=2)
            d.clock=lambda:then
            env=CrossMASEnvelope(message_id='request',origin_mas='portfolio_rebalance',
                target_mas='market_investigation',run_id=source.id,correlation_id='corr',
                message_type='MARKET_EVIDENCE_REQUEST',as_of=DEMO_AS_OF,created_at=then,
                deadline_at=then+timedelta(seconds=1),idempotency_key='request',budget=RunBudget())
            d.admit_cross_message(source.id,target.id,expected_source_version=source.version,
                expected_target_version=target.version,envelope=env)
            d.clock=lambda:then+timedelta(seconds=2)
        if '{case}'=='legacy_retry':
            d.cancel(target.id,d.get_run(target.id).version)
            target=d.retry(target.id,d.get_run(target.id).version,idempotency_key='retry')
        def database_state():
            with sync_session_factory() as s:
                return {{table.name: sorted(repr(tuple(row)) for row in s.execute(select(table)))
                    for table in Base.metadata.sorted_tables}}
        def delivery():
            return (run_agent.run(target.id) if '{entry}'=='run_agent'
                else resume_agent_job.run(target.id,'synthetic-job'))
        before=database_state()
        if '{case}' in ('orphan','legacy_ambiguous'):
            try:
                delivery()
            except FinancialExecutionAuthorizationError as exc:
                assert exc.code=='financial_execution_authorization_denied'
            else:
                raise AssertionError('Unauthorized financial target executed')
            assert database_state()==before,'Denied queue delivery mutated persistence'
            assert calls=={{'models':0,'tools':0}},calls
        elif '{case}'=='expired':
            assert delivery()['status']=='expired'
            snapshot=d.snapshot(target.id)
            assert snapshot['error_code']=='cross_execution_expired'
            assert snapshot['budget']['model_calls']==0
            assert snapshot['budget']['tool_calls']==0
            assert not snapshot['checkpoint'].get('artifact_ids')
            expired=database_state()
            assert delivery()['status']=='expired'
            assert database_state()==expired,'Duplicate expiry mutated persistence'
            assert calls=={{'models':0,'tools':0}},calls
        else:
            assert delivery()['status']=='completed',d.snapshot(target.id)
            snapshot=d.snapshot(target.id)
            assert snapshot['budget']['model_calls']>0
            assert snapshot['budget']['tool_calls']>0
            assert snapshot['checkpoint']['artifact_ids']
            assert calls['models']==snapshot['budget']['model_calls']
            assert calls['tools']==snapshot['budget']['tool_calls']
            completed=database_state()
            completed_calls=dict(calls)
            assert delivery()['status']=='completed'
            assert database_state()==completed,'Duplicate queue delivery mutated persistence'
            assert calls==completed_calls
    ''', tmp_path)
