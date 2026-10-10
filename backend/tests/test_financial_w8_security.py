"""W8 security regression checks on the synthetic financial API only."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from agent.financial_demo import DEMO_AS_OF
from agent.llm import ModelProviderError
from agent.market_mas import SyntheticMarketModel
from api.routes import financial
from db.base import Base
from db.models import AgentEvent, Conversation, FinancialInvocation
from workers import agent_tasks


def test_provider_exception_text_is_not_exposed_by_financial_api_or_audit(tmp_path, monkeypatch):
    """Only the stable error code may cross the provider failure boundary."""
    engine = create_engine('sqlite:///' + str(tmp_path / 'security.db'),
        connect_args={'check_same_thread': False, 'timeout': 20})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as session:
        session.add(Conversation(id='security'))
        session.commit()

    monkeypatch.setattr(financial, 'sync_session_factory', sessions)
    monkeypatch.setattr(agent_tasks, 'sync_session_factory', sessions)
    monkeypatch.delenv('REDIS_URL', raising=False)
    sentinel = 'SYNTHETIC_PROVIDER_SECRET_DO_NOT_DISCLOSE_7c9f'

    async def provider_failure(self, messages, *, request_id=None):
        raise ModelProviderError('internal_error', sentinel)

    monkeypatch.setattr(SyntheticMarketModel, 'complete', provider_failure)
    app = FastAPI()
    app.include_router(financial.router, prefix='/api/financial')

    try:
        with TestClient(app) as client:
            created = client.post('/api/financial/market-investigations', json={
                'conversation_id': 'security',
                'idempotency_key': 'w8-secret-boundary',
                'mode': 'auto',
                'market': {
                    'symbol': 'MU',
                    'sector_benchmark': 'SOXX',
                    'as_of': DEMO_AS_OF.isoformat(),
                },
            })
            assert created.status_code == 202, created.text
            run_id = created.json()['market_run_id']

            result = client.get(f'/api/financial/runs/{run_id}')
            assert result.status_code == 200, result.text
            assert result.json()['status'] == 'failed'
            assert result.json()['error_code'] == 'internal_error'
            assert sentinel not in result.text

        with sessions() as session:
            events = list(session.scalars(select(AgentEvent).where(
                AgentEvent.run_id == run_id)).all())
            invocations = list(session.scalars(select(FinancialInvocation).where(
                FinancialInvocation.run_id == run_id)).all())
            persisted = json.dumps({
                'events': [event.payload for event in events],
                'invocations': [
                    {'output': item.output, 'error_code': item.error_code}
                    for item in invocations
                ],
            }, sort_keys=True)
            assert sentinel not in persisted
            assert any(event.event_type == 'mas.failure' for event in events)
            assert all(item.error_code in (None, 'internal_error') for item in invocations)
    finally:
        engine.dispose()
