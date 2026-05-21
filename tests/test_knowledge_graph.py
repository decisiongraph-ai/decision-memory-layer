"""Tests for the knowledge graph."""

import pytest

from decision_memory.knowledge_graph import KnowledgeGraph
from decision_memory.memory_store import MemoryStore
from decision_memory.models import DecisionCreate, RelationshipCreate, RelationshipType


@pytest.fixture
async def services():
    store = MemoryStore(":memory:")
    await store.initialize()
    graph = KnowledgeGraph(store.db)
    await graph.initialize()
    yield store, graph
    await store.close()


class TestKnowledgeGraph:
    async def test_add_relationship(self, services: tuple) -> None:
        store, graph = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        rel = await graph.add_relationship(
            RelationshipCreate(
                source_id=d1.id,
                target_id=d2.id,
                relationship_type=RelationshipType.DEPENDS_ON,
                description="A depends on B",
            )
        )
        assert rel.source_id == d1.id
        assert rel.target_id == d2.id

    async def test_get_relationship(self, services: tuple) -> None:
        store, graph = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        rel = await graph.add_relationship(
            RelationshipCreate(
                source_id=d1.id,
                target_id=d2.id,
                relationship_type=RelationshipType.RELATED_TO,
            )
        )
        fetched = await graph.get_relationship(rel.id)
        assert fetched is not None
        assert fetched.id == rel.id

    async def test_get_relationship_nonexistent(self, services: tuple) -> None:
        _, graph = services
        assert await graph.get_relationship("bad-id") is None

    async def test_delete_relationship(self, services: tuple) -> None:
        store, graph = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        rel = await graph.add_relationship(
            RelationshipCreate(
                source_id=d1.id,
                target_id=d2.id,
                relationship_type=RelationshipType.SUPERSEDES,
            )
        )
        assert await graph.delete_relationship(rel.id) is True
        assert await graph.get_relationship(rel.id) is None

    async def test_delete_nonexistent(self, services: tuple) -> None:
        _, graph = services
        assert await graph.delete_relationship("bad-id") is False

    async def test_get_relationships_for(self, services: tuple) -> None:
        store, graph = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        d3 = await store.create_decision(DecisionCreate(title="C"))
        await graph.add_relationship(
            RelationshipCreate(
                source_id=d1.id, target_id=d2.id, relationship_type=RelationshipType.DEPENDS_ON
            )
        )
        await graph.add_relationship(
            RelationshipCreate(
                source_id=d3.id, target_id=d1.id, relationship_type=RelationshipType.RELATED_TO
            )
        )
        rels = await graph.get_relationships_for(d1.id)
        assert len(rels) == 2

    async def test_list_relationships(self, services: tuple) -> None:
        store, graph = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        await graph.add_relationship(
            RelationshipCreate(
                source_id=d1.id, target_id=d2.id, relationship_type=RelationshipType.IMPLEMENTS
            )
        )
        rels = await graph.list_relationships()
        assert len(rels) == 1

    async def test_get_related_decisions(self, services: tuple) -> None:
        store, graph = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        d3 = await store.create_decision(DecisionCreate(title="C"))
        await graph.add_relationship(
            RelationshipCreate(
                source_id=d1.id, target_id=d2.id, relationship_type=RelationshipType.DEPENDS_ON
            )
        )
        await graph.add_relationship(
            RelationshipCreate(
                source_id=d2.id, target_id=d3.id, relationship_type=RelationshipType.DEPENDS_ON
            )
        )
        related = graph.get_related_decisions(d1.id, max_depth=2)
        assert d2.id in related
        assert d3.id in related

    async def test_get_related_nonexistent(self, services: tuple) -> None:
        _, graph = services
        assert graph.get_related_decisions("bad-id") == []

    async def test_dependency_chain(self, services: tuple) -> None:
        store, graph = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        d3 = await store.create_decision(DecisionCreate(title="C"))
        await graph.add_relationship(
            RelationshipCreate(
                source_id=d1.id, target_id=d2.id, relationship_type=RelationshipType.DEPENDS_ON
            )
        )
        await graph.add_relationship(
            RelationshipCreate(
                source_id=d2.id, target_id=d3.id, relationship_type=RelationshipType.DEPENDS_ON
            )
        )
        deps = graph.get_dependency_chain(d3.id)
        assert d1.id in deps
        assert d2.id in deps

    async def test_impact_chain(self, services: tuple) -> None:
        store, graph = services
        d1 = await store.create_decision(DecisionCreate(title="A"))
        d2 = await store.create_decision(DecisionCreate(title="B"))
        await graph.add_relationship(
            RelationshipCreate(
                source_id=d1.id, target_id=d2.id, relationship_type=RelationshipType.DEPENDS_ON
            )
        )
        impact = graph.get_impact_chain(d1.id)
        assert d2.id in impact
