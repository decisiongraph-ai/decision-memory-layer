"""Pydantic models for decisions, context, relationships, and temporal snapshots."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DecisionStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    IMPLEMENTED = "implemented"
    ARCHIVED = "archived"


class RelationshipType(StrEnum):
    DEPENDS_ON = "depends_on"
    SUPERSEDES = "supersedes"
    RELATED_TO = "related_to"
    CONFLICTS_WITH = "conflicts_with"
    IMPLEMENTS = "implements"
    CAUSED_BY = "caused_by"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class DecisionContext(BaseModel):
    """Contextual information surrounding a decision."""

    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    alternatives_considered: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class Decision(BaseModel):
    """Core decision entity with full context."""

    id: str = Field(default_factory=_new_id)
    title: str
    description: str = ""
    rationale: str = ""
    status: DecisionStatus = DecisionStatus.PROPOSED
    stakeholders: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    context: DecisionContext = Field(default_factory=DecisionContext)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class DecisionCreate(BaseModel):
    """Schema for creating a new decision."""

    title: str
    description: str = ""
    rationale: str = ""
    status: DecisionStatus = DecisionStatus.PROPOSED
    stakeholders: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    context: DecisionContext = Field(default_factory=DecisionContext)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionUpdate(BaseModel):
    """Schema for updating an existing decision (partial)."""

    title: str | None = None
    description: str | None = None
    rationale: str | None = None
    status: DecisionStatus | None = None
    stakeholders: list[str] | None = None
    tags: list[str] | None = None
    context: DecisionContext | None = None
    metadata: dict[str, Any] | None = None


class Relationship(BaseModel):
    """A directed relationship between two decisions."""

    id: str = Field(default_factory=_new_id)
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    description: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class RelationshipCreate(BaseModel):
    """Schema for creating a relationship."""

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    description: str = ""


class TemporalSnapshot(BaseModel):
    """A point-in-time snapshot of a decision's state."""

    id: str = Field(default_factory=_new_id)
    decision_id: str
    snapshot: Decision
    change_reason: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class SearchQuery(BaseModel):
    """Query parameters for decision search."""

    keywords: str | None = None
    tags: list[str] | None = None
    stakeholders: list[str] | None = None
    status: DecisionStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
