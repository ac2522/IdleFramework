"""Tests for analysis endpoints."""


class TestRunAnalysis:
    def test_run_greedy_analysis(self, client):
        resp = client.post(
            "/api/v1/analysis/run",
            json={
                "game_id": "minicap",
                "simulation_time": 60.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_name"] == "MiniCap"
        assert "dead_upgrades" in data
        assert "progression_walls" in data
        assert "optimizer_result" in data

    def test_run_analysis_nonexistent_game(
        self, client,
    ):
        resp = client.post(
            "/api/v1/analysis/run",
            json={"game_id": "nonexistent"},
        )
        assert resp.status_code == 404

    def test_run_with_custom_time(self, client):
        resp = client.post(
            "/api/v1/analysis/run",
            json={
                "game_id": "minicap",
                "simulation_time": 30.0,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["simulation_time"] == 30.0


class TestRunAnalysisValidation:
    def test_simulation_time_zero_422(self, client):
        resp = client.post(
            "/api/v1/analysis/run",
            json={
                "game_id": "minicap",
                "simulation_time": 0,
            },
        )
        assert resp.status_code == 422

    def test_simulation_time_negative_422(self, client):
        resp = client.post(
            "/api/v1/analysis/run",
            json={
                "game_id": "minicap",
                "simulation_time": -1,
            },
        )
        assert resp.status_code == 422

    def test_simulation_time_over_max_422(self, client):
        resp = client.post(
            "/api/v1/analysis/run",
            json={
                "game_id": "minicap",
                "simulation_time": 86401,
            },
        )
        assert resp.status_code == 422


class TestCompare:
    def test_compare_strategies(self, client):
        resp = client.post(
            "/api/v1/analysis/compare",
            json={
                "game_id": "minicap",
                "strategies": ["free", "paid"],
                "simulation_time": 60.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "baseline" in data
        assert "variants" in data

    def test_compare_single_strategy(self, client):
        resp = client.post(
            "/api/v1/analysis/compare",
            json={
                "game_id": "minicap",
                "strategies": ["free"],
                "simulation_time": 60.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["variants"]) == 1

    def test_compare_nonexistent_game_404(self, client):
        resp = client.post(
            "/api/v1/analysis/compare",
            json={
                "game_id": "nonexistent",
                "strategies": ["free"],
            },
        )
        assert resp.status_code == 404


class TestReport:
    def test_generate_html_report(self, client):
        resp = client.post(
            "/api/v1/analysis/report",
            json={
                "game_id": "minicap",
                "simulation_time": 60.0,
            },
        )
        assert resp.status_code == 200
        assert "<!DOCTYPE html>" in resp.text
        assert "MiniCap" in resp.text

    def test_report_nonexistent_game_404(self, client):
        resp = client.post(
            "/api/v1/analysis/report",
            json={"game_id": "nonexistent"},
        )
        assert resp.status_code == 404
