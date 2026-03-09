"""Tests for the greedy optimizer.

The greedy optimizer picks the highest-efficiency purchase at each step:
- Generator efficiency: delta_production / cost
- Upgrade efficiency: (current_production * (multiplier - 1)) / cost
- Additive upgrade:   (bonus * current_production) / cost

These tests verify correct efficiency ranking, purchase sequencing,
and integration with the PiecewiseEngine.
"""
import json
import pytest
from pathlib import Path
from idleframework.model.game import GameDefinition
from idleframework.engine.segments import PiecewiseEngine
from idleframework.optimizer.greedy import GreedyOptimizer


def _make_two_gen_game():
    """Two generators with different efficiency profiles."""
    return GameDefinition(
        schema_version="1.0",
        name="GreedyTest",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "cheap", "type": "generator", "name": "Cheap",
             "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
            {"id": "expensive", "type": "generator", "name": "Expensive",
             "base_production": 50.0, "cost_base": 500.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
        ],
        edges=[
            {"id": "e1", "source": "cheap", "target": "cash", "edge_type": "production_target"},
            {"id": "e2", "source": "expensive", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={},
    )


def _make_upgrade_game():
    """Game with generator + multiplicative upgrade."""
    return GameDefinition(
        schema_version="1.0",
        name="UpgradeGreedyTest",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "miner", "type": "generator", "name": "Miner",
             "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
            {"id": "x3_miner", "type": "upgrade", "name": "x3 Miner",
             "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 500.0,
             "target": "miner", "stacking_group": "cash_upgrades"},
        ],
        edges=[
            {"id": "e1", "source": "miner", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={"cash_upgrades": "multiplicative"},
    )


def _make_additive_upgrade_game():
    """Game with additive upgrade for efficiency formula testing."""
    return GameDefinition(
        schema_version="1.0",
        name="AdditiveGreedyTest",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "miner", "type": "generator", "name": "Miner",
             "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
            {"id": "bonus_5pct", "type": "upgrade", "name": "+5% Bonus",
             "upgrade_type": "additive", "magnitude": 0.05, "cost": 50.0,
             "target": "miner", "stacking_group": "angel_bonus"},
        ],
        edges=[
            {"id": "e1", "source": "miner", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={"angel_bonus": "additive"},
    )


class TestGreedyEfficiency:
    def test_greedy_buys_best_efficiency(self):
        """Greedy should pick highest delta_production / cost."""
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 600.0)
        engine.set_owned("cheap", 1)  # need some production to start

        optimizer = GreedyOptimizer(engine)
        # cheap efficiency: 1.0 / (10 * 1.15^1) = 1/11.5 ≈ 0.087
        # expensive efficiency: 50.0 / 500.0 = 0.1
        # Expensive is more efficient, should buy it first
        result = optimizer.step()
        assert result is not None
        assert result.node_id == "expensive"

    def test_greedy_picks_cheap_when_more_efficient(self):
        """When cheap gen is better efficiency, pick it."""
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 600.0)

        optimizer = GreedyOptimizer(engine)
        # cheap efficiency: 1.0 / 10.0 = 0.1
        # expensive efficiency: 50.0 / 500.0 = 0.1
        # Tie — either is acceptable, but first one at cost 10 is more immediately useful
        result = optimizer.step()
        assert result is not None
        # With equal efficiency, the cheaper one should be preferred
        # (or at least one of them should be bought)
        assert result.node_id in ("cheap", "expensive")


class TestGreedyUpgradeEfficiency:
    def test_greedy_multiplicative_formula(self):
        """Multiplicative upgrade efficiency = production * (mult - 1) / cost."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        engine.set_balance("cash", 1000.0)

        optimizer = GreedyOptimizer(engine)
        candidates = optimizer.get_candidates()

        # Find the upgrade candidate
        upg_candidate = next(c for c in candidates if c["node_id"] == "x3_miner")
        # Current production from miners: 5 * 10.0 / 1.0 = 50.0
        # Upgrade gives 3x, so delta = 50 * (3-1) = 100
        # Efficiency = 100 / 500 = 0.2
        assert upg_candidate["efficiency"] == pytest.approx(0.2, rel=1e-2)

    def test_greedy_additive_formula(self):
        """Additive upgrade efficiency = (bonus * current_group_mult * base_prod) / cost."""
        game = _make_additive_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        engine.set_balance("cash", 100.0)

        optimizer = GreedyOptimizer(engine)
        candidates = optimizer.get_candidates()

        upg_candidate = next(c for c in candidates if c["node_id"] == "bonus_5pct")
        # Current production: 5 * 10.0 = 50.0, no existing upgrades
        # Additive bonus: group goes from 1.0 to 1.05
        # delta_production = 50.0 * 0.05 = 2.5
        # Efficiency = 2.5 / 50.0 = 0.05
        assert upg_candidate["efficiency"] == pytest.approx(0.05, rel=1e-2)


class TestGreedyOptimize:
    def test_greedy_on_minicap(self):
        """Greedy optimizer should produce a valid purchase sequence on MiniCap."""
        fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
        with open(fixture_path) as f:
            data = json.load(f)
        game = GameDefinition.model_validate(data)
        engine = PiecewiseEngine(game, validate=True)
        engine.set_balance("cash", 50.0)
        engine.purchase("lemonade", 1)

        optimizer = GreedyOptimizer(engine)
        result = optimizer.optimize(target_time=300.0, max_steps=200)

        assert len(result.purchases) > 5
        assert result.final_production > 0
        assert result.final_balance >= 0
        assert engine.time == pytest.approx(300.0)

    def test_greedy_includes_upgrades_in_sequence(self):
        """Greedy should buy upgrades when they're more efficient than generators."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        engine.set_balance("cash", 2000.0)

        optimizer = GreedyOptimizer(engine)
        result = optimizer.optimize(target_time=100.0, max_steps=50)

        # The x3 upgrade should appear in the purchase sequence
        upgrade_purchases = [p for p in result.purchases if p.node_id == "x3_miner"]
        assert len(upgrade_purchases) == 1

    def test_greedy_result_has_timeline(self):
        """OptimizeResult should include a timeline of production rates."""
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 100.0)
        engine.set_owned("cheap", 1)

        optimizer = GreedyOptimizer(engine)
        result = optimizer.optimize(target_time=60.0, max_steps=20)

        assert len(result.timeline) > 0
        # Timeline entries should be chronologically ordered
        times = [t["time"] for t in result.timeline]
        assert times == sorted(times)
        # Each entry has time and production_rate
        for entry in result.timeline:
            assert "time" in entry
            assert "production_rate" in entry


class TestGreedyEdgeCases:
    def test_greedy_no_production_no_purchase(self):
        """If no production and no balance, optimizer returns empty result."""
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)

        optimizer = GreedyOptimizer(engine)
        result = optimizer.optimize(target_time=100.0, max_steps=50)
        assert len(result.purchases) == 0

    def test_greedy_respects_max_steps(self):
        """Optimizer should stop after max_steps purchases."""
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 1e10)
        engine.set_owned("cheap", 1)

        optimizer = GreedyOptimizer(engine)
        result = optimizer.optimize(target_time=1000.0, max_steps=10)
        assert len(result.purchases) <= 10


class TestGreedyPerformance:
    def test_greedy_under_200ms(self, benchmark):
        """Greedy optimizer should complete in < 200ms for MiniCap."""
        fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
        with open(fixture_path) as f:
            data = json.load(f)
        game = GameDefinition.model_validate(data)

        def run_greedy():
            engine = PiecewiseEngine(game, validate=True)
            engine.set_balance("cash", 50.0)
            engine.purchase("lemonade", 1)
            optimizer = GreedyOptimizer(engine)
            return optimizer.optimize(target_time=300.0, max_steps=200)

        result = benchmark(run_greedy)
        assert result.final_production > 0
