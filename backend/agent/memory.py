"""Explicit memory service; no implicit extraction from chat."""

from __future__ import annotations

from typing import Callable

from sqlalchemy import select

from db.models.agent import MemoryItem

ALLOWED_MEMORY_KINDS = {"user_preference", "research_constraint", "confirmed_fact"}


class MemoryService:
    def __init__(self, session_factory: Callable) -> None:
        self.session_factory = session_factory

    def create(self, conversation_id: str, kind: str, content: str, source_message_id: str | None = None) -> MemoryItem:
        if kind not in ALLOWED_MEMORY_KINDS:
            raise ValueError(f"Unsupported explicit memory kind: {kind}")
        with self.session_factory() as session:
            item = MemoryItem(
                conversation_id=conversation_id,
                kind=kind,
                content=content,
                source_message_id=source_message_id,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def list_active(self, conversation_id: str) -> list[MemoryItem]:
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(MemoryItem).where(
                        MemoryItem.conversation_id == conversation_id,
                        MemoryItem.deleted_at.is_(None),
                        MemoryItem.superseded_by.is_(None),
                    )
                )
            )

    def delete(self, memory_id: str, expected_version: int | None = None) -> bool:
        from datetime import datetime

        with self.session_factory() as session:
            item = session.get(MemoryItem, memory_id)
            if not item:
                return False
            if expected_version is not None and item.version != expected_version:
                raise RuntimeError("version_conflict")
            item.deleted_at = datetime.now()
            item.version += 1
            session.commit()
            return True

    def supersede(self, memory_id: str, content: str, expected_version: int | None = None) -> MemoryItem:
        with self.session_factory() as session:
            previous = session.get(MemoryItem, memory_id)
            if not previous or previous.deleted_at is not None:
                raise ValueError("Memory item does not exist or is deleted")
            if expected_version is not None and previous.version != expected_version:
                raise RuntimeError("version_conflict")
            replacement = MemoryItem(
                conversation_id=previous.conversation_id,
                kind=previous.kind,
                content=content,
                source_message_id=previous.source_message_id,
            )
            session.add(replacement)
            session.flush()
            previous.superseded_by = replacement.id
            previous.version += 1
            session.commit()
            session.refresh(replacement)
            return replacement
