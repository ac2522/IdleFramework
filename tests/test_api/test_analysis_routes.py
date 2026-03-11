"""Tests for analysis endpoints."""
import pytest
from fastapi.testclient import TestClient
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestRunAnalysis:
    def test_run_greedy_analysis(self, client):
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "minicap",
            "simulation_time": 60.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_name"] == "MiniCap"
        assert "dead_upgrades" in data
        assert "progression_walls" in data
        assert "optimizer_result" in data

    def test_run_analysis_nonexistent_game(self, client):
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "nonexistent",
        })
        assert resp.status_code == 404

    def test_run_with_custom_time(self, client):
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "minicap",
            "simulation_time": 30.0,
        })
        assert resp.status_code == 200
        assert resp.json()["simulation_time"] == 30.0


class TestCompare:
    def test_compare_strategies(self, client):
        resp = client.post("/api/v1/analysis/compare", json={
            "game_id": "minicap",
            "strategies": ["free", "paid"],
            "simulation_time": 60.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "baseline" in data
        assert "variants" in data


class TestReport:
    def test_generate_html_report(self, client):
        resp = client.post("/api/v1/analysis/report", json={
            "game_id": "minicap",
            "simulation_time": 60.0,
        })
        assert resp.status_code == 200
        assert "<!DOCTYPE html>" in resp.text
        assert "MiniCap" in resp.text
