"""In-memory + SQLite persistence for decisions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from .models import Decision, DecisionCreate, DecisionStatus, DecisionUpdate, _new_id, _utcnow

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'proposed',
    stakeholders TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]',
    context TEXT NOT NULL DEFAULT '{}',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at);
"""


def _decision_to_row(d: Decision) -> tuple:
    return (
        d.id,
        d.title,
        d.description,
        d.rationale,
        d.status.value,
        json.dumps(d.stakeholders),
        json.dumps(d.tags),
        d.context.model_dump_json(),
        json.dumps(d.metadata),
        d.created_at.isoformat(),
        d.updated_at.isoformat(),
    )


def _row_to_decision(row: aiosqlite.Row) -> Decision:
    return Decision(
        id=row[0],
        title=row[1],
        description=row[2],
        rationale=row[3],
        status=DecisionStatus(row[4]),
        stakeholders=json.loads(row[5]),
        tags=json.loads(row[6]),
        context=json.loads(row[7]),
        metadata=json.loads(row[8]),
        created_at=datetime.fromisoformat(row[9]),
        updated_at=datetime.fromisoformat(row[10]),
    )


class MemoryStore:
    """Decision persistence backed by SQLite."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Store not initialized. Call initialize() first.")
        return self._db

    async def create_decision(self, data: DecisionCreate) -> Decision:
        now = _utcnow()
        decision = Decision(
            id=_new_id(),
            title=data.title,
            description=data.description,
            rationale=data.rationale,
            status=data.status,
            stakeholders=data.stakeholders,
            tags=data.tags,
            context=data.context,
            metadata=data.metadata,
            created_at=now,
            updated_at=now,
        )
        row = _decision_to_row(decision)
        await self.db.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )
        await self.db.commit()
        return decision

    async def get_decision(self, decision_id: str) -> Decision | None:
        cursor = await self.db.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_decision(row)

    async def update_decision(self, decision_id: str, data: DecisionUpdate) -> Decision | None:
        existing = await self.get_decision(decision_id)
        if existing is None:
            return None

        updates = data.model_dump(exclude_none=True)
        if not updates:
            return existing

        for field, value in updates.items():
            setattr(existing, field, value)
        existing.updated_at = _utcnow()

        row = _decision_to_row(existing)
        await self.db.execute(
            """UPDATE decisions SET
                title=?, description=?, rationale=?, status=?,
                stakeholders=?, tags=?, context=?, metadata=?,
                created_at=?, updated_at=?
            WHERE id=?""",
            (*row[1:], row[0]),
        )
        await self.db.commit()
        return existing

    async def delete_decision(self, decision_id: str) -> bool:
        cursor = await self.db.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    async def list_decisions(
        self,
        status: DecisionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Decision]:
        if status is not None:
            cursor = await self.db.execute(
                "SELECT * FROM decisions WHERE status = ?"
                " ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status.value, limit, offset),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        rows = await cursor.fetchall()
        return [_row_to_decision(r) for r in rows]

    async def search_by_tags(self, tags: list[str]) -> list[Decision]:
        all_decisions = await self.list_decisions(limit=10000)
        return [d for d in all_decisions if any(t in d.tags for t in tags)]

    async def search_by_stakeholders(self, stakeholders: list[str]) -> list[Decision]:
        all_decisions = await self.list_decisions(limit=10000)
        return [d for d in all_decisions if any(s in d.stakeholders for s in stakeholders)]

    async def search_by_date_range(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[Decision]:
        all_decisions = await self.list_decisions(limit=10000)
        results = []
        for d in all_decisions:
            created = d.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if date_from and created < date_from:
                continue
            if date_to and created > date_to:
                continue
            results.append(d)
        return results
