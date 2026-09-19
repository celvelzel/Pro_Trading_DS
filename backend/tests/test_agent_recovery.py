"""Replay and intervention recovery contracts."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_event_replay_returns_only_events_after_cursor(tmp_path):
    from agent.state_machine import transition
    from db.base import Base
    from db.models.agent import AgentRun, Conversation
    from db.repositories.agent import append_event, list_events

    engine = create_engine(f"sqlite:///{tmp_path / 'replay.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        conversation = Conversation(title="replay")
        session.add(conversation)
        session.flush()
        run = AgentRun(conversation_id=conversation.id, goal="replay", status="created")
        session.add(run)
        session.flush()
        append_event(session, run=run, event_type="run.status_changed", request_id="r1", payload={"seq": 1})
        append_event(session, run=run, event_type="plan.created", request_id="r2", payload={"seq": 2})
        append_event(session, run=run, event_type="step.started", request_id="r3", payload={"seq": 3})
        session.commit()
        replayed = list_events(session, run.id, after_seq=1)
        assert [event.seq for event in replayed] == [2, 3]
    assert transition("waiting_job", "request_pause") == "pause_requested"
    engine.dispose()
