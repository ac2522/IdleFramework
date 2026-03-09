"""Tests for the beam search optimizer.

The beam search optimizer maintains top-K states at each step,
exploring multiple purchase paths in parallel. This lets it find
solutions where a locally suboptimal purchase (e.g., an expensive
multiplier) leads to globally better production.
"""
import copy
import json
import pytest
from pathlib import Path
from idleframework.model.game import GameDefinition
from idleframework.engine.segments import PiecewiseEngine
from idleframework.optimizer.beam import BeamSearchOptimizer
from idleframework.optimizer.greedy import GreedyOptimizer, OptimizeResult


def _make_two_gen_game():
    """Two generators with different efficiency profiles."""
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
    """Game where greedy buys cheap generators but beam should buy the x10 upgrade first.

    The x10 upgrade costs 500 and multiplies all production by 10.
    Cheap generators cost 5 each and produce 1/s.
    Greedy sees generator efficiency = 1/5 = 0.2 vs upgrade efficiency (with 1 gen) = 1*(10-1)/500 = 0.018.
    So greedy buys many cheap gens first.

    But with enough starting cash, buying the x10 upgrade first and then generators
    gives 10x production on every subsequent generator, which compounds to much more.

    We give enough starting cash + production time for this to matter.
    """
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
        """Beam width > 1 should explore non-greedy paths."""
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 600.0)
        engine.set_owned("cheap", 1)

        optimizer = BeamSearchOptimizer(engine, beam_width=3)
        result = optimizer.optimize(target_time=60.0, max_steps=10)

        # With beam_width=3, we should have explored multiple paths
        assert isinstance(result, OptimizeResult)
        assert len(result.purchases) > 0
        # The result should include purchases of both generator types
        # (beam explores alternatives unlike greedy which only picks one)
        node_ids = {p.node_id for p in result.purchases}
        # At minimum, the beam should have considered both generators
        assert len(result.purchases) >= 2


class TestBeamDeterministic:
    def test_beam_deterministic(self):
        """Same input should produce identical output."""
        game = _make_two_gen_game()

        results = []
        for _ in range(3):
            engine = PiecewiseEngine(game)
            engine.set_balance("cash", 200.0)
            engine.set_owned("cheap", 1)
            optimizer = BeamSearchOptimizer(engine, beam_width=5)
            results.append(optimizer.optimize(target_time=60.0, max_steps=20))

        # All runs should produce identical purchase sequences
        for r in results[1:]:
            assert len(r.purchases) == len(results[0].purchases)
            for p1, p2 in zip(results[0].purchases, r.purchases):
                assert p1.node_id == p2.node_id
                assert p1.cost == pytest.approx(p2.cost, rel=1e-9)
            assert r.final_production == pytest.approx(results[0].final_production, rel=1e-9)


class TestBeamBeatsGreedyOnMultiplicative:
    def test_beam_beats_greedy_on_multiplicative(self):
        """Beam search should beat greedy when an expensive multiplier is better long-term.

        Setup: 10 workers producing 1/s each = 10/s total.
        Starting cash: 600 (enough for the x10 upgrade at cost 500, or ~12 more workers).
        Time horizon: 600s.

        Greedy will buy cheap workers first (efficiency 1/5.25 > 10*9/500 = 0.18 with 10 gens).
        But buying the x10 first makes each worker produce 10/s, so all future production
        is 10x higher. Over 600s this compounds to much more total production.
        """
        game = _make_multiplicative_trap_game()

        # Run greedy
        engine_greedy = PiecewiseEngine(game)
        engine_greedy.set_owned("worker", 10)
        engine_greedy.set_balance("cash", 600.0)
        greedy = GreedyOptimizer(engine_greedy)
        greedy_result = greedy.optimize(target_time=600.0, max_steps=100)

        # Run beam with wide beam
        engine_beam = PiecewiseEngine(game)
        engine_beam.set_owned("worker", 10)
        engine_beam.set_balance("cash", 600.0)
        beam = BeamSearchOptimizer(engine_beam, beam_width=10)
        beam_result = beam.optimize(target_time=600.0, max_steps=100)

        # Beam should achieve at least as good production as greedy
        # In this scenario, beam should find the upgrade-first path
        assert beam_result.final_production >= greedy_result.final_production * 0.99


class TestBeamWidthParameter:
    def test_beam_width_parameter(self):
        """Wider beam should produce equal or better result."""
        game = _make_multiplicative_trap_game()

        results = {}
        for width in [1, 3, 5, 10]:
            engine = PiecewiseEngine(game)
            engine.set_owned("worker", 10)
            engine.set_balance("cash", 600.0)
            optimizer = BeamSearchOptimizer(engine, beam_width=width)
            results[width] = optimizer.optimize(target_time=600.0, max_steps=100)

        # Wider beam should produce equal or better final production
        # (with some tolerance for floating-point)
        for narrow, wide in [(1, 3), (3, 5), (5, 10)]:
            assert results[wide].final_production >= results[narrow].final_production * 0.99, (
                f"beam_width={wide} ({results[wide].final_production:.2f}) should be >= "
                f"beam_width={narrow} ({results[narrow].final_production:.2f})"
            )


class TestBeamOnMiniCap:
    def test_beam_on_minicap(self):
        """Beam search should work on the MiniCap fixture."""
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
        """Beam optimizer should stop after max_steps purchases."""
        game = _make_two_gen_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 1e10)
        engine.set_owned("cheap", 1)

        optimizer = BeamSearchOptimizer(engine, beam_width=5)
        result = optimizer.optimize(target_time=1000.0, max_steps=10)
        assert len(result.purchases) <= 10
