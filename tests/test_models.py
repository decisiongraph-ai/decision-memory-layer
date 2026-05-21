"""Tests for Pydantic models."""

from datetime import UTC, datetime

from decision_memory.models import (
    Decision,
    DecisionContext,
    DecisionCreate,
    DecisionStatus,
    DecisionUpdate,
    Relationship,
    RelationshipCreate,
    RelationshipType,
    SearchQuery,
    TemporalSnapshot,
)


class TestDecision:
    def test_create_minimal(self) -> None:
        d = Decision(title="Use Kubernetes")
        assert d.title == "Use Kubernetes"
        assert d.status == DecisionStatus.PROPOSED
        assert d.id
        assert d.created_at
        assert d.tags == []
        assert d.stakeholders == []

    def test_create_full(self) -> None:
        ctx = DecisionContext(
            assumptions=["Cloud-first strategy"],
            constraints=["Budget < 100k"],
            alternatives_considered=["Docker Swarm"],
            evidence=["Benchmark results"],
            risks=["Complexity"],
        )
        d = Decision(
            title="Use Kubernetes",
            description="Container orchestration platform",
            rationale="Industry standard",
            status=DecisionStatus.APPROVED,
            stakeholders=["Alice", "Bob"],
            tags=["infra", "cloud"],
            context=ctx,
            metadata={"priority": "high"},
        )
        assert d.status == DecisionStatus.APPROVED
        assert "Alice" in d.stakeholders
        assert len(d.context.assumptions) == 1
        assert d.metadata["priority"] == "high"

    def test_decision_serialization(self) -> None:
        d = Decision(title="Test", tags=["a", "b"])
        data = d.model_dump()
        restored = Decision(**data)
        assert restored.title == d.title
        assert restored.tags == d.tags
        assert restored.id == d.id


class TestDecisionCreate:
    def test_defaults(self) -> None:
        dc = DecisionCreate(title="New decision")
        assert dc.title == "New decision"
        assert dc.status == DecisionStatus.PROPOSED

    def test_with_fields(self) -> None:
        dc = DecisionCreate(
            title="Migrate DB",
            rationale="Performance improvements",
            tags=["database"],
        )
        assert dc.rationale == "Performance improvements"


class TestDecisionUpdate:
    def test_partial(self) -> None:
        du = DecisionUpdate(title="Updated title")
        assert du.title == "Updated title"
        assert du.status is None
        assert du.tags is None

    def test_exclude_none(self) -> None:
        du = DecisionUpdate(status=DecisionStatus.APPROVED)
        fields = du.model_dump(exclude_none=True)
        assert "status" in fields
        assert "title" not in fields


class TestRelationship:
    def test_create(self) -> None:
        r = Relationship(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        assert r.source_id == "a"
        assert r.relationship_type == RelationshipType.DEPENDS_ON
        assert r.id


class TestRelationshipCreate:
    def test_create(self) -> None:
        rc = RelationshipCreate(
            source_id="a",
            target_id="b",
            relationship_type=RelationshipType.SUPERSEDES,
            description="Replaces old approach",
        )
        assert rc.description == "Replaces old approach"


class TestTemporalSnapshot:
    def test_create(self) -> None:
        d = Decision(title="Original")
        snap = TemporalSnapshot(
            decision_id=d.id,
            snapshot=d,
            change_reason="initial",
        )
        assert snap.decision_id == d.id
        assert snap.snapshot.title == "Original"


class TestSearchQuery:
    def test_minimal(self) -> None:
        sq = SearchQuery()
        assert sq.keywords is None

    def test_full(self) -> None:
        sq = SearchQuery(
            keywords="kubernetes",
            tags=["infra"],
            stakeholders=["Alice"],
            status=DecisionStatus.APPROVED,
            date_from=datetime(2024, 1, 1, tzinfo=UTC),
        )
        assert sq.keywords == "kubernetes"
        assert sq.status == DecisionStatus.APPROVED


class TestDecisionStatus:
    def test_values(self) -> None:
        assert DecisionStatus.PROPOSED.value == "proposed"
        assert DecisionStatus.SUPERSEDED.value == "superseded"


class TestRelationshipType:
    def test_values(self) -> None:
        assert RelationshipType.DEPENDS_ON.value == "depends_on"
        assert RelationshipType.CAUSED_BY.value == "caused_by"
