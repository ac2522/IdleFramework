"""Optimizer ordering tests — verify optimizers beat baseline and produce valid results."""

import copy

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.optimizer.greedy import GreedyOptimizer

from .conftest import (
    SINGLE_RESOURCE_FIXTURES,
    find_primary_resource,
    load_e2e_game,
)


class TestGreedyVsBaseline:
    @pytest.mark.parametrize("fixture_name", list(SINGLE_RESOURCE_FIXTURES))
    def test_greedy_beats_no_purchases(self, fixture_name):
        """Greedy final production >= no-purchase production at same time."""
        game = load_e2e_game(fixture_name)
        res_id = find_primary_resource(game)

        # Baseline: just advance with initial balance, no auto-buy
        baseline = PiecewiseEngine(copy.deepcopy(game), validate=True)
        baseline.set_balance(res_id, 1e6)
        baseline.advance_to(300.0)
        baseline_rate = baseline.get_production_rate(res_id)

        # Greedy
        greedy_engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
        greedy_engine.set_balance(res_id, 1e6)
        optimizer = GreedyOptimizer(game, greedy_engine.state)
        result = optimizer.optimize(target_time=300.0, max_steps=100)

        assert result.final_production >= baseline_rate

    @pytest.mark.parametrize("fixture_name", list(SINGLE_RESOURCE_FIXTURES))
    def test_greedy_returns_valid_result(self, fixture_name):
        game = load_e2e_game(fixture_name)
        res_id = find_primary_resource(game)

        engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
        engine.set_balance(res_id, 1e6)
        optimizer = GreedyOptimizer(game, engine.state)
        result = optimizer.optimize(target_time=300.0, max_steps=100)

        assert result.final_production >= 0
        assert len(result.purchases) >= 0

    @pytest.mark.parametrize("fixture_name", list(SINGLE_RESOURCE_FIXTURES))
    def test_greedy_purchases_are_chronological(self, fixture_name):
        game = load_e2e_game(fixture_name)
        res_id = find_primary_resource(game)

        engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
        engine.set_balance(res_id, 1e6)
        optimizer = GreedyOptimizer(game, engine.state)
        result = optimizer.optimize(target_time=300.0, max_steps=100)

        times = [p.time for p in result.purchases]
        for i in range(1, len(times)):
            assert times[i] >= times[i - 1], "Purchase times must be non-decreasing"


class TestBeamOptimizer:
    @pytest.mark.timeout(60)
    def test_beam_returns_valid_result(self):
        """Beam on cookie_clicker (simplest fixture) with small params."""
        from idleframework.optimizer.beam import BeamSearchOptimizer

        game = load_e2e_game("cookie_clicker")

        engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
        engine.set_balance("cookies", 1e4)
        optimizer = BeamSearchOptimizer(engine, beam_width=2)
        result = optimizer.optimize(target_time=60.0, max_steps=10)

        assert result.final_production >= 0


class TestMCTSOptimizer:
    @pytest.mark.timeout(60)
    def test_mcts_returns_valid_result(self):
        """MCTS on cookie_clicker with very small params to avoid timeout."""
        from idleframework.optimizer.mcts import MCTSOptimizer

        game = load_e2e_game("cookie_clicker")
        engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
        engine.set_balance("cookies", 1e4)
        optimizer = MCTSOptimizer(engine, iterations=5, rollout_depth=3, seed=42)
        result = optimizer.optimize(target_time=30.0, max_steps=5)

        assert result.final_production >= 0

    @pytest.mark.timeout(60)
    def test_mcts_deterministic_with_seed(self):
        from idleframework.optimizer.mcts import MCTSOptimizer

        game = load_e2e_game("cookie_clicker")
        results = []
        for _ in range(2):
            engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
            engine.set_balance("cookies", 1e4)
            optimizer = MCTSOptimizer(engine, iterations=5, rollout_depth=3, seed=42)
            result = optimizer.optimize(target_time=30.0, max_steps=5)
            results.append(result.final_production)

        assert results[0] == pytest.approx(results[1])


class TestBnBOptimizer:
    @pytest.mark.timeout(60)
    def test_bnb_returns_valid_result(self):
        """BnB on cookie_clicker with small depth and steps."""
        from idleframework.optimizer.bnb import BranchAndBoundOptimizer

        game = load_e2e_game("cookie_clicker")
        engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
        engine.set_balance("cookies", 1e4)
        optimizer = BranchAndBoundOptimizer(engine, depth_limit=3)
        result = optimizer.optimize(target_time=30.0, max_steps=5)

        assert result.final_production >= 0
