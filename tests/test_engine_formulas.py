"""Tests for formula DSL integration and graph validation in the engine.

Tests that:
1. Engine validates graph on init (bad edges raise)
2. PrestigeLayer formula_expr can be evaluated with engine state
3. Register node formula_expr can be evaluated
"""
import pytest
from idleframework.model.game import GameDefinition
from idleframework.engine.segments import PiecewiseEngine
from idleframework.dsl.compiler import compile_formula, evaluate_formula


class TestGraphValidationOnInit:
    def test_invalid_edge_raises_on_init(self):
        """Engine should reject games with edges referencing nonexistent nodes."""
        game = GameDefinition(
            schema_version="1.0",
            name="BadEdge",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            ],
            edges=[
                {"id": "e1", "source": "ghost", "target": "cash",
                 "edge_type": "production_target"},
            ],
            stacking_groups={},
        )
        with pytest.raises(ValueError, match="[Vv]alidat"):
            PiecewiseEngine(game, validate=True)

    def test_dependency_cycle_raises_on_init(self):
        """Engine should reject games with unlock_dependency cycles."""
        game = GameDefinition(
            schema_version="1.0",
            name="CyclicDeps",
            nodes=[
                {"id": "a", "type": "unlock_gate", "name": "A"},
                {"id": "b", "type": "unlock_gate", "name": "B"},
            ],
            edges=[
                {"id": "e1", "source": "a", "target": "b",
                 "edge_type": "unlock_dependency"},
                {"id": "e2", "source": "b", "target": "a",
                 "edge_type": "unlock_dependency"},
            ],
            stacking_groups={},
        )
        with pytest.raises(ValueError, match="[Cc]ycle"):
            PiecewiseEngine(game, validate=True)

    def test_valid_graph_no_error(self):
        """Valid game should init without error."""
        game = GameDefinition(
            schema_version="1.0",
            name="Good",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0,
                 "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "cash",
                 "edge_type": "production_target"},
            ],
            stacking_groups={},
        )
        engine = PiecewiseEngine(game, validate=True)
        assert engine is not None


class TestPrestigeFormulaEvaluation:
    def test_evaluate_prestige_formula(self):
        """Engine should be able to evaluate prestige layer formulas."""
        game = GameDefinition(
            schema_version="1.0",
            name="PrestigeTest",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0,
                 "cost_growth_rate": 1.15, "cycle_time": 1.0},
                {"id": "prestige", "type": "prestige_layer",
                 "name": "Angels",
                 "formula_expr": "150 * sqrt(lifetime_earnings / 1e15)",
                 "layer_index": 0,
                 "reset_scope": ["cash", "miner"],
                 "bonus_type": "multiplicative"},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "cash",
                 "edge_type": "production_target"},
            ],
            stacking_groups={},
        )
        engine = PiecewiseEngine(game)
        # Simulate earning 1e18
        engine.set_balance("cash", 1e18)

        angels = engine.evaluate_prestige("prestige", lifetime_earnings=1e18)
        # 150 * sqrt(1e18 / 1e15) = 150 * sqrt(1000) ≈ 4743.4
        assert angels == pytest.approx(4743.416, rel=1e-3)

    def test_prestige_formula_zero_earnings(self):
        """Zero earnings should give zero or near-zero angels."""
        game = GameDefinition(
            schema_version="1.0",
            name="PrestigeZero",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {"id": "prestige", "type": "prestige_layer",
                 "name": "Angels",
                 "formula_expr": "150 * sqrt(lifetime_earnings / 1e15)",
                 "layer_index": 0,
                 "reset_scope": ["cash"],
                 "bonus_type": "multiplicative"},
            ],
            edges=[],
            stacking_groups={},
        )
        engine = PiecewiseEngine(game)
        angels = engine.evaluate_prestige("prestige", lifetime_earnings=0)
        assert angels == pytest.approx(0.0)


class TestRegisterFormulaEvaluation:
    def test_evaluate_register(self):
        """Register node formulas should be evaluable with current state."""
        game = GameDefinition(
            schema_version="1.0",
            name="RegisterTest",
            nodes=[
                {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
                {"id": "calc", "type": "register", "name": "Bonus Calc",
                 "formula_expr": "x * 0.02 + 1"},
            ],
            edges=[],
            stacking_groups={},
        )
        engine = PiecewiseEngine(game)
        result = engine.evaluate_register("calc", {"x": 100})
        assert result == pytest.approx(3.0)
