"""Piecewise analytical engine tests.

Tests the core simulation engine that advances game state through
analytical segments, purchasing items at optimal times.
"""
import json
import pytest
from pathlib import Path
from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.game import GameDefinition


def _make_simple_game():
    """One resource, one generator, one upgrade."""
    return GameDefinition(
        schema_version="1.0",
        name="Simple",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "miner", "type": "generator", "name": "Miner",
             "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
        ],
        edges=[
            {"id": "e1", "source": "miner", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={},
    )


def _make_two_gen_game():
    """Two generators producing to same resource."""
    return GameDefinition(
        schema_version="1.0",
        name="TwoGen",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "miner", "type": "generator", "name": "Miner",
             "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
            {"id": "factory", "type": "generator", "name": "Factory",
             "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
             "cycle_time": 2.0},
        ],
        edges=[
            {"id": "e1", "source": "miner", "target": "cash", "edge_type": "production_target"},
            {"id": "e2", "source": "factory", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={},
    )


class TestSingleSegment:
    def test_constant_production(self):
        """One generator, no purchases → linear growth."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        engine.advance_to(10.0)
        # 5 miners * 1.0 production * 10 seconds = 50
        assert engine.get_balance("cash") == pytest.approx(50.0, rel=1e-3)

    def test_zero_generators(self):
        """No generators → no production."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.advance_to(100.0)
        assert engine.get_balance("cash") == pytest.approx(0.0)


class TestPurchases:
    def test_purchase_creates_new_segment(self):
        """Buying a generator increases production rate for remaining time."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 10.0)  # Enough for 1 miner
        engine.purchase("miner", 1)
        assert engine.get_owned("miner") == 1
        # Balance should decrease by cost
        assert engine.get_balance("cash") < 10.0

    def test_purchase_insufficient_funds(self):
        """Can't buy what you can't afford."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 1.0)  # Not enough
        with pytest.raises(ValueError, match="[Aa]fford"):
            engine.purchase("miner", 1)

    def test_sequential_purchases(self):
        """Multiple purchases at different times."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 100.0)
        engine.purchase("miner", 1)
        engine.advance_to(10.0)
        # Should have 1 miner producing for 10s plus remaining balance
        balance = engine.get_balance("cash")
        assert balance > 0


class TestEventScheduling:
    def test_find_next_purchase_time(self):
        """Engine should compute when next purchase becomes affordable."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 1)  # 1 miner at 1.0/sec
        # Cost of next miner: 10 * 1.15^1 = 11.5
        # Time to afford: 11.5 / 1.0 = 11.5 seconds
        event = engine.find_next_purchase_event("miner")
        assert event is not None
        assert event.time == pytest.approx(11.5, rel=1e-3)

    def test_no_event_when_no_production(self):
        """No production → can never afford → no event."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        event = engine.find_next_purchase_event("miner")
        assert event is None


class TestAutoAdvance:
    def test_auto_advance_buys_generators(self):
        """auto_advance should buy generators as they become affordable."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 10.0)  # Enough for first miner
        engine.purchase("miner", 1)
        # Auto-advance to accumulate and buy more
        engine.auto_advance(target_time=100.0)
        assert engine.get_owned("miner") > 1

    def test_chattering_protection(self):
        """Engine should not purchase more than MAX_PURCHASES_PER_STEP."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 1e10)  # Lots of money
        engine.set_owned("miner", 1)
        # Should not infinite-loop buying
        engine.auto_advance(target_time=1.0, max_purchases_per_step=10)
        # Just verify it completes without hanging


class TestConvergenceVsRK4:
    def test_constant_rate_matches_rk4(self):
        """Piecewise engine with constant rate should match RK4 exactly."""
        game = _make_simple_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)

        # Piecewise engine
        engine.advance_to(10.0)
        piecewise_result = engine.get_balance("cash")

        # RK4 inline
        state = {"cash": 0.0}
        rates = {"cash": 5.0}
        dt = 0.01
        for _ in range(1000):
            k1 = {k: rates.get(k, 0.0) for k in state}
            s2 = {k: state[k] + k1[k] * dt / 2 for k in state}
            k2 = {k: rates.get(k, 0.0) for k in s2}
            s3 = {k: state[k] + k2[k] * dt / 2 for k in state}
            k3 = {k: rates.get(k, 0.0) for k in s3}
            s4 = {k: state[k] + k3[k] * dt for k in state}
            k4 = {k: rates.get(k, 0.0) for k in s4}
            state = {
                k: state[k] + (k1[k] + 2*k2[k] + 2*k3[k] + k4[k]) * dt / 6
                for k in state
            }
        rk4_result = state["cash"]

        assert piecewise_result == pytest.approx(rk4_result, rel=1e-3)


class TestMiniCapIntegration:
    def test_minicap_engine_runs(self):
        """PiecewiseEngine should handle the MiniCap fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
        with open(fixture_path) as f:
            data = json.load(f)
        game = GameDefinition.model_validate(data)
        engine = PiecewiseEngine(game)
        engine.set_owned("lemonade", 1)
        engine.advance_to(10.0)
        assert engine.get_balance("cash") > 0
