"""End-to-end integration tests for the IdleFramework API."""

import pytest

# -- Minimal game JSON for upload tests --
UPLOAD_GAME = {
    "schema_version": "1.0",
    "name": "Integration Test Game",
    "nodes": [
        {
            "id": "coins",
            "type": "resource",
            "name": "Coins",
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
            "id": "miner_to_coins",
            "source": "miner",
            "target": "coins",
            "edge_type": "production_target",
        },
    ],
    "stacking_groups": {},
}


class TestPlaySessionFlow:
    """E2E: start -> advance -> purchase -> advance ->
    auto-optimize -> delete."""

    def test_play_session_flow(self, client):
        # 1. Start a session
        resp = client.post(
            "/api/v1/engine/start",
            json={"game_id": "minicap"},
        )
        assert resp.status_code == 200
        data = resp.json()
        session_id = data["session_id"]
        assert data["game_id"] == "minicap"
        assert data["elapsed_time"] == 0.0
        assert len(data["resources"]) > 0
        assert len(data["generators"]) > 0

        # 2. Advance time to accumulate resources
        resp = client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 30.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["elapsed_time"] == pytest.approx(
            30.0,
            abs=0.5,
        )
        first_resource = list(
            data["resources"].values(),
        )[0]
        assert first_resource["current_value"] > 0

        # 3. Purchase a generator
        gen_id = list(data["generators"].keys())[0]
        resp = client.post(
            f"/api/v1/engine/{session_id}/purchase",
            json={"node_id": gen_id, "count": 1},
        )
        assert resp.status_code == 200
        gen_data = resp.json()["generators"]
        assert gen_data[gen_id]["owned"] >= 1

        # 4. Advance more time
        resp = client.post(
            f"/api/v1/engine/{session_id}/advance",
            json={"seconds": 10.0},
        )
        assert resp.status_code == 200
        assert resp.json()["elapsed_time"] == (pytest.approx(40.0, abs=0.5))

        # 5. Run auto-optimize
        resp = client.post(
            f"/api/v1/engine/{session_id}/auto-optimize",
            json={
                "target_time": 60.0,
                "max_steps": 20,
            },
        )
        assert resp.status_code == 200
        opt_data = resp.json()
        assert "purchases" in opt_data
        assert "timeline" in opt_data
        assert opt_data["final_production"] >= 0

        # 6. Delete session
        resp = client.delete(
            f"/api/v1/engine/{session_id}",
        )
        assert resp.status_code == 204

        # Verify session is gone
        resp = client.get(
            f"/api/v1/engine/{session_id}/state",
        )
        assert resp.status_code == 404


class TestAnalysisThenReport:
    """E2E: run analysis -> generate HTML report."""

    def test_analysis_then_report(self, client):
        # 1. Run analysis
        resp = client.post(
            "/api/v1/analysis/run",
            json={
                "game_id": "minicap",
                "simulation_time": 60.0,
            },
        )
        assert resp.status_code == 200
        analysis = resp.json()
        assert analysis["game_name"] == "MiniCap"
        assert analysis["simulation_time"] == 60.0
        assert "dead_upgrades" in analysis
        assert "progression_walls" in analysis
        assert "dominant_strategy" in analysis

        # 2. Generate HTML report
        resp = client.post(
            "/api/v1/analysis/report",
            json={
                "game_id": "minicap",
                "simulation_time": 60.0,
            },
        )
        assert resp.status_code == 200
        html = resp.text
        assert "<!DOCTYPE html>" in html
        assert "MiniCap" in html


class TestGameUploadAndAnalyze:
    """E2E: upload game -> analyze it -> delete it."""

    def test_game_upload_and_analyze(self, client):
        # 1. Upload a new game
        resp = client.post(
            "/api/v1/games/",
            json=UPLOAD_GAME,
        )
        assert resp.status_code == 201
        create_data = resp.json()
        game_id = create_data["id"]
        assert create_data["name"] == ("Integration Test Game")

        # Verify it appears in the game list
        resp = client.get("/api/v1/games/")
        assert resp.status_code == 200
        game_ids = [g["id"] for g in resp.json()["games"]]
        assert game_id in game_ids

        # 2. Run analysis on the uploaded game
        resp = client.post(
            "/api/v1/analysis/run",
            json={
                "game_id": game_id,
                "simulation_time": 30.0,
            },
        )
        assert resp.status_code == 200
        analysis = resp.json()
        assert analysis["game_name"] == ("Integration Test Game")

        # 3. Delete the uploaded game
        resp = client.delete(
            f"/api/v1/games/{game_id}",
        )
        assert resp.status_code == 204

        # Verify it's gone
        resp = client.get(
            f"/api/v1/games/{game_id}",
        )
        assert resp.status_code == 404
