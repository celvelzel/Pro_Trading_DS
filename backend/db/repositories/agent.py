"""Small transaction helpers shared by API and workers."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models.agent import AgentEvent, AgentRun, Conversation, Message


def append_event(
    session: Session,
    *,
    run: AgentRun,
    event_type: str,
    request_id: str,
    payload: dict[str, Any] | None = None,
) -> AgentEvent:
    last_seq = session.scalar(select(func.max(AgentEvent.seq)).where(AgentEvent.run_id == run.id)) or 0
    event = AgentEvent(
        event_id=str(uuid.uuid4()),
        run_id=run.id,
        conversation_id=run.conversation_id,
        seq=last_seq + 1,
        event_type=event_type,
        request_id=request_id,
        payload=payload or {},
    )
    session.add(event)
    return event


def create_conversation(session: Session, title: str | None = None, user_id: str | None = None) -> Conversation:
    conversation = Conversation(title=title, user_id=user_id)
    session.add(conversation)
    session.flush()
    return conversation


def add_message(session: Session, conversation_id: str, role: str, content: str) -> Message:
    last_sequence = session.scalar(
        select(func.max(Message.sequence)).where(Message.conversation_id == conversation_id)
    ) or 0
    message = Message(
        conversation_id=conversation_id,
        sequence=last_sequence + 1,
        role=role,
        content=content,
    )
    session.add(message)
    session.flush()
    return message


def list_events(session: Session, run_id: str, after_seq: int = 0, limit: int = 100) -> list[AgentEvent]:
    return list(
        session.scalars(
            select(AgentEvent)
            .where(AgentEvent.run_id == run_id, AgentEvent.seq > after_seq)
            .order_by(AgentEvent.seq)
            .limit(limit)
        )
    )
