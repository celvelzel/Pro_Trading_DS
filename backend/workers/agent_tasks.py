"""Agent queue tasks; waiting jobs release this worker and resume later."""

from __future__ import annotations

import asyncio

from celery import shared_task

from db.session import sync_session_factory
from workers.celery_app import celery_app


def _financial_dispatcher(snapshot):
    # Reconstruction is a trusted deployment mapping, never inferred from symbols.
    if snapshot.get("execution_profile") != "synthetic-demo-v1":
        raise ValueError("unsupported_execution_profile: financial worker configuration is unavailable")
    from agent.financial import build_financial_dispatcher
    return build_financial_dispatcher(sync_session_factory, enabled=(snapshot["mas_kind"],))


def _financial_pair_router(snapshot):
    if snapshot.get("execution_profile") != "synthetic-demo-v1":
        raise ValueError("unsupported_execution_profile: financial worker configuration is unavailable")
    from agent.financial import build_financial_dispatcher
    from agent.financial_demo import demo_snapshot_loader
    from agent.integration import CrossMASRouter
    from agent.shared import ArtifactStore
    router = None
    dispatcher = build_financial_dispatcher(sync_session_factory,
        portfolio_artifact_resolver=lambda *args: router.artifact_resolver(*args))
    router = CrossMASRouter(dispatcher, ArtifactStore(sync_session_factory),
        demo_snapshot_loader, execution_profile="synthetic-demo-v1")
    return router


@celery_app.task(name="backend.workers.agent_tasks.run_financial_pair", queue="agent")
def run_financial_pair(run_id: str) -> dict:
    """Restore the persisted pair from either actual member; no local pair map."""
    from agent.shared import FinancialMASDispatcher
    snapshot = FinancialMASDispatcher(sync_session_factory).snapshot(run_id)
    router = _financial_pair_router(snapshot)
    result = asyncio.run(router.advance(router.restore(run_id)))
    return result.model_dump(mode="json")


@celery_app.task(name="backend.workers.agent_tasks.run_agent", queue="agent")
def run_agent(run_id: str) -> dict:
    from agent.shared import FinancialMASDispatcher
    dispatcher = FinancialMASDispatcher(sync_session_factory)
    if dispatcher.is_financial(run_id):
        dispatcher = _financial_dispatcher(dispatcher.snapshot(run_id))
        dispatcher.validate_queue_eligibility(run_id)
        run = asyncio.run(dispatcher.start(run_id))
        return {"run_id": run.id, "status": run.status, "version": run.version}
    from agent.llm import OpenAICompatibleModel
    from agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(sync_session_factory, OpenAICompatibleModel.from_env())
    run = asyncio.run(orchestrator.start(run_id))
    return {"run_id": run.id, "status": run.status, "version": run.version}


@celery_app.task(name="backend.workers.agent_tasks.resume_agent_job", queue="agent")
def resume_agent_job(run_id: str, job_id: str) -> dict:
    from agent.shared import FinancialMASDispatcher
    dispatcher = FinancialMASDispatcher(sync_session_factory)
    if dispatcher.is_financial(run_id):
        dispatcher = _financial_dispatcher(dispatcher.snapshot(run_id))
        dispatcher.validate_queue_eligibility(run_id)
        run = asyncio.run(dispatcher.start(run_id))
        return {"run_id": run.id, "status": run.status, "version": run.version}
    from agent.llm import OpenAICompatibleModel
    from agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(sync_session_factory, OpenAICompatibleModel.from_env())
    run = asyncio.run(orchestrator.resume_job(run_id, job_id))
    return {"run_id": run.id, "status": run.status, "version": run.version}
