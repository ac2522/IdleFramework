"""Tests for interactive engine session endpoints."""
import pytest
from fastapi.testclient import TestClient
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session_id(client):
    """Start a MiniCap session and return the session ID."""
    resp = client.post("/api/v1/engine/start", json={"game_id": "minicap"})
    assert resp.status_code == 200
    return resp.json()["session_id"]


class TestStartSession:
    def test_start_creates_session(self, client):
        resp = client.post("/api/v1/engine/start", json={"game_id": "minicap"})
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["game_id"] == "minicap"
        assert data["elapsed_time"] == 0.0
        assert "resources" in data
        assert "generators" in data

    def test_start_nonexistent_game_404(self, client):
        resp = client.post("/api/v1/engine/start", json={"game_id": "nope"})
        assert resp.status_code == 404


class TestGetState:
    def test_get_state(self, client, session_id):
        resp = client.get(f"/api/v1/engine/{session_id}/state")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

    def test_get_nonexistent_session_404(self, client):
        resp = client.get("/api/v1/engine/fake-id/state")
        assert resp.status_code == 404


class TestAdvance:
    def test_advance_increases_time(self, client, session_id):
        resp = client.post(f"/api/v1/engine/{session_id}/advance", json={"seconds": 5.0})
        assert resp.status_code == 200
        assert resp.json()["elapsed_time"] == pytest.approx(5.0, abs=0.1)

    def test_advance_increases_resources(self, client, session_id):
        # First advance to generate some cash
        client.post(f"/api/v1/engine/{session_id}/advance", json={"seconds": 10.0})
        resp = client.get(f"/api/v1/engine/{session_id}/state")
        data = resp.json()
        # Should have some cash after advancing (initial balance + production)
        cash = data["resources"].get("cash", {}).get("current_value", 0)
        assert cash > 0


class TestPurchase:
    def test_purchase_generator(self, client, session_id):
        # Advance to accumulate cash
        client.post(f"/api/v1/engine/{session_id}/advance", json={"seconds": 30.0})
        resp = client.post(f"/api/v1/engine/{session_id}/purchase", json={
            "node_id": "lemonade",
            "count": 1,
        })
        assert resp.status_code == 200
        # Verify owned count increased
        data = resp.json()
        assert data["generators"]["lemonade"]["owned"] >= 1

    def test_purchase_nonexistent_node_400(self, client, session_id):
        resp = client.post(f"/api/v1/engine/{session_id}/purchase", json={
            "node_id": "nonexistent",
        })
        assert resp.status_code == 400


class TestAutoOptimize:
    def test_auto_optimize_returns_purchases(self, client, session_id):
        resp = client.post(f"/api/v1/engine/{session_id}/auto-optimize", json={
            "target_time": 60.0,
            "max_steps": 50,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "purchases" in data
        assert "timeline" in data
        assert data["final_production"] > 0


class TestDeleteSession:
    def test_delete_session(self, client, session_id):
        resp = client.delete(f"/api/v1/engine/{session_id}")
        assert resp.status_code == 204
        # Verify gone
        resp = client.get(f"/api/v1/engine/{session_id}/state")
        assert resp.status_code == 404
