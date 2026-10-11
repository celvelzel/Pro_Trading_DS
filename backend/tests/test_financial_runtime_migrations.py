"""Disposable migration ownership checks; never use an application database."""
import os
from pathlib import Path
import subprocess
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from db.base import Base
from db.models import FinancialRun  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
FINANCIAL = {'financial_runs', 'financial_invocations', 'financial_artifacts', 'financial_relations', 'financial_datasets'}


def migrate(path, direction, revision):
    env = dict(os.environ, DATABASE_URL='sqlite:///' + str(path))
    result = subprocess.run([sys.executable, '-m', 'alembic', direction, revision], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_fresh_existing_upgrade_and_downgrade_preserves_general(tmp_path):
    path = tmp_path / 'disposable.db'
    migrate(path, 'upgrade', '0001_agent_platform')
    engine = create_engine('sqlite:///' + str(path))
    assert not FINANCIAL.intersection(inspect(engine).get_table_names())
    migrate(path, 'upgrade', '0003_runtime_hardening')
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO conversations (id) VALUES ('legacy')"))
        conn.execute(text("INSERT INTO agent_runs (id, conversation_id, status, mode, goal, version, replan_count, model_calls, tool_calls, checkpoint) VALUES ('general', 'legacy', 'completed', 'auto', 'legacy', 1, 0, 0, 0, '{}')"))
    migrate(path, 'upgrade', 'head')
    assert FINANCIAL.issubset(inspect(engine).get_table_names())
    migrate(path, 'downgrade', '0003_runtime_hardening')
    assert not FINANCIAL.intersection(inspect(engine).get_table_names())
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT goal FROM agent_runs WHERE id='general'")) == 'legacy'
    engine.dispose()
    fresh = tmp_path / 'fresh.db'
    migrate(fresh, 'upgrade', 'head')
    fresh_engine = create_engine('sqlite:///' + str(fresh))
    assert FINANCIAL.issubset(inspect(fresh_engine).get_table_names())
    fresh_engine.dispose()


def test_financial_postgresql_ddl_uses_jsonb():
    for name in FINANCIAL:
        ddl = str(CreateTable(Base.metadata.tables[name]).compile(dialect=postgresql.dialect()))
        assert 'JSONB' in ddl
        assert 'FOREIGN KEY' in ddl
