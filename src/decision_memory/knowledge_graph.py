"""Lightweight knowledge graph for decision relationships using networkx."""

from __future__ import annotations

from datetime import datetime

import aiosqlite
import networkx as nx

from .models import Relationship, RelationshipCreate, RelationshipType, _new_id, _utcnow

_SCHEMA = """
CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
"""


class KnowledgeGraph:
    """Maps relationships between decisions, stakeholders, and workflows."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db
        self._graph = nx.DiGraph()

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    async def initialize(self) -> None:
        await self._db.executescript(_SCHEMA)
        await self._db.commit()
        await self._rebuild_graph()

    async def _rebuild_graph(self) -> None:
        self._graph.clear()
        cursor = await self._db.execute("SELECT * FROM relationships")
        rows = await cursor.fetchall()
        for row in rows:
            rel = self._row_to_relationship(row)
            self._graph.add_edge(
                rel.source_id,
                rel.target_id,
                id=rel.id,
                relationship_type=rel.relationship_type.value,
                description=rel.description,
                created_at=rel.created_at.isoformat(),
            )

    async def add_relationship(self, data: RelationshipCreate) -> Relationship:
        rel = Relationship(
            id=_new_id(),
            source_id=data.source_id,
            target_id=data.target_id,
            relationship_type=data.relationship_type,
            description=data.description,
            created_at=_utcnow(),
        )
        await self._db.execute(
            "INSERT INTO relationships VALUES (?, ?, ?, ?, ?, ?)",
            (
                rel.id,
                rel.source_id,
                rel.target_id,
                rel.relationship_type.value,
                rel.description,
                rel.created_at.isoformat(),
            ),
        )
        await self._db.commit()
        self._graph.add_edge(
            rel.source_id,
            rel.target_id,
            id=rel.id,
            relationship_type=rel.relationship_type.value,
            description=rel.description,
            created_at=rel.created_at.isoformat(),
        )
        return rel

    async def get_relationship(self, relationship_id: str) -> Relationship | None:
        cursor = await self._db.execute(
            "SELECT * FROM relationships WHERE id = ?", (relationship_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_relationship(row)

    async def delete_relationship(self, relationship_id: str) -> bool:
        rel = await self.get_relationship(relationship_id)
        if rel is None:
            return False
        await self._db.execute("DELETE FROM relationships WHERE id = ?", (relationship_id,))
        await self._db.commit()
        if self._graph.has_edge(rel.source_id, rel.target_id):
            self._graph.remove_edge(rel.source_id, rel.target_id)
        return True

    async def get_relationships_for(self, decision_id: str) -> list[Relationship]:
        cursor = await self._db.execute(
            "SELECT * FROM relationships WHERE source_id = ? OR target_id = ?",
            (decision_id, decision_id),
        )
        rows = await cursor.fetchall()
        return [self._row_to_relationship(r) for r in rows]

    async def list_relationships(self, limit: int = 100, offset: int = 0) -> list[Relationship]:
        cursor = await self._db.execute(
            "SELECT * FROM relationships ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [self._row_to_relationship(r) for r in rows]

    def get_related_decisions(self, decision_id: str, max_depth: int = 2) -> list[str]:
        if decision_id not in self._graph:
            return []
        related: set[str] = set()
        undirected = self._graph.to_undirected()
        path_lengths = nx.single_source_shortest_path_length(
            undirected, decision_id, cutoff=max_depth
        )
        for node in path_lengths:
            if node != decision_id:
                related.add(node)
        return sorted(related)

    def get_dependency_chain(self, decision_id: str) -> list[str]:
        if decision_id not in self._graph:
            return []
        return list(nx.ancestors(self._graph, decision_id))

    def get_impact_chain(self, decision_id: str) -> list[str]:
        if decision_id not in self._graph:
            return []
        return list(nx.descendants(self._graph, decision_id))

    @staticmethod
    def _row_to_relationship(row: aiosqlite.Row) -> Relationship:
        return Relationship(
            id=row[0],
            source_id=row[1],
            target_id=row[2],
            relationship_type=RelationshipType(row[3]),
            description=row[4],
            created_at=datetime.fromisoformat(row[5]),
        )
