"""Tests for the beam search optimizer."""
import json
from pathlib import Path

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.game import GameDefinition
from idleframework.optimizer.beam import BeamSearchOptimizer
from idleframework.optimizer.greedy import GreedyOptimizer, OptimizeResult


def _make_two_gen_game():
    return GameDefinition(
        schema_version="1.0",
        name="BeamTest",
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


def _make_multiplicative_trap_game():
    return GameDefinition(
        schema_version="1.0",
        name="MultTrap",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "worker", "type": "generator", "name": "Worker",
             "base_production": 1.0, "cost_base": 5.0, "cost_growth_rate": 1.05,
             "cycle_time": 1.0},
            {"id": "x10_all", "type": "upgrade", "name": "x10 All",
             "upgrade_type": "multiplicative", "magnitude": 10.0, "cost": 500.0,
             "target": "_all", "stacking_group": "mult"},
        ],
        edges=[
            {"id": "e1", "source": "worker", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={"mult": "multiplicative"},
    )


class TestBeamExploresAlternatives:
    def test_beam_explores_alternatives(self):
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 600.0)
        engine.set_owned("cheap", 1)

        optimizer = BeamSearchOptimizer(engine, beam_width=3)
        result = optimizer.optimize(target_time=60.0, max_steps=10)

        assert isinstance(result, OptimizeResult)
        assert len(result.purchases) > 0
        assert len(result.purchases) >= 2


class TestBeamDeterministic:
    def test_beam_deterministic(self):
        game = _make_two_gen_game()

        results = []
        for _ in range(3):
            engine = PiecewiseEngine(game)
            engine.set_balance("cash", 200.0)
            engine.set_owned("cheap", 1)
            optimizer = BeamSearchOptimizer(engine, beam_width=5)
            results.append(optimizer.optimize(target_time=60.0, max_steps=20))

        for r in results[1:]:
            assert len(r.purchases) == len(results[0].purchases)
            for p1, p2 in zip(results[0].purchases, r.purchases, strict=True):
                assert p1.node_id == p2.node_id
                assert p1.cost == pytest.approx(p2.cost, rel=1e-9)
            assert r.final_production == pytest.approx(results[0].final_production, rel=1e-9)


class TestBeamBeatsGreedyOnMultiplicative:
    def test_beam_beats_greedy_on_multiplicative(self):
        game = _make_multiplicative_trap_game()

        engine_greedy = PiecewiseEngine(game)
        engine_greedy.set_owned("worker", 10)
        engine_greedy.set_balance("cash", 600.0)
        greedy = GreedyOptimizer(game, engine_greedy.state)
        greedy_result = greedy.optimize(target_time=600.0, max_steps=100)

        engine_beam = PiecewiseEngine(game)
        engine_beam.set_owned("worker", 10)
        engine_beam.set_balance("cash", 600.0)
        beam = BeamSearchOptimizer(engine_beam, beam_width=10)
        beam_result = beam.optimize(target_time=600.0, max_steps=100)

        assert beam_result.final_production >= greedy_result.final_production * 0.99


class TestBeamWidthParameter:
    def test_beam_width_parameter(self):
        game = _make_multiplicative_trap_game()

        results = {}
        for width in [1, 3, 5, 10]:
            engine = PiecewiseEngine(game)
            engine.set_owned("worker", 10)
            engine.set_balance("cash", 600.0)
            optimizer = BeamSearchOptimizer(engine, beam_width=width)
            results[width] = optimizer.optimize(target_time=600.0, max_steps=100)

        for narrow, wide in [(1, 3), (3, 5), (5, 10)]:
            assert results[wide].final_production >= results[narrow].final_production * 0.99, (
                f"beam_width={wide} ({results[wide].final_production:.2f}) should be >= "
                f"beam_width={narrow} ({results[narrow].final_production:.2f})"
            )


class TestBeamOnMiniCap:
    def test_beam_on_minicap(self):
        fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
        with open(fixture_path) as f:
            data = json.load(f)
        game = GameDefinition.model_validate(data)
        engine = PiecewiseEngine(game, validate=True)
        engine.set_balance("cash", 50.0)
        engine.purchase("lemonade", 1)

        optimizer = BeamSearchOptimizer(engine, beam_width=5)
        result = optimizer.optimize(target_time=300.0, max_steps=200)

        assert len(result.purchases) > 5
        assert result.final_production > 0
        assert result.final_balance >= 0
        assert engine.time == pytest.approx(300.0)


class TestBeamRespectsMaxSteps:
    def test_beam_respects_max_steps(self):
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 1e10)
        engine.set_owned("cheap", 1)

        optimizer = BeamSearchOptimizer(engine, beam_width=5)
        result = optimizer.optimize(target_time=1000.0, max_steps=10)
        assert len(result.purchases) <= 10
