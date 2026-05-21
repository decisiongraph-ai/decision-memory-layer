"""Tests for the memory store (SQLite persistence)."""

import pytest

from decision_memory.memory_store import MemoryStore
from decision_memory.models import DecisionCreate, DecisionStatus, DecisionUpdate


@pytest.fixture
async def store():
    s = MemoryStore(":memory:")
    await s.initialize()
    yield s
    await s.close()


class TestMemoryStore:
    async def test_create_and_get(self, store: MemoryStore) -> None:
        data = DecisionCreate(title="Use FastAPI", description="Web framework choice")
        decision = await store.create_decision(data)
        assert decision.title == "Use FastAPI"
        assert decision.id

        fetched = await store.get_decision(decision.id)
        assert fetched is not None
        assert fetched.title == "Use FastAPI"

    async def test_get_nonexistent(self, store: MemoryStore) -> None:
        result = await store.get_decision("nonexistent")
        assert result is None

    async def test_update(self, store: MemoryStore) -> None:
        data = DecisionCreate(title="Old title")
        decision = await store.create_decision(data)

        updated = await store.update_decision(
            decision.id, DecisionUpdate(title="New title", status=DecisionStatus.APPROVED)
        )
        assert updated is not None
        assert updated.title == "New title"
        assert updated.status == DecisionStatus.APPROVED
        assert updated.updated_at > decision.created_at

    async def test_update_nonexistent(self, store: MemoryStore) -> None:
        result = await store.update_decision("bad-id", DecisionUpdate(title="x"))
        assert result is None

    async def test_delete(self, store: MemoryStore) -> None:
        data = DecisionCreate(title="To delete")
        decision = await store.create_decision(data)
        assert await store.delete_decision(decision.id) is True
        assert await store.get_decision(decision.id) is None

    async def test_delete_nonexistent(self, store: MemoryStore) -> None:
        assert await store.delete_decision("bad-id") is False

    async def test_list_decisions(self, store: MemoryStore) -> None:
        for i in range(5):
            await store.create_decision(DecisionCreate(title=f"Decision {i}"))
        results = await store.list_decisions()
        assert len(results) == 5

    async def test_list_by_status(self, store: MemoryStore) -> None:
        await store.create_decision(DecisionCreate(title="A", status=DecisionStatus.PROPOSED))
        await store.create_decision(DecisionCreate(title="B", status=DecisionStatus.APPROVED))
        await store.create_decision(DecisionCreate(title="C", status=DecisionStatus.APPROVED))

        proposed = await store.list_decisions(status=DecisionStatus.PROPOSED)
        assert len(proposed) == 1
        approved = await store.list_decisions(status=DecisionStatus.APPROVED)
        assert len(approved) == 2

    async def test_list_pagination(self, store: MemoryStore) -> None:
        for i in range(10):
            await store.create_decision(DecisionCreate(title=f"D{i}"))
        page1 = await store.list_decisions(limit=3, offset=0)
        page2 = await store.list_decisions(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].id != page2[0].id

    async def test_search_by_tags(self, store: MemoryStore) -> None:
        await store.create_decision(DecisionCreate(title="A", tags=["infra", "cloud"]))
        await store.create_decision(DecisionCreate(title="B", tags=["frontend"]))
        results = await store.search_by_tags(["infra"])
        assert len(results) == 1
        assert results[0].title == "A"

    async def test_search_by_stakeholders(self, store: MemoryStore) -> None:
        await store.create_decision(DecisionCreate(title="A", stakeholders=["Alice"]))
        await store.create_decision(DecisionCreate(title="B", stakeholders=["Bob"]))
        results = await store.search_by_stakeholders(["Alice"])
        assert len(results) == 1

    async def test_search_by_date_range(self, store: MemoryStore) -> None:
        d1 = await store.create_decision(DecisionCreate(title="Old"))
        await store.create_decision(DecisionCreate(title="New"))
        results = await store.search_by_date_range(date_from=d1.created_at)
        assert len(results) >= 1
