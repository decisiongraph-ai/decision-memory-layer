"""Temporal context tracking — decision evolution over time."""

from __future__ import annotations

import json
from datetime import datetime

import aiosqlite

from .models import Decision, TemporalSnapshot, _new_id, _utcnow

_SCHEMA = """
CREATE TABLE IF NOT EXISTS temporal_snapshots (
    id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    snapshot TEXT NOT NULL,
    change_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_decision_id ON temporal_snapshots(decision_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON temporal_snapshots(created_at);
"""


class TemporalTracker:
    """Tracks how decisions evolve over time via snapshots."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def initialize(self) -> None:
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def create_snapshot(
        self, decision: Decision, change_reason: str = ""
    ) -> TemporalSnapshot:
        snapshot = TemporalSnapshot(
            id=_new_id(),
            decision_id=decision.id,
            snapshot=decision.model_copy(deep=True),
            change_reason=change_reason,
            created_at=_utcnow(),
        )
        await self._db.execute(
            "INSERT INTO temporal_snapshots VALUES (?, ?, ?, ?, ?)",
            (
                snapshot.id,
                snapshot.decision_id,
                snapshot.snapshot.model_dump_json(),
                snapshot.change_reason,
                snapshot.created_at.isoformat(),
            ),
        )
        await self._db.commit()
        return snapshot

    async def get_history(self, decision_id: str) -> list[TemporalSnapshot]:
        cursor = await self._db.execute(
            "SELECT * FROM temporal_snapshots WHERE decision_id = ? ORDER BY created_at ASC",
            (decision_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    async def get_snapshot(self, snapshot_id: str) -> TemporalSnapshot | None:
        cursor = await self._db.execute(
            "SELECT * FROM temporal_snapshots WHERE id = ?",
            (snapshot_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_snapshot(row)

    async def get_state_at(
        self, decision_id: str, point_in_time: datetime
    ) -> TemporalSnapshot | None:
        cursor = await self._db.execute(
            """SELECT * FROM temporal_snapshots
            WHERE decision_id = ? AND created_at <= ?
            ORDER BY created_at DESC LIMIT 1""",
            (decision_id, point_in_time.isoformat()),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_snapshot(row)

    async def get_all_snapshots(self, limit: int = 100, offset: int = 0) -> list[TemporalSnapshot]:
        cursor = await self._db.execute(
            "SELECT * FROM temporal_snapshots ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    @staticmethod
    def _row_to_snapshot(row: aiosqlite.Row) -> TemporalSnapshot:
        snapshot_data = json.loads(row[2])
        return TemporalSnapshot(
            id=row[0],
            decision_id=row[1],
            snapshot=Decision(**snapshot_data),
            change_reason=row[3],
            created_at=datetime.fromisoformat(row[4]),
        )
