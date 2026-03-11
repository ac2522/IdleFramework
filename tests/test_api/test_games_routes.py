"""Tests for game definition CRUD endpoints."""
import pytest
from fastapi.testclient import TestClient
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestListGames:
    def test_list_returns_bundled_games(self, client):
        resp = client.get("/api/v1/games/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["games"], list)
        ids = [g["id"] for g in data["games"]]
        assert "minicap" in ids

    def test_list_includes_name_and_node_count(self, client):
        resp = client.get("/api/v1/games/")
        game = next(g for g in resp.json()["games"] if g["id"] == "minicap")
        assert game["name"] == "MiniCap"
        assert game["node_count"] > 0


class TestGetGame:
    def test_get_existing_game(self, client):
        resp = client.get("/api/v1/games/minicap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "MiniCap"
        assert "nodes" in data

    def test_get_nonexistent_game_404(self, client):
        resp = client.get("/api/v1/games/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "game_not_found"


class TestCreateGame:
    def test_create_game_from_json(self, client):
        game_json = {
            "schema_version": "1.0",
            "name": "Test Game",
            "nodes": [
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
            ],
            "edges": [],
            "stacking_groups": {},
        }
        resp = client.post("/api/v1/games/", json=game_json)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "test-game"
        assert data["name"] == "Test Game"

    def test_create_invalid_game_422(self, client):
        resp = client.post("/api/v1/games/", json={"bad": "data"})
        assert resp.status_code == 422


class TestDeleteGame:
    def test_delete_user_game(self, client):
        # Create first
        game_json = {
            "schema_version": "1.0",
            "name": "Deletable",
            "nodes": [],
            "edges": [],
            "stacking_groups": {},
        }
        client.post("/api/v1/games/", json=game_json)
        resp = client.delete("/api/v1/games/deletable")
        assert resp.status_code == 204

    def test_delete_bundled_game_403(self, client):
        resp = client.delete("/api/v1/games/minicap")
        assert resp.status_code == 403


class TestExportGame:
    def test_export_yaml(self, client):
        resp = client.get("/api/v1/games/minicap/export?format=yaml")
        assert resp.status_code == 200
        assert "MiniCap" in resp.text

    def test_export_xml(self, client):
        resp = client.get("/api/v1/games/minicap/export?format=xml")
        assert resp.status_code == 200
        assert "<GameDefinition" in resp.text

    def test_export_schema(self, client):
        resp = client.get("/api/v1/games/minicap/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "properties" in data
