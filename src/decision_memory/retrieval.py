"""Query interface for decision retrieval — keyword + metadata filtering."""

from __future__ import annotations

from .knowledge_graph import KnowledgeGraph
from .memory_store import MemoryStore
from .models import Decision, SearchQuery


class RetrievalEngine:
    """Unified search across memory store and knowledge graph."""

    def __init__(self, store: MemoryStore, graph: KnowledgeGraph) -> None:
        self._store = store
        self._graph = graph

    async def search(self, query: SearchQuery) -> list[Decision]:
        candidates = await self._gather_candidates(query)
        ranked = self._rank(candidates, query)
        return ranked

    async def _gather_candidates(self, query: SearchQuery) -> list[Decision]:
        candidate_ids: set[str] | None = None

        if query.tags:
            tag_results = await self._store.search_by_tags(query.tags)
            ids = {d.id for d in tag_results}
            candidate_ids = ids if candidate_ids is None else candidate_ids & ids

        if query.stakeholders:
            sh_results = await self._store.search_by_stakeholders(query.stakeholders)
            ids = {d.id for d in sh_results}
            candidate_ids = ids if candidate_ids is None else candidate_ids & ids

        if query.date_from or query.date_to:
            date_results = await self._store.search_by_date_range(query.date_from, query.date_to)
            ids = {d.id for d in date_results}
            candidate_ids = ids if candidate_ids is None else candidate_ids & ids

        if query.status:
            status_results = await self._store.list_decisions(status=query.status, limit=10000)
            ids = {d.id for d in status_results}
            candidate_ids = ids if candidate_ids is None else candidate_ids & ids

        if candidate_ids is None:
            all_decisions = await self._store.list_decisions(limit=10000)
        else:
            all_decisions = []
            for did in candidate_ids:
                d = await self._store.get_decision(did)
                if d is not None:
                    all_decisions.append(d)

        if query.keywords:
            all_decisions = self._keyword_filter(all_decisions, query.keywords)

        return all_decisions

    @staticmethod
    def _keyword_filter(decisions: list[Decision], keywords: str) -> list[Decision]:
        terms = keywords.lower().split()
        results = []
        for d in decisions:
            searchable = " ".join([
                d.title,
                d.description,
                d.rationale,
                " ".join(d.tags),
                " ".join(d.stakeholders),
            ]).lower()
            if all(t in searchable for t in terms):
                results.append(d)
        return results

    @staticmethod
    def _rank(decisions: list[Decision], query: SearchQuery) -> list[Decision]:
        if not query.keywords:
            return sorted(decisions, key=lambda d: d.updated_at, reverse=True)

        terms = query.keywords.lower().split()

        def score(d: Decision) -> float:
            text = " ".join([
                d.title,
                d.description,
                d.rationale,
                " ".join(d.tags),
            ]).lower()
            return sum(text.count(t) for t in terms)

        return sorted(decisions, key=score, reverse=True)

    async def get_related(self, decision_id: str, max_depth: int = 2) -> list[Decision]:
        related_ids = self._graph.get_related_decisions(decision_id, max_depth=max_depth)
        decisions = []
        for did in related_ids:
            d = await self._store.get_decision(did)
            if d is not None:
                decisions.append(d)
        return decisions

    async def get_dependency_chain(self, decision_id: str) -> list[Decision]:
        chain_ids = self._graph.get_dependency_chain(decision_id)
        decisions = []
        for did in chain_ids:
            d = await self._store.get_decision(did)
            if d is not None:
                decisions.append(d)
        return decisions

    async def get_impact_chain(self, decision_id: str) -> list[Decision]:
        chain_ids = self._graph.get_impact_chain(decision_id)
        decisions = []
        for did in chain_ids:
            d = await self._store.get_decision(did)
            if d is not None:
                decisions.append(d)
        return decisions
