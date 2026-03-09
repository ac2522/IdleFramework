"""Tests for the analysis engine detectors.

Detectors identify balance issues in game definitions:
- Dead upgrades: upgrades that are never worth purchasing
- Progression walls: points where growth rate drops sharply
- Dominant strategies: one purchase path >>2x better than alternatives
- Sensitivity analysis: how parameter perturbations affect outcomes
"""
import json
import pytest
from pathlib import Path
from idleframework.model.game import GameDefinition
from idleframework.analysis.detectors import (
    detect_dead_upgrades,
    detect_progression_walls,
    detect_dominant_strategy,
    run_sensitivity_analysis,
    AnalysisReport,
    run_full_analysis,
)
import sys
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
        """Intentionally overpriced upgrade should be flagged as dead."""
        dead = detect_dead_upgrades(mediumcap_game, simulation_time=600.0)
        dead_ids = [d["upgrade_id"] for d in dead]
        assert "dead_upgrade" in dead_ids

    def test_dead_upgrade_detected_in_largecap(self, largecap_game):
        """LargeCap's 1e30-cost x1.001 upgrade should be flagged."""
        dead = detect_dead_upgrades(largecap_game, simulation_time=600.0)
        dead_ids = [d["upgrade_id"] for d in dead]
        assert "dead_upgrade" in dead_ids

    def test_normal_upgrades_not_flagged(self, minicap_game):
        """MiniCap's standard upgrades should not be dead."""
        dead = detect_dead_upgrades(minicap_game, simulation_time=600.0)
        dead_ids = [d["upgrade_id"] for d in dead]
        # x3_lemon at cost 1000 is definitely reachable and useful
        assert "x3_lemon" not in dead_ids

    def test_dead_upgrade_has_reason(self, mediumcap_game):
        """Dead upgrade entries should include a reason."""
        dead = detect_dead_upgrades(mediumcap_game, simulation_time=600.0)
        for d in dead:
            assert "reason" in d


class TestProgressionWallDetection:
    def test_progression_wall_in_largecap(self, largecap_game):
        """LargeCap's last generator (1.50 growth) should create a wall."""
        walls = detect_progression_walls(largecap_game, simulation_time=300.0)
        assert len(walls) > 0
        # Wall should mention the high-growth generator
        wall_gens = [w.get("generator_id") for w in walls]
        assert "gen_9" in wall_gens

    def test_no_wall_in_minicap(self, minicap_game):
        """MiniCap is well-balanced — no severe walls expected in short sim."""
        walls = detect_progression_walls(minicap_game, simulation_time=300.0)
        # Might find mild ones, but no severe walls
        severe = [w for w in walls if w.get("severity", "") == "severe"]
        assert len(severe) == 0


class TestDominantStrategyDetection:
    def test_dominant_strategy_detection(self):
        """One generator clearly dominant over another."""
        game = GameDefinition(
            schema_version="1.0",
            name="DominantTest",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {"id": "weak", "type": "generator", "name": "Weak",
                 "base_production": 1.0, "cost_base": 1000.0, "cost_growth_rate": 1.15,
                 "cycle_time": 1.0},
                {"id": "strong", "type": "generator", "name": "Strong",
                 "base_production": 100.0, "cost_base": 10.0, "cost_growth_rate": 1.07,
                 "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "weak", "target": "cash", "edge_type": "production_target"},
                {"id": "e2", "source": "strong", "target": "cash", "edge_type": "production_target"},
            ],
            stacking_groups={},
        )
        result = detect_dominant_strategy(game, simulation_time=300.0)
        assert result["dominant_gen"] == "strong"
        assert result["ratio"] > 2.0

    def test_balanced_generators_no_dominance(self):
        """Two generators with similar efficiency should not flag dominance."""
        game = GameDefinition(
            schema_version="1.0",
            name="BalancedTest",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {"id": "gen_a", "type": "generator", "name": "Gen A",
                 "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
                 "cycle_time": 1.0},
                {"id": "gen_b", "type": "generator", "name": "Gen B",
                 "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
                 "cycle_time": 1.0},
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
        """Perturbing cost_base should change final production."""
        results = run_sensitivity_analysis(
            minicap_game,
            parameter="cost_base",
            perturbation_pcts=[0.5, 1.0, 2.0],
            simulation_time=300.0,
        )
        assert len(results) == 3
        # Higher cost → lower production
        productions = [r["final_production"] for r in results]
        assert productions[0] > productions[2]  # 50% cost > 200% cost

    def test_sensitivity_result_has_fields(self, minicap_game):
        """Each sensitivity result should have perturbation and outcome."""
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
        """Full analysis should return an AnalysisReport."""
        report = run_full_analysis(minicap_game, simulation_time=300.0)
        assert isinstance(report, AnalysisReport)
        assert report.game_name == "MiniCap"
        assert report.dead_upgrades is not None
        assert report.progression_walls is not None

    def test_full_analysis_on_mediumcap(self, mediumcap_game):
        """Full analysis on MediumCap should detect the dead upgrade."""
        report = run_full_analysis(mediumcap_game, simulation_time=600.0)
        dead_ids = [d["upgrade_id"] for d in report.dead_upgrades]
        assert "dead_upgrade" in dead_ids

    def test_full_analysis_on_largecap(self, largecap_game):
        """Full analysis on LargeCap should complete and find issues."""
        report = run_full_analysis(largecap_game, simulation_time=300.0)
        assert report.game_name == "LargeCap"
        assert len(report.dead_upgrades) > 0 or len(report.progression_walls) > 0
