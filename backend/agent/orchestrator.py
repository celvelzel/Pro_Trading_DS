"""Persistent Plan → Execute orchestration with safe checkpoints."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable

from sqlalchemy import select

from db.models.agent import AgentRun, Plan, Step, ToolCall, ToolResult
from db.repositories.agent import append_event

from .context_builder import ContextBuilder
from .llm import ModelProvider, ModelProviderError
from .planner import Planner
from .schemas import PlanSpec, ToolResultEnvelope, ToolStatus
from .state_machine import InvalidStateTransition, transition
from .tools import default_registry
from .tools.executor import ToolExecutor


class AgentOrchestrator:
    def __init__(
        self,
        session_factory: Callable,
        provider: ModelProvider,
        executor: ToolExecutor | None = None,
        planner: Planner | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.provider = provider
        self.executor = executor or ToolExecutor(default_registry)
        self.planner = planner or Planner({tool.name for tool in default_registry.list()})
        self.context_builder = context_builder or ContextBuilder()

    def create_run(self, conversation_id: str, goal: str, mode: str = "review") -> AgentRun:
        with self.session_factory() as session:
            run = AgentRun(conversation_id=conversation_id, goal=goal, mode=mode, status="created")
            session.add(run)
            session.flush()
            append_event(
                session,
                run=run,
                event_type="run.status_changed",
                request_id=str(uuid.uuid4()),
                payload={"from": None, "to": "created"},
            )
            session.commit()
            session.refresh(run)
            return run

    async def start(self, run_id: str) -> AgentRun:
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise ValueError("Run does not exist")
            if run.status not in {"created", "paused", "waiting_job"}:
                return run
            if run.status == "created":
                self._move(session, run, "queue")
                self._move(session, run, "begin_planning")
                session.commit()
            else:
                self._move(session, run, "begin_execution")
                session.commit()
        if run.status == "planning":
            await self._plan(run_id)
        return self._get_run(run_id)

    async def approve(self, run_id: str, expected_version: int) -> AgentRun:
        with self.session_factory() as session:
            run = self._checked_run(session, run_id, expected_version)
            self._move(session, run, "approve")
            session.commit()
        await self._execute_steps(run_id)
        return self._get_run(run_id)

    async def _plan(self, run_id: str) -> None:
        run = self._get_run(run_id)
        context = self.context_builder.build(
            system_policy="Return JSON with kind=plan and a bounded plan. Never invent financial values.",
            memories=[],
            messages=[{"role": "user", "content": run.goal}],
        )
        try:
            plan = await self.planner.create(self.provider, context)
        except (ModelProviderError, ValueError) as exc:
            with self.session_factory() as session:
                current = session.get(AgentRun, run_id)
                self._move(session, current, "fail")
                current.error_code = getattr(exc, "code", "internal_error")
                session.commit()
            return
        with self.session_factory() as session:
            current = session.get(AgentRun, run_id)
            plan_row = Plan(
                run_id=current.id,
                revision=plan.revision,
                goal=plan.goal,
                assumptions=plan.assumptions,
                completion_conditions=plan.completion_conditions,
            )
            session.add(plan_row)
            session.flush()
            for ordinal, item in enumerate(plan.steps):
                session.add(
                    Step(
                        plan_id=plan_row.id,
                        ordinal=ordinal,
                        type=item.type,
                        name=item.name,
                        tool_name=item.tool_name,
                        depends_on=item.depends_on,
                        input_data=item.input_data,
                        requires_confirmation=item.requires_confirmation,
                    )
                )
            append_event(
                session,
                run=current,
                event_type="plan.created",
                request_id=str(uuid.uuid4()),
                payload={"plan_id": plan_row.id, "revision": plan.revision, "step_count": len(plan.steps)},
            )
            if current.mode == "review":
                self._move(session, current, "wait_user")
                append_event(
                    session,
                    run=current,
                    event_type="plan.approval_required",
                    request_id=str(uuid.uuid4()),
                    payload={"plan_id": plan_row.id, "revision": plan.revision},
                )
            else:
                self._move(session, current, "begin_execution")
            session.commit()
        if run.mode != "review":
            await self._execute_steps(run_id)

    async def _execute_steps(self, run_id: str) -> None:
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            plan = session.scalar(select(Plan).where(Plan.run_id == run_id).order_by(Plan.revision.desc()))
            steps = list(session.scalars(select(Step).where(Step.plan_id == plan.id).order_by(Step.ordinal))) if plan else []
        for step in steps:
            with self.session_factory() as session:
                run = session.get(AgentRun, run_id)
                if run.status in {"pause_requested", "cancelling"}:
                    action = "pause" if run.status == "pause_requested" else "cancel"
                    self._move(session, run, action)
                    session.commit()
                    return
                if run.status != "executing":
                    return
                step = session.get(Step, step.id)
                step.status = "running"
                append_event(session, run=run, event_type="step.started", request_id=str(uuid.uuid4()), payload={"step_id": step.id})
                if step.type == "tool" and step.tool_name:
                    self._move(session, run, "wait_tool")
                session.commit()

            if step.type == "tool" and step.tool_name:
                envelope = await self.executor.execute(step.tool_name, step.input_data)
                with self.session_factory() as session:
                    run = session.get(AgentRun, run_id)
                    db_step = session.get(Step, step.id)
                    call = ToolCall(
                        run_id=run_id,
                        step_id=step.id,
                        tool_name=step.tool_name,
                        status=envelope.status.value,
                        input_data=step.input_data,
                        request_id=str(uuid.uuid4()),
                    )
                    session.add(call)
                    session.flush()
                    session.add(
                        ToolResult(
                            tool_call_id=call.id,
                            data=envelope.data,
                            citations=[citation.model_dump() for citation in envelope.citations],
                            summary=str(envelope.data)[:1000] if envelope.data else None,
                            duration_ms=envelope.duration_ms,
                            cached=envelope.cached,
                        )
                    )
                    db_step.status = "succeeded" if envelope.status == ToolStatus.SUCCEEDED else "failed"
                    append_event(
                        session,
                        run=run,
                        event_type="tool.completed" if envelope.status == ToolStatus.SUCCEEDED else "tool.failed",
                        request_id=str(uuid.uuid4()),
                        payload={"step_id": step.id, "tool_name": step.tool_name, "status": envelope.status.value},
                    )
                    if envelope.status != ToolStatus.SUCCEEDED:
                        self._move(session, run, "fail")
                        run.error_code = envelope.error.code if envelope.error else "internal_error"
                        session.commit()
                        return
                    self._move(session, run, "begin_execution")
                    session.commit()
            else:
                with self.session_factory() as session:
                    run = session.get(AgentRun, run_id)
                    db_step = session.get(Step, step.id)
                    db_step.status = "succeeded"
                    session.commit()

        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            if run.status == "executing":
                run.final_answer = "计划已完成。结果来自已执行的结构化工具步骤。"
                self._move(session, run, "complete")
                append_event(session, run=run, event_type="run.completed", request_id=str(uuid.uuid4()), payload={"has_answer": True})
                session.commit()

    async def resume_job(self, run_id: str, job_id: str) -> AgentRun:
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            if not run or run.status != "waiting_job":
                raise ValueError("Run is not waiting for a job")
            if run.checkpoint.get("job_id") != job_id:
                raise ValueError("Job does not match run checkpoint")
            self._move(session, run, "begin_execution")
            session.commit()
        await self._execute_steps(run_id)
        return self._get_run(run_id)

    def _get_run(self, run_id: str) -> AgentRun:
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise ValueError("Run does not exist")
            session.expunge(run)
            return run

    @staticmethod
    def _checked_run(session, run_id: str, expected_version: int) -> AgentRun:
        run = session.get(AgentRun, run_id)
        if run is None:
            raise ValueError("Run does not exist")
        if run.version != expected_version:
            raise RuntimeError("version_conflict")
        return run

    @staticmethod
    def _move(session, run: AgentRun, event: str) -> None:
        previous = run.status
        run.status = transition(previous, event)
        run.version += 1
        append_event(
            session,
            run=run,
            event_type="run.status_changed",
            request_id=str(uuid.uuid4()),
            payload={"from": previous, "to": run.status, "version": run.version},
        )
