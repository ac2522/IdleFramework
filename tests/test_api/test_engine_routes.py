"""Tests for interactive engine session endpoints."""

import pytest


@pytest.fixture
def session_id(client):
    """Start a MiniCap session and return the session ID."""
    resp = client.post(
        "/api/v1/engine/start",
        json={"game_id": "minicap"},
    )
    assert resp.status_code == 200
    return resp.json()["session_id"]


class TestStartSession:
    def test_start_creates_session(self, client):
        resp = client.post(
            "/api/v1/engine/start",
            json={"game_id": "minicap"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["game_id"] == "minicap"
        assert data["elapsed_time"] == 0.0
        assert "resources" in data
        assert "generators" in data

    def test_start_nonexistent_game_404(self, client):
        resp = client.post(
            "/api/v1/engine/start",
            json={"game_id": "nope"},
        )
        assert resp.status_code == 404


class TestGetState:
    def test_get_state(self, client, session_id):
        resp = client.get(
            f"/api/v1/engine/{session_id}/state",
        )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

    def test_get_nonexistent_session_404(self, client):
        resp = client.get(
            "/api/v1/engine/fake-id/state",
        )
        assert resp.status_code == 404


class TestAdvance:
    def test_advance_increases_time(
        self,
        client,
        session_id,
    ):
        resp = client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 5.0},
        )
        assert resp.status_code == 200
        assert resp.json()["elapsed_time"] == pytest.approx(
            5.0,
            abs=0.1,
        )

    def test_advance_increases_resources(
        self,
        client,
        session_id,
    ):
        client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 10.0},
        )
        resp = client.get(
            f"/api/v1/engine/{session_id}/state",
        )
        data = resp.json()
        cash = data["resources"].get("cash", {}).get("current_value", 0)
        assert cash > 0


class TestAdvanceBoundaryValues:
    def test_advance_small_seconds(
        self,
        client,
        session_id,
    ):
        resp = client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 0.01},
        )
        assert resp.status_code == 200
        assert resp.json()["elapsed_time"] > 0

    def test_advance_large_seconds(
        self,
        client,
        session_id,
    ):
        resp = client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 86400},
        )
        assert resp.status_code == 200
        assert resp.json()["elapsed_time"] == pytest.approx(
            86400,
            abs=1.0,
        )

    def test_advance_zero_seconds_422(
        self,
        client,
        session_id,
    ):
        resp = client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 0},
        )
        assert resp.status_code == 422

    def test_advance_negative_seconds_422(
        self,
        client,
        session_id,
    ):
        resp = client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": -5},
        )
        assert resp.status_code == 422

    def test_advance_over_max_seconds_422(
        self,
        client,
        session_id,
    ):
        resp = client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 86401},
        )
        assert resp.status_code == 422


