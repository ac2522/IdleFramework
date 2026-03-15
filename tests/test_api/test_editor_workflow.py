"""Round-trip tests for the editor workflow: create, load, analyze."""

MINIMAL_GAME = {
    "schema_version": "1.0",
    "name": "Editor Test Game",
    "stacking_groups": {"default": "multiplicative"},
    "nodes": [
        {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
        {
            "id": "gen1",
            "type": "generator",
            "name": "Worker",
            "base_production": 1.0,
            "cost_base": 10.0,
            "cost_growth_rate": 1.07,
            "cycle_time": 1.0,
        },
        {
            "id": "upg1",
            "type": "upgrade",
            "name": "Boost",
            "upgrade_type": "multiplicative",
            "magnitude": 2.0,
            "cost": 100.0,
            "target": "gen1",
            "stacking_group": "default",
        },
    ],
    "edges": [
        {"id": "e1", "source": "gen1", "target": "cash", "edge_type": "resource_flow"},
    ],
}

ALL_NODE_TYPES_GAME = {
    "schema_version": "1.0",
    "name": "All Node Types Game",
    "stacking_groups": {"default": "multiplicative"},
    "nodes": [
        {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
        {
            "id": "miner",
            "type": "generator",
            "name": "Miner",
            "base_production": 1.0,
            "cost_base": 10.0,
            "cost_growth_rate": 1.15,
            "cycle_time": 1.0,
        },
        {
            "id": "pickaxe",
            "type": "upgrade",
            "name": "Pickaxe",
            "upgrade_type": "multiplicative",
            "magnitude": 2.0,
            "cost": 50.0,
            "target": "miner",
            "stacking_group": "default",
        },
        {
            "id": "ach1",
            "type": "achievement",
            "name": "First Gold",
            "condition_type": "single_threshold",
            "targets": [{"node_id": "gold", "property": "current_value", "threshold": 100}],
        },
    ],
    "edges": [
        {"id": "e1", "source": "miner", "target": "gold", "edge_type": "resource_flow"},
    ],
}


class TestCreateAndLoad:
    def test_create_and_load(self, client):
        """Create a game via POST, then load it via GET and verify contents."""
        # Create
        resp = client.post("/api/v1/games/", json=MINIMAL_GAME)
        assert resp.status_code == 201
        create_data = resp.json()
        game_id = create_data["id"]
        assert create_data["name"] == "Editor Test Game"

        # Load
        resp = client.get(f"/api/v1/games/{game_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Editor Test Game"
        assert len(data["nodes"]) == 3

        # Cleanup
        client.delete(f"/api/v1/games/{game_id}")


class TestCreateAndAnalyze:
    def test_create_and_analyze(self, client):
        """Create a game, run analysis, verify response structure."""
        # Create
        resp = client.post("/api/v1/games/", json=MINIMAL_GAME)
        assert resp.status_code == 201
        game_id = resp.json()["id"]

        # Analyze
        resp = client.post(
            "/api/v1/analysis/run",
            json={
                "game_id": game_id,
                "simulation_time": 60.0,
            },
        )
        assert resp.status_code == 200
        analysis = resp.json()
        assert "dead_upgrades" in analysis
        assert "progression_walls" in analysis

        # Cleanup
        client.delete(f"/api/v1/games/{game_id}")


class TestCreateInvalidGameFails:
    def test_create_invalid_game_fails(self, client):
        """POST invalid JSON should return 422 or 400."""
        resp = client.post("/api/v1/games/", json={"name": "bad"})
        assert resp.status_code in (400, 422)


class TestCreateGameAllNodeTypes:
    def test_create_game_all_node_types(self, client):
        """Create a game with resource, generator, upgrade, achievement nodes and edges."""
        # Create
        resp = client.post("/api/v1/games/", json=ALL_NODE_TYPES_GAME)
        assert resp.status_code == 201
        game_id = resp.json()["id"]

        # Load and verify
        resp = client.get(f"/api/v1/games/{game_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 4

        node_types = {n["type"] for n in data["nodes"]}
        assert node_types == {"resource", "generator", "upgrade", "achievement"}

        assert len(data["edges"]) == 1

        # Cleanup
        client.delete(f"/api/v1/games/{game_id}")
