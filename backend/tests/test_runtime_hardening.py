"""O73 observability and explicit-memory concurrency contracts."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def runtime_session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import db.session as session_module

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}")
    session_module.get_database_url.cache_clear()
    session_module.async_engine.cache_clear()
    session_module.sync_engine.cache_clear()
    session_module.sync_session_factory.configure(bind=session_module.sync_engine())
    from db.base import Base
    from db.models import agent, jobs  # noqa: F401

    Base.metadata.create_all(session_module.sync_engine())
    yield session_module.sync_session_factory
    session_module.sync_engine().dispose()


def test_memory_delete_and_supersede_reject_stale_versions(runtime_session_factory):
    from agent.memory import MemoryService
    from db.models.agent import Conversation

    with runtime_session_factory() as session:
        conversation = Conversation(title="memory")
        session.add(conversation)
        session.commit()
        conversation_id = conversation.id

    service = MemoryService(runtime_session_factory)
    item = service.create(conversation_id, "confirmed_fact", "risk limit is 1%")
    with pytest.raises(RuntimeError, match="version_conflict"):
        service.supersede(item.id, "risk limit is 0.5%", expected_version=2)
    replacement = service.supersede(item.id, "risk limit is 0.5%", expected_version=1)
    assert replacement.content == "risk limit is 0.5%"
    with pytest.raises(RuntimeError, match="version_conflict"):
        service.delete(replacement.id, expected_version=2)


def test_metrics_use_route_templates_and_never_request_ids():
    from observability.metrics import Metrics

    metrics = Metrics()
    metrics.observe("GET", "/api/agent/runs/{run_id}", 200, 0.01)
    metrics.observe("GET", "/api/agent/runs/{run_id}", 409, 0.02)
    rendered = metrics.render()
    assert "route=\"/api/agent/runs/{run_id}\"" in rendered
    assert "request_id" not in rendered