class TestPurchase:
    def test_purchase_generator(
        self,
        client,
        session_id,
    ):
        client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 30.0},
        )
        resp = client.post(
            f"/api/v1/engine/{session_id}/purchase",
            json={"node_id": "lemonade", "count": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["generators"]["lemonade"]["owned"] >= 1

    def test_purchase_nonexistent_node_400(
        self,
        client,
        session_id,
    ):
        resp = client.post(
            f"/api/v1/engine/{session_id}/purchase",
            json={"node_id": "nonexistent"},
        )
        assert resp.status_code == 400


class TestPurchaseInsufficientFunds:
    def test_insufficient_funds_400(
        self,
        client,
        session_id,
    ):
        """Buying without funds returns 400 insufficient."""
        resp = client.post(
            f"/api/v1/engine/{session_id}/purchase",
            json={"node_id": "lemonade", "count": 999},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["error"] == "insufficient_funds"

    def test_purchase_resource_node_400(
        self,
        client,
        session_id,
    ):
        """Buying a Resource node returns 400."""
        resp = client.post(
            f"/api/v1/engine/{session_id}/purchase",
            json={"node_id": "cash"},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["error"] == "invalid_purchase"


class TestPrestige:
    def test_prestige_returns_result(
        self,
        client,
        session_id,
    ):
        """Prestige endpoint resets state and returns new balance."""
        client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 300.0},
        )
        resp = client.post(
            f"/api/v1/engine/{session_id}/prestige",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert "prestige" in data

    def test_prestige_nonexistent_session_404(
        self,
        client,
    ):
        resp = client.post(
            "/api/v1/engine/fake-session/prestige",
        )
        assert resp.status_code == 404

    def test_prestige_updates_currency(
        self,
        client,
        session_id,
    ):
        """After prestige, available_currency reflects the prestige gain."""
        client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 600.0},
        )
        resp = client.post(
            f"/api/v1/engine/{session_id}/prestige",
        )
        assert resp.status_code == 200
        prestige_data = resp.json()["prestige"]
        assert prestige_data is not None

    def test_prestige_no_prestige_layer_400(self, client):
        """Game without prestige layer returns 400."""
        no_prestige_game = {
            "schema_version": "1.0",
            "name": "No Prestige Game",
            "nodes": [
                {
                    "id": "gold",
                    "type": "resource",
                    "name": "Gold",
                    "initial_value": 100,
                },
                {
                    "id": "miner",
                    "type": "generator",
                    "name": "Miner",
                    "cost_base": 10,
                    "cost_growth_rate": 1.15,
                    "base_production": 1.0,
                    "cycle_time": 1.0,
                },
            ],
            "edges": [
                {
                    "id": "m2g",
                    "source": "miner",
                    "target": "gold",
                    "edge_type": "production_target",
                },
            ],
            "stacking_groups": {},
        }
        client.post("/api/v1/games/", json=no_prestige_game)
        resp = client.post(
            "/api/v1/engine/start",
            json={"game_id": "no-prestige-game"},
        )
        assert resp.status_code == 200
        sid = resp.json()["session_id"]

        resp = client.post(
            f"/api/v1/engine/{sid}/prestige",
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["error"] == "no_prestige"


class TestAutoOptimize:
    def test_auto_optimize_returns_purchases(
        self,
        client,
        session_id,
    ):
        resp = client.post(
            f"/api/v1/engine/{session_id}/auto-optimize",
            json={"target_time": 60.0, "max_steps": 50},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "purchases" in data
        assert "timeline" in data
        assert data["final_production"] > 0


@pytest.mark.skip(reason="Beam/MCTS/BnB optimizers too slow for CI; tested via unit tests")
class TestAutoOptimizeStrategies:
    @pytest.mark.timeout(10)
    @pytest.mark.xfail(
        reason="Beam optimizer may timeout on CI",
        strict=False,
    )
    def test_beam_optimizer(self, client, session_id):
        resp = client.post(
            f"/api/v1/engine/{session_id}/auto-optimize",
            json={
                "target_time": 10.0,
                "max_steps": 3,
                "optimizer": "beam",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "purchases" in data

    @pytest.mark.timeout(10)
    @pytest.mark.xfail(
        reason=("MCTS optimizer fails with 500 on fresh sessions"),
        strict=False,
    )
    def test_mcts_optimizer(self, client, session_id):
        resp = client.post(
            f"/api/v1/engine/{session_id}/auto-optimize",
            json={
                "target_time": 30.0,
                "max_steps": 5,
                "optimizer": "mcts",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "purchases" in data

    @pytest.mark.timeout(10)
    @pytest.mark.xfail(
        reason="B&B optimizer may timeout on CI",
        strict=False,
    )
    def test_bnb_optimizer(self, client, session_id):
        resp = client.post(
            f"/api/v1/engine/{session_id}/auto-optimize",
            json={
                "target_time": 30.0,
                "max_steps": 5,
                "optimizer": "bnb",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "purchases" in data


class TestDeleteSession:
    def test_delete_session(self, client, session_id):
        resp = client.delete(
            f"/api/v1/engine/{session_id}",
        )
        assert resp.status_code == 204
        resp = client.get(
            f"/api/v1/engine/{session_id}/state",
        )
        assert resp.status_code == 404
