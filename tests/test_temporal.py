"""Tests for temporal context tracking."""

import pytest

from decision_memory.memory_store import MemoryStore
from decision_memory.models import DecisionCreate, DecisionStatus, DecisionUpdate
from decision_memory.temporal import TemporalTracker


@pytest.fixture
async def services():
    store = MemoryStore(":memory:")
    await store.initialize()
    tracker = TemporalTracker(store.db)
    await tracker.initialize()
    yield store, tracker
    await store.close()


class TestTemporalTracker:
    async def test_create_snapshot(self, services: tuple) -> None:
        store, tracker = services
        decision = await store.create_decision(DecisionCreate(title="Initial"))
        snapshot = await tracker.create_snapshot(decision, "initial creation")
        assert snapshot.decision_id == decision.id
        assert snapshot.change_reason == "initial creation"
        assert snapshot.snapshot.title == "Initial"

    async def test_get_history(self, services: tuple) -> None:
        store, tracker = services
        decision = await store.create_decision(DecisionCreate(title="V1"))
        await tracker.create_snapshot(decision, "v1")

        updated = await store.update_decision(
            decision.id, DecisionUpdate(title="V2", status=DecisionStatus.APPROVED)
        )
        assert updated is not None
        await tracker.create_snapshot(updated, "v2")

        history = await tracker.get_history(decision.id)
        assert len(history) == 2
        assert history[0].snapshot.title == "V1"
        assert history[1].snapshot.title == "V2"

    async def test_get_snapshot(self, services: tuple) -> None:
        store, tracker = services
        decision = await store.create_decision(DecisionCreate(title="Test"))
        snap = await tracker.create_snapshot(decision, "test")
        fetched = await tracker.get_snapshot(snap.id)
        assert fetched is not None
        assert fetched.id == snap.id

    async def test_get_snapshot_nonexistent(self, services: tuple) -> None:
        _, tracker = services
        assert await tracker.get_snapshot("bad-id") is None

    async def test_get_state_at(self, services: tuple) -> None:
        store, tracker = services
        decision = await store.create_decision(DecisionCreate(title="V1"))
        snap1 = await tracker.create_snapshot(decision, "v1")

        updated = await store.update_decision(decision.id, DecisionUpdate(title="V2"))
        assert updated is not None
        await tracker.create_snapshot(updated, "v2")

        state = await tracker.get_state_at(decision.id, snap1.created_at)
        assert state is not None
        assert state.snapshot.title == "V1"

    async def test_get_all_snapshots(self, services: tuple) -> None:
        store, tracker = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        await tracker.create_snapshot(d1, "a")
        await tracker.create_snapshot(d2, "b")

        all_snaps = await tracker.get_all_snapshots()
        assert len(all_snaps) == 2
