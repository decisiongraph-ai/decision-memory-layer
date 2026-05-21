"""FastAPI REST API for the Decision Memory Layer."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from .knowledge_graph import KnowledgeGraph
from .memory_store import MemoryStore
from .models import (
    Decision,
    DecisionCreate,
    DecisionStatus,
    DecisionUpdate,
    Relationship,
    RelationshipCreate,
    SearchQuery,
    TemporalSnapshot,
)
from .retrieval import RetrievalEngine
from .temporal import TemporalTracker

_store: MemoryStore | None = None
_tracker: TemporalTracker | None = None
_graph: KnowledgeGraph | None = None
_retrieval: RetrievalEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _store, _tracker, _graph, _retrieval
    db_path = os.environ.get("DML_DB_PATH", ":memory:")
    _store = MemoryStore(db_path)
    await _store.initialize()
    _tracker = TemporalTracker(_store.db)
    await _tracker.initialize()
    _graph = KnowledgeGraph(_store.db)
    await _graph.initialize()
    _retrieval = RetrievalEngine(_store, _graph)
    yield
    await _store.close()


app = FastAPI(
    title="Decision Memory Layer",
    description="Persistent organizational memory for enterprise decision intelligence",
    version="0.1.0",
    lifespan=lifespan,
)


def _get_store() -> MemoryStore:
    if _store is None:
        raise RuntimeError("Store not initialized")
    return _store


def _get_tracker() -> TemporalTracker:
    if _tracker is None:
        raise RuntimeError("Temporal tracker not initialized")
    return _tracker


def _get_graph() -> KnowledgeGraph:
    if _graph is None:
        raise RuntimeError("Knowledge graph not initialized")
    return _graph


def _get_retrieval() -> RetrievalEngine:
    if _retrieval is None:
        raise RuntimeError("Retrieval engine not initialized")
    return _retrieval


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


# --- Decision CRUD ---


@app.post("/decisions", response_model=Decision, status_code=201)
async def create_decision(data: DecisionCreate) -> Decision:
    store = _get_store()
    tracker = _get_tracker()
    decision = await store.create_decision(data)
    await tracker.create_snapshot(decision, change_reason="initial creation")
    return decision


@app.get("/decisions", response_model=list[Decision])
async def list_decisions(
    status: DecisionStatus | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[Decision]:
    return await _get_store().list_decisions(status=status, limit=limit, offset=offset)


@app.get("/decisions/{decision_id}", response_model=Decision)
async def get_decision(decision_id: str) -> Decision:
    decision = await _get_store().get_decision(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@app.patch("/decisions/{decision_id}", response_model=Decision)
async def update_decision(decision_id: str, data: DecisionUpdate) -> Decision:
    store = _get_store()
    tracker = _get_tracker()
    decision = await store.update_decision(decision_id, data)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    await tracker.create_snapshot(decision, change_reason="updated")
    return decision


@app.delete("/decisions/{decision_id}", status_code=204)
async def delete_decision(decision_id: str) -> None:
    deleted = await _get_store().delete_decision(decision_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Decision not found")


# --- Search ---


@app.post("/decisions/search", response_model=list[Decision])
async def search_decisions(query: SearchQuery) -> list[Decision]:
    return await _get_retrieval().search(query)


# --- Temporal ---


@app.get("/decisions/{decision_id}/history", response_model=list[TemporalSnapshot])
async def get_decision_history(decision_id: str) -> list[TemporalSnapshot]:
    return await _get_tracker().get_history(decision_id)


@app.get("/snapshots/{snapshot_id}", response_model=TemporalSnapshot)
async def get_snapshot(snapshot_id: str) -> TemporalSnapshot:
    snapshot = await _get_tracker().get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot


# --- Relationships ---


@app.post("/relationships", response_model=Relationship, status_code=201)
async def create_relationship(data: RelationshipCreate) -> Relationship:
    return await _get_graph().add_relationship(data)


@app.get("/relationships", response_model=list[Relationship])
async def list_relationships(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[Relationship]:
    return await _get_graph().list_relationships(limit=limit, offset=offset)


@app.get("/relationships/{relationship_id}", response_model=Relationship)
async def get_relationship(relationship_id: str) -> Relationship:
    rel = await _get_graph().get_relationship(relationship_id)
    if rel is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return rel


@app.delete("/relationships/{relationship_id}", status_code=204)
async def delete_relationship(relationship_id: str) -> None:
    deleted = await _get_graph().delete_relationship(relationship_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")


@app.get("/decisions/{decision_id}/relationships", response_model=list[Relationship])
async def get_decision_relationships(decision_id: str) -> list[Relationship]:
    return await _get_graph().get_relationships_for(decision_id)


# --- Graph traversal ---


@app.get("/decisions/{decision_id}/related", response_model=list[Decision])
async def get_related_decisions(
    decision_id: str,
    max_depth: int = Query(default=2, ge=1, le=5),
) -> list[Decision]:
    return await _get_retrieval().get_related(decision_id, max_depth=max_depth)


@app.get("/decisions/{decision_id}/dependencies", response_model=list[Decision])
async def get_dependencies(decision_id: str) -> list[Decision]:
    return await _get_retrieval().get_dependency_chain(decision_id)


@app.get("/decisions/{decision_id}/impact", response_model=list[Decision])
async def get_impact(decision_id: str) -> list[Decision]:
    return await _get_retrieval().get_impact_chain(decision_id)
