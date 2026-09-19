"""W3 state, planner, memory and orchestrator tests."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


def test_state_machine_rejects_illegal_transitions_and_terminal_reopen():
    from agent.state_machine import InvalidStateTransition, transition

    assert transition("created", "queue") == "queued"
    assert transition("waiting_user", "approve") == "executing"
    assert transition("executing", "request_pause") == "pause_requested"
    with pytest.raises(InvalidStateTransition):
        transition("completed", "begin_execution")


def test_planner_rejects_unknown_tools_cycles_and_more_than_six_steps():
    from agent.planner import PlanValidationError, Planner
    from agent.schemas import PlanSpec, PlanStepSpec

    planner = Planner({"known"})
    with pytest.raises(PlanValidationError):
        planner.validate(PlanSpec(goal="x", steps=[PlanStepSpec(id="a", type="tool", name="x", tool_name="unknown")]))
    with pytest.raises(ValueError, match="acyclic"):
        planner.validate(
            PlanSpec(
                goal="x",
                steps=[
                    PlanStepSpec(id="a", type="tool", name="a", tool_name="known", depends_on=["b"]),
                    PlanStepSpec(id="b", type="tool", name="b", tool_name="known", depends_on=["a"]),
                ],
            )
        )
    with pytest.raises(ValueError):
        PlanSpec(
            goal="x",
            steps=[PlanStepSpec(id=str(index), type="tool", name="x", tool_name="known") for index in range(7)],
        )


def test_context_builder_preserves_policy_and_recent_messages_with_budget():
    from agent.context_builder import ContextBuilder

    messages = [{"role": "user", "content": str(index) * 100} for index in range(20)]
    result = ContextBuilder(max_tokens=80).build(
        system_policy="policy",
        memories=["memory"],
        messages=messages,
    )
    assert result[0]["content"] == "policy"
    assert result[-1]["content"] == "19" * 100
    assert sum(len(item["content"]) for item in result) <= 320


@pytest.fixture()
def core_session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import db.session as session_module

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'agent.db'}")
    session_module.get_database_url.cache_clear()
    session_module.async_engine.cache_clear()
    session_module.sync_engine.cache_clear()
    session_module.sync_session_factory.configure(bind=session_module.sync_engine())
    from db.base import Base
    from db.models import agent, jobs  # noqa: F401

    Base.metadata.create_all(session_module.sync_engine())
    yield session_module.sync_session_factory
    session_module.sync_engine().dispose()


def test_review_run_is_waiting_user_then_completes_after_approval(core_session_factory):
    from agent.llm import ScriptedFakeModel
    from agent.orchestrator import AgentOrchestrator
    from agent.planner import Planner
    from agent.tools.executor import ToolExecutor
    from agent.tools.registry import ToolRegistry, ToolSpec
    from db.models.agent import Conversation

    class Input(__import__("pydantic").BaseModel):
        value: int

    class Output(__import__("pydantic").BaseModel):
        result: int

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="demo",
            version="1",
            description="demo",
            input_model=Input,
            output_model=Output,
            handler=lambda payload: {"result": payload.value + 1},
        )
    )
    with core_session_factory() as session:
        conversation = Conversation(title="test")
        session.add(conversation)
        session.commit()
        conversation_id = conversation.id

    provider = ScriptedFakeModel(
        [
            {
                "kind": "plan",
                "payload": {
                    "goal": "demo",
                    "steps": [{"id": "step-1", "type": "tool", "name": "demo", "tool_name": "demo", "input_data": {"value": 1}}],
                },
            }
        ]
    )
    orchestrator = AgentOrchestrator(
        core_session_factory,
        provider,
        executor=ToolExecutor(registry),
        planner=Planner({"demo"}),
    )
    run = orchestrator.create_run(conversation_id, "demo", mode="review")
    waiting = asyncio.run(orchestrator.start(run.id))
    assert waiting.status == "waiting_user"
    completed = asyncio.run(orchestrator.approve(run.id, waiting.version))
    assert completed.status == "completed"
    assert completed.final_answer

    from sqlalchemy import select
    from db.models.agent import AgentEvent

    with core_session_factory() as session:
        events = list(session.scalars(select(AgentEvent).where(AgentEvent.run_id == run.id).order_by(AgentEvent.seq)))
        assert [event.seq for event in events] == list(range(1, len(events) + 1))


def test_plan_rejection_replans_once_then_becomes_terminal(core_session_factory):
    from agent.llm import ScriptedFakeModel
    from agent.orchestrator import AgentOrchestrator
    from agent.planner import Planner
    from db.models.agent import Conversation, Plan

    with core_session_factory() as session:
        conversation = Conversation(title="replan")
        session.add(conversation)
        session.commit()
        conversation_id = conversation.id

    plan = {"kind": "plan", "payload": {"goal": "replan", "steps": [{"id": "final", "type": "final", "name": "answer"}]}}
    provider = ScriptedFakeModel([plan, plan])
    orchestrator = AgentOrchestrator(core_session_factory, provider, planner=Planner(set()))
    run = orchestrator.create_run(conversation_id, "replan", mode="review")
    waiting = asyncio.run(orchestrator.start(run.id))
    revised = asyncio.run(orchestrator.reject(waiting.id, waiting.version, "请缩小研究范围"))
    assert revised.status == "waiting_user"
    assert revised.replan_count == 1
    with core_session_factory() as session:
        assert [row.revision for row in session.query(Plan).filter(Plan.run_id == run.id).all()] == [1, 2]
    terminal = asyncio.run(orchestrator.reject(revised.id, revised.version, "仍然不合适"))
    assert terminal.status == "failed"
    assert terminal.error_code == "plan_rejected"


def test_pause_and_cancel_are_allowed_while_waiting_for_job():
    from agent.state_machine import transition

    assert transition("waiting_job", "request_pause") == "pause_requested"
    assert transition("waiting_job", "request_cancel") == "cancelling"
