"""Agent REST snapshot, intervention and replayable GET SSE endpoints."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from agent.llm import OpenAICompatibleModel
from agent.memory import MemoryService
from agent.orchestrator import AgentOrchestrator
from api.models.agent import (
    ConversationCreate,
    ConversationResponse,
    MemoryCreate,
    MemorySupersede,
    RunAction,
    RunCreate,
)
from db.models.agent import AgentRun, Conversation, MemoryItem, Plan, Step
from db.repositories.agent import add_message, append_event, create_conversation, list_events
from db.session import sync_session_factory

router = APIRouter()


def _orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator(sync_session_factory, OpenAICompatibleModel.from_env())


def _snapshot(run_id: str) -> dict[str, Any]:
    with sync_session_factory() as session:
        run = session.get(AgentRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Agent run not found")
        plans = list(session.scalars(select(Plan).where(Plan.run_id == run_id).order_by(Plan.revision)))
        plan_data = None
        if plans:
            current = plans[-1]
            steps = list(session.scalars(select(Step).where(Step.plan_id == current.id).order_by(Step.ordinal)))
            plan_data = {
                "id": current.id,
                "revision": current.revision,
                "goal": current.goal,
                "assumptions": current.assumptions,
                "completion_conditions": current.completion_conditions,
                "steps": [
                    {
                        "id": item.id,
                        "ordinal": item.ordinal,
                        "type": item.type,
                        "name": item.name,
                        "status": item.status,
                        "tool_name": item.tool_name,
                        "depends_on": item.depends_on,
                        "requires_confirmation": item.requires_confirmation,
                    }
                    for item in steps
                ],
            }
        return {
            "id": run.id,
            "conversation_id": run.conversation_id,
            "parent_run_id": run.parent_run_id,
            "status": run.status,
            "mode": run.mode,
            "goal": run.goal,
            "version": run.version,
            "replan_count": run.replan_count,
            "checkpoint": run.checkpoint,
            "final_answer": run.final_answer,
            "error_code": run.error_code,
            "plan": plan_data,
        }


def _dispatch(run_id: str) -> None:
    if not os.getenv("REDIS_URL"):
        # Local development can still use the API with a configured provider;
        # Docker supplies REDIS_URL and dispatches to the real worker.
        return
    from workers.agent_tasks import run_agent

    run_agent.delay(run_id)


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_agent_conversation(payload: ConversationCreate):
    with sync_session_factory() as session:
        conversation = create_conversation(session, payload.title)
        session.commit()
        return ConversationResponse(id=conversation.id, title=conversation.title).model_dump()


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def create_agent_run(payload: RunCreate):
    with sync_session_factory() as session:
        if session.get(Conversation, payload.conversation_id) is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        run = _orchestrator().create_run(payload.conversation_id, payload.goal, payload.mode)
        add_message(session, payload.conversation_id, "user", payload.goal)
        session.commit()
    _dispatch(run.id)
    return _snapshot(run.id)


@router.get("/runs/{run_id}")
async def get_agent_run(run_id: str):
    return _snapshot(run_id)


@router.post("/runs/{run_id}/approve")
async def approve_agent_run(run_id: str, payload: RunAction):
    try:
        run = await _orchestrator().approve(run_id, payload.expected_version)
    except RuntimeError as exc:
        if str(exc) == "version_conflict":
            raise HTTPException(status_code=409, detail="Run version conflict") from exc
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _snapshot(run.id)


@router.post("/runs/{run_id}/reject")
async def reject_agent_run(run_id: str, payload: RunAction):
    with sync_session_factory() as session:
        run = session.get(AgentRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Agent run not found")
        if run.version != payload.expected_version:
            raise HTTPException(status_code=409, detail="Run version conflict")
        if run.status != "waiting_user":
            raise HTTPException(status_code=409, detail="Only a waiting plan can be rejected")
        from agent.state_machine import transition

        previous = run.status
        run.status = transition(run.status, "fail")
        run.error_code = "plan_rejected"
        run.version += 1
        append_event(
            session,
            run=run,
            event_type="plan.rejected",
            request_id=str(uuid.uuid4()),
            payload={"from": previous, "to": run.status, "reason": payload.reason},
        )
        session.commit()
    return _snapshot(run_id)


@router.post("/runs/{run_id}/resume")
async def resume_agent_run(run_id: str, payload: RunAction):
    try:
        with sync_session_factory() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise ValueError("Run does not exist")
            if run.version != payload.expected_version:
                raise RuntimeError("version_conflict")
            from agent.state_machine import transition

            run.status = transition(run.status, "resume")
            run.version += 1
            append_event(session, run=run, event_type="run.resumed", request_id=str(uuid.uuid4()), payload={})
            session.commit()
        await _orchestrator()._execute_steps(run_id)
    except RuntimeError as exc:
        if str(exc) == "version_conflict":
            raise HTTPException(status_code=409, detail="Run version conflict") from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _snapshot(run_id)


@router.post("/runs/{run_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_agent_run(run_id: str, payload: RunAction):
    with sync_session_factory() as session:
        parent = session.get(AgentRun, run_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="Agent run not found")
        if parent.version != payload.expected_version:
            raise HTTPException(status_code=409, detail="Run version conflict")
        if parent.status not in {"failed", "cancelled"}:
            raise HTTPException(status_code=409, detail="Only a failed or cancelled run can be retried")
        child = _orchestrator().create_run(parent.conversation_id, parent.goal, parent.mode)
        child_id = child.id
        child = session.get(AgentRun, child_id)
        child.parent_run_id = parent.id
        child.retry_of_step_id = payload.retry_of_step_id
        append_event(
            session,
            run=parent,
            event_type="run.child_created",
            request_id=str(uuid.uuid4()),
            payload={"child_run_id": child_id, "retry_of_step_id": payload.retry_of_step_id},
        )
        session.commit()
    _dispatch(child_id)
    return _snapshot(child_id)


@router.post("/runs/{run_id}/pause")
async def pause_agent_run(run_id: str, payload: RunAction):
    return await _intervene(run_id, payload, "pause")


@router.post("/runs/{run_id}/cancel")
async def cancel_agent_run(run_id: str, payload: RunAction):
    return await _intervene(run_id, payload, "cancel")


async def _intervene(run_id: str, payload: RunAction, action: str):
    with sync_session_factory() as session:
        run = session.get(AgentRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Agent run not found")
        if run.version != payload.expected_version:
            raise HTTPException(status_code=409, detail="Run version conflict")
        try:
            from agent.state_machine import transition

            event = "request_pause" if action == "pause" else "request_cancel"
            previous = run.status
            run.status = transition(run.status, event)
            run.version += 1
            append_event(
                session,
                run=run,
                event_type="run.pause_requested" if action == "pause" else "run.status_changed",
                request_id=str(uuid.uuid4()),
                payload={"from": previous, "to": run.status, "reason": payload.reason},
            )
            session.commit()
        except Exception as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _snapshot(run_id)


@router.get("/runs/{run_id}/events")
async def agent_events(run_id: str, request: Request, after_seq: int = 0):
    with sync_session_factory() as session:
        if session.get(AgentRun, run_id) is None:
            raise HTTPException(status_code=404, detail="Agent run not found")
        last_event_id = request.headers.get("Last-Event-ID")
        if last_event_id and last_event_id.isdigit():
            after_seq = max(after_seq, int(last_event_id))
        events = list_events(session, run_id, after_seq=after_seq)

    async def stream() -> AsyncIterator[str]:
        for event in events:
            yield (
                f"id: {event.seq}\n"
                f"event: {event.event_type}\n"
                f"data: {json.dumps({'schema_version': event.schema_version, 'event_id': event.event_id, 'seq': event.seq, 'event_type': event.event_type, 'timestamp': event.created_at.isoformat() if event.created_at else None, 'conversation_id': event.conversation_id, 'run_id': event.run_id, 'request_id': event.request_id, 'payload': event.payload}, ensure_ascii=False)}\n\n"
            )
        yield ": heartbeat\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/conversations/{conversation_id}/memory")
async def list_memory(conversation_id: str):
    items = MemoryService(sync_session_factory).list_active(conversation_id)
    return [_memory_dump(item) for item in items]


@router.post("/conversations/{conversation_id}/memory", status_code=status.HTTP_201_CREATED)
async def create_memory(conversation_id: str, payload: MemoryCreate):
    try:
        item = MemoryService(sync_session_factory).create(
            conversation_id, payload.kind, payload.content, payload.source_message_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _memory_dump(item)


@router.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: str):
    if not MemoryService(sync_session_factory).delete(memory_id):
        raise HTTPException(status_code=404, detail="Memory item not found")


@router.post("/memory/{memory_id}/supersede", status_code=status.HTTP_201_CREATED)
async def supersede_memory(memory_id: str, payload: MemorySupersede):
    try:
        return _memory_dump(MemoryService(sync_session_factory).supersede(memory_id, payload.content))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _memory_dump(item: MemoryItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "conversation_id": item.conversation_id,
        "kind": item.kind,
        "content": item.content,
        "source_message_id": item.source_message_id,
        "superseded_by": item.superseded_by,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }
