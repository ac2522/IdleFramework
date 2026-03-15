"""Tests for the analysis engine detectors."""

import json
import sys
from pathlib import Path

import pytest

from idleframework.analysis.detectors import (
    AnalysisReport,
    detect_dead_upgrades,
    detect_dominant_strategy,
    detect_progression_walls,
    run_full_analysis,
    run_sensitivity_analysis,
)
from idleframework.model.game import GameDefinition

sys.path.insert(0, str(Path(__file__).parent))
from fixtures.largecap import make_largecap


@pytest.fixture
def minicap_game() -> GameDefinition:
    fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return GameDefinition.model_validate(data)


@pytest.fixture
def mediumcap_game() -> GameDefinition:
    fixture_path = Path(__file__).parent / "fixtures" / "mediumcap.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return GameDefinition.model_validate(data)


@pytest.fixture
def largecap_game() -> GameDefinition:
    return make_largecap(num_generators=10, upgrades_per_gen=10)


class TestDeadUpgradeDetection:
    def test_dead_upgrade_detected_in_mediumcap(self, mediumcap_game):
        dead = detect_dead_upgrades(mediumcap_game, simulation_time=600.0)
        dead_ids = [d["upgrade_id"] for d in dead]
        assert "dead_upgrade" in dead_ids

    def test_dead_upgrade_detected_in_largecap(self, largecap_game):
        dead = detect_dead_upgrades(largecap_game, simulation_time=600.0)
        dead_ids = [d["upgrade_id"] for d in dead]
        assert "dead_upgrade" in dead_ids

    def test_normal_upgrades_not_flagged(self, minicap_game):
        dead = detect_dead_upgrades(minicap_game, simulation_time=600.0)
        dead_ids = [d["upgrade_id"] for d in dead]
        assert "x3_lemon" not in dead_ids

    def test_dead_upgrade_has_reason(self, mediumcap_game):
        dead = detect_dead_upgrades(mediumcap_game, simulation_time=600.0)
        for d in dead:
            assert "reason" in d


class TestProgressionWallDetection:
    def test_progression_wall_in_largecap(self, largecap_game):
        walls = detect_progression_walls(largecap_game, simulation_time=300.0)
        assert len(walls) > 0
        wall_gens = [w.get("generator_id") for w in walls]
        assert "gen_9" in wall_gens

    def test_no_wall_in_minicap(self, minicap_game):
        walls = detect_progression_walls(minicap_game, simulation_time=300.0)
        severe = [w for w in walls if w.get("severity", "") == "severe"]
        assert len(severe) == 0


class TestDominantStrategyDetection:
    def test_dominant_strategy_detection(self):
        game = GameDefinition(
            schema_version="1.0",
            name="DominantTest",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {
                    "id": "weak",
                    "type": "generator",
                    "name": "Weak",
                    "base_production": 1.0,
                    "cost_base": 1000.0,
                    "cost_growth_rate": 1.15,
                    "cycle_time": 1.0,
                },
                {
                    "id": "strong",
                    "type": "generator",
                    "name": "Strong",
                    "base_production": 100.0,
                    "cost_base": 10.0,
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "weak", "target": "cash", "edge_type": "production_target"},
                {
                    "id": "e2",
                    "source": "strong",
                    "target": "cash",
                    "edge_type": "production_target",
                },
            ],
            stacking_groups={},
        )
        result = detect_dominant_strategy(game, simulation_time=300.0)
        assert result["dominant_gen"] == "strong"
        assert result["ratio"] > 2.0

    def test_balanced_generators_no_dominance(self):
        game = GameDefinition(
            schema_version="1.0",
            name="BalancedTest",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {
                    "id": "gen_a",
                    "type": "generator",
                    "name": "Gen A",
                    "base_production": 10.0,
                    "cost_base": 100.0,
                    "cost_growth_rate": 1.15,
                    "cycle_time": 1.0,
                },
                {
                    "id": "gen_b",
                    "type": "generator",
                    "name": "Gen B",
                    "base_production": 10.0,
                    "cost_base": 100.0,
                    "cost_growth_rate": 1.15,
                    "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "gen_a", "target": "cash", "edge_type": "production_target"},
                {"id": "e2", "source": "gen_b", "target": "cash", "edge_type": "production_target"},
            ],
            stacking_groups={},
        )
        result = detect_dominant_strategy(game, simulation_time=300.0)
        assert result["dominant_gen"] is None or result["ratio"] < 2.0


class TestSensitivityAnalysis:
    def test_sensitivity_perturbs_parameters(self, minicap_game):
        results = run_sensitivity_analysis(
            minicap_game,
            parameter="cost_base",
            perturbation_pcts=[0.5, 1.0, 2.0],
            simulation_time=300.0,
        )
        assert len(results) == 3
        productions = [r["final_production"] for r in results]
        assert productions[0] > productions[2]

    def test_sensitivity_result_has_fields(self, minicap_game):
        results = run_sensitivity_analysis(
            minicap_game,
            parameter="cost_base",
            perturbation_pcts=[1.0],
            simulation_time=300.0,
        )
        assert len(results) == 1
        r = results[0]
        assert "perturbation_pct" in r
        assert "final_production" in r
        assert "final_balance" in r


class TestFullAnalysis:
    def test_full_analysis_on_minicap(self, minicap_game):
        report = run_full_analysis(minicap_game, simulation_time=300.0)
        assert isinstance(report, AnalysisReport)
        assert report.game_name == "MiniCap"
        assert report.dead_upgrades is not None
        assert report.progression_walls is not None

    def test_full_analysis_on_mediumcap(self, mediumcap_game):
        report = run_full_analysis(mediumcap_game, simulation_time=600.0)
        dead_ids = [d["upgrade_id"] for d in report.dead_upgrades]
        assert "dead_upgrade" in dead_ids

    def test_full_analysis_on_largecap(self, largecap_game):
        report = run_full_analysis(largecap_game, simulation_time=300.0)
        assert report.game_name == "LargeCap"
        assert len(report.dead_upgrades) > 0 or len(report.progression_walls) > 0
