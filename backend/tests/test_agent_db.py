"""W1 database/session and Celery contract tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import inspect, select


@pytest.fixture()
def sqlite_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Reload session factories against an isolated SQLite database."""

    import db.session as session_module

    database_path = tmp_path / "agent.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    session_module.get_database_url.cache_clear()
    session_module.async_engine.cache_clear()
    session_module.sync_engine.cache_clear()
    session_module.async_session_factory.configure(bind=session_module.async_engine())
    session_module.sync_session_factory.configure(bind=session_module.sync_engine())
    yield session_module
    session_module.async_engine().sync_engine.dispose()
    session_module.sync_engine().dispose()


def test_models_can_round_trip_with_sync_session(sqlite_database):
    from db.base import Base
    from db.models import Conversation

    engine = sqlite_database.sync_engine()
    Base.metadata.create_all(engine)
    with sqlite_database.sync_session_factory() as session:
        conversation = Conversation(title="test")
        session.add(conversation)
        session.commit()
        found = session.scalar(select(Conversation).where(Conversation.id == conversation.id))
        assert found is not None
        assert found.title == "test"
    assert "agent_events" in inspect(engine).get_table_names()


def test_celery_uses_json_and_separate_queues():
    from workers.celery_app import celery_app

    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.task_serializer == "json"
    routes = celery_app.conf.task_routes
    assert routes["backend.workers.agent_tasks.*"]["queue"] == "agent"
    assert routes["backend.workers.compute_tasks.*"]["queue"] == "compute"
