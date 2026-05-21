"""Tests for the FastAPI REST API."""

import pytest
from httpx import ASGITransport, AsyncClient

from decision_memory.api import app, lifespan


@pytest.fixture
async def client():
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


class TestHealth:
    async def test_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestDecisionEndpoints:
    async def test_create_decision(self, client: AsyncClient) -> None:
        resp = await client.post("/decisions", json={"title": "Use FastAPI"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Use FastAPI"
        assert data["status"] == "proposed"
        assert data["id"]

    async def test_get_decision(self, client: AsyncClient) -> None:
        create_resp = await client.post("/decisions", json={"title": "Test"})
        decision_id = create_resp.json()["id"]
        resp = await client.get(f"/decisions/{decision_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test"

    async def test_get_decision_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/decisions/nonexistent")
        assert resp.status_code == 404

    async def test_list_decisions(self, client: AsyncClient) -> None:
        await client.post("/decisions", json={"title": "A"})
        await client.post("/decisions", json={"title": "B"})
        resp = await client.get("/decisions")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_list_by_status(self, client: AsyncClient) -> None:
        await client.post("/decisions", json={"title": "Proposed", "status": "proposed"})
        await client.post("/decisions", json={"title": "Approved", "status": "approved"})
        resp = await client.get("/decisions", params={"status": "approved"})
        assert resp.status_code == 200
        for d in resp.json():
            assert d["status"] == "approved"

    async def test_update_decision(self, client: AsyncClient) -> None:
        create_resp = await client.post("/decisions", json={"title": "Old"})
        decision_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/decisions/{decision_id}",
            json={"title": "New", "status": "approved"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"
        assert resp.json()["status"] == "approved"

    async def test_update_not_found(self, client: AsyncClient) -> None:
        resp = await client.patch("/decisions/bad-id", json={"title": "x"})
        assert resp.status_code == 404

    async def test_delete_decision(self, client: AsyncClient) -> None:
        create_resp = await client.post("/decisions", json={"title": "Delete me"})
        decision_id = create_resp.json()["id"]
        resp = await client.delete(f"/decisions/{decision_id}")
        assert resp.status_code == 204
        resp = await client.get(f"/decisions/{decision_id}")
        assert resp.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient) -> None:
        resp = await client.delete("/decisions/bad-id")
        assert resp.status_code == 404


class TestSearchEndpoint:
    async def test_search_by_keywords(self, client: AsyncClient) -> None:
        await client.post(
            "/decisions",
            json={"title": "Kubernetes deployment", "tags": ["infra"]},
        )
        await client.post(
            "/decisions",
            json={"title": "React frontend", "tags": ["frontend"]},
        )
        resp = await client.post("/decisions/search", json={"keywords": "kubernetes"})
        assert resp.status_code == 200
        results = resp.json()
        assert any("Kubernetes" in r["title"] for r in results)

    async def test_search_by_tags(self, client: AsyncClient) -> None:
        await client.post("/decisions", json={"title": "A", "tags": ["security"]})
        resp = await client.post("/decisions/search", json={"tags": ["security"]})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_search_empty(self, client: AsyncClient) -> None:
        resp = await client.post("/decisions/search", json={"keywords": "nonexistent_xyz"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestTemporalEndpoints:
    async def test_decision_history(self, client: AsyncClient) -> None:
        create_resp = await client.post("/decisions", json={"title": "V1"})
        decision_id = create_resp.json()["id"]
        await client.patch(f"/decisions/{decision_id}", json={"title": "V2"})

        resp = await client.get(f"/decisions/{decision_id}/history")
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) >= 2
        assert history[0]["snapshot"]["title"] == "V1"

    async def test_get_snapshot(self, client: AsyncClient) -> None:
        create_resp = await client.post("/decisions", json={"title": "Snap"})
        decision_id = create_resp.json()["id"]
        history_resp = await client.get(f"/decisions/{decision_id}/history")
        snapshot_id = history_resp.json()[0]["id"]
        resp = await client.get(f"/snapshots/{snapshot_id}")
        assert resp.status_code == 200
        assert resp.json()["snapshot"]["title"] == "Snap"

    async def test_snapshot_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/snapshots/nonexistent")
        assert resp.status_code == 404


class TestRelationshipEndpoints:
    async def test_create_relationship(self, client: AsyncClient) -> None:
        d1 = (await client.post("/decisions", json={"title": "A"})).json()
        d2 = (await client.post("/decisions", json={"title": "B"})).json()
        resp = await client.post(
            "/relationships",
            json={
                "source_id": d1["id"],
                "target_id": d2["id"],
                "relationship_type": "depends_on",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["source_id"] == d1["id"]

    async def test_list_relationships(self, client: AsyncClient) -> None:
        d1 = (await client.post("/decisions", json={"title": "A"})).json()
        d2 = (await client.post("/decisions", json={"title": "B"})).json()
        await client.post(
            "/relationships",
            json={
                "source_id": d1["id"],
                "target_id": d2["id"],
                "relationship_type": "related_to",
            },
        )
        resp = await client.get("/relationships")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_relationship(self, client: AsyncClient) -> None:
        d1 = (await client.post("/decisions", json={"title": "A"})).json()
        d2 = (await client.post("/decisions", json={"title": "B"})).json()
        rel = (
            await client.post(
                "/relationships",
                json={
                    "source_id": d1["id"],
                    "target_id": d2["id"],
                    "relationship_type": "implements",
                },
            )
        ).json()
        resp = await client.get(f"/relationships/{rel['id']}")
        assert resp.status_code == 200

    async def test_delete_relationship(self, client: AsyncClient) -> None:
        d1 = (await client.post("/decisions", json={"title": "A"})).json()
        d2 = (await client.post("/decisions", json={"title": "B"})).json()
        rel = (
            await client.post(
                "/relationships",
                json={
                    "source_id": d1["id"],
                    "target_id": d2["id"],
                    "relationship_type": "supersedes",
                },
            )
        ).json()
        resp = await client.delete(f"/relationships/{rel['id']}")
        assert resp.status_code == 204

    async def test_decision_relationships(self, client: AsyncClient) -> None:
        d1 = (await client.post("/decisions", json={"title": "A"})).json()
        d2 = (await client.post("/decisions", json={"title": "B"})).json()
        await client.post(
            "/relationships",
            json={
                "source_id": d1["id"],
                "target_id": d2["id"],
                "relationship_type": "depends_on",
            },
        )
        resp = await client.get(f"/decisions/{d1['id']}/relationships")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestGraphTraversal:
    async def test_related_decisions(self, client: AsyncClient) -> None:
        d1 = (await client.post("/decisions", json={"title": "A"})).json()
        d2 = (await client.post("/decisions", json={"title": "B"})).json()
        await client.post(
            "/relationships",
            json={
                "source_id": d1["id"],
                "target_id": d2["id"],
                "relationship_type": "depends_on",
            },
        )
        resp = await client.get(f"/decisions/{d1['id']}/related")
        assert resp.status_code == 200

    async def test_dependencies(self, client: AsyncClient) -> None:
        d1 = (await client.post("/decisions", json={"title": "A"})).json()
        d2 = (await client.post("/decisions", json={"title": "B"})).json()
        await client.post(
            "/relationships",
            json={
                "source_id": d1["id"],
                "target_id": d2["id"],
                "relationship_type": "depends_on",
            },
        )
        resp = await client.get(f"/decisions/{d2['id']}/dependencies")
        assert resp.status_code == 200

    async def test_impact(self, client: AsyncClient) -> None:
        d1 = (await client.post("/decisions", json={"title": "A"})).json()
        d2 = (await client.post("/decisions", json={"title": "B"})).json()
        await client.post(
            "/relationships",
            json={
                "source_id": d1["id"],
                "target_id": d2["id"],
                "relationship_type": "depends_on",
            },
        )
        resp = await client.get(f"/decisions/{d1['id']}/impact")
        assert resp.status_code == 200
