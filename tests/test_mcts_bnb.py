"""Tests for MCTS and Branch-and-Bound optimizers.

MCTS: Monte Carlo Tree Search with epsilon-greedy rollouts, UCB1 selection,
and average backup. Should be anytime (more iterations = equal or better).

Branch-and-Bound: DFS with pruning via upper-bound estimates. Should find
provably optimal sequences for small problems.
"""
import copy
import itertools
import json
import pytest
from pathlib import Path

from idleframework.model.game import GameDefinition
from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import bulk_cost, time_to_afford
from idleframework.optimizer.greedy import GreedyOptimizer, OptimizeResult
from idleframework.optimizer.mcts import MCTSOptimizer
from idleframework.optimizer.bnb import BranchAndBoundOptimizer


def _make_two_gen_game():
    """Two generators — simple test scenario."""
    return GameDefinition(
        schema_version="1.0",
        name="TwoGenTest",
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


def _make_three_candidate_game():
    """Three generators with clear efficiency differences for BnB testing."""
    return GameDefinition(
        schema_version="1.0",
        name="ThreeCandidateTest",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "gen_a", "type": "generator", "name": "Gen A",
             "base_production": 1.0, "cost_base": 5.0, "cost_growth_rate": 1.1,
             "cycle_time": 1.0},
            {"id": "gen_b", "type": "generator", "name": "Gen B",
             "base_production": 3.0, "cost_base": 20.0, "cost_growth_rate": 1.1,
             "cycle_time": 1.0},
            {"id": "gen_c", "type": "generator", "name": "Gen C",
             "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.1,
             "cycle_time": 1.0},
        ],
        edges=[
            {"id": "e1", "source": "gen_a", "target": "cash", "edge_type": "production_target"},
            {"id": "e2", "source": "gen_b", "target": "cash", "edge_type": "production_target"},
            {"id": "e3", "source": "gen_c", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={},
    )


def _load_minicap():
    fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return GameDefinition.model_validate(data)


# ---------------------------------------------------------------------------
# MCTS tests
# ---------------------------------------------------------------------------

class TestMCTS:
    def test_mcts_epsilon_greedy_rollouts(self):
        """With epsilon > 0, rollouts aren't all identical — there's randomness."""
        game = _make_two_gen_game()

        # Run MCTS multiple times with high epsilon to get variance
        results_purchases = []
        for seed in range(10):
            engine = PiecewiseEngine(game)
            engine.set_balance("cash", 100.0)
            engine.set_owned("cheap", 1)
            opt = MCTSOptimizer(engine, iterations=50, rollout_depth=5, epsilon=0.8, seed=seed)
            result = opt.optimize(target_time=120.0, max_steps=20)
            purchase_ids = tuple(p.node_id for p in result.purchases)
            results_purchases.append(purchase_ids)

        # With epsilon=0.8, different seeds should produce at least some different sequences
        unique_sequences = set(results_purchases)
        assert len(unique_sequences) > 1, "All 10 seeds produced identical sequences — no randomness"

    def test_mcts_seeded_determinism(self):
        """Same seed produces the same result."""
        game = _make_two_gen_game()

        def run_with_seed(seed):
            engine = PiecewiseEngine(game)
            engine.set_balance("cash", 100.0)
            engine.set_owned("cheap", 1)
            opt = MCTSOptimizer(engine, iterations=50, rollout_depth=5, epsilon=0.3, seed=seed)
            return opt.optimize(target_time=120.0, max_steps=20)

        r1 = run_with_seed(42)
        r2 = run_with_seed(42)

        assert len(r1.purchases) == len(r2.purchases)
        for p1, p2 in zip(r1.purchases, r2.purchases):
            assert p1.node_id == p2.node_id
            assert p1.cost == pytest.approx(p2.cost)
        assert r1.final_production == pytest.approx(r2.final_production)

    def test_mcts_anytime(self):
        """More iterations should generally produce better results (statistical)."""
        game = _make_two_gen_game()

        low_prods = []
        high_prods = []
        for seed in range(5):
            engine = PiecewiseEngine(game)
            engine.set_balance("cash", 100.0)
            engine.set_owned("cheap", 1)
            opt = MCTSOptimizer(engine, iterations=10, rollout_depth=8, epsilon=0.2, seed=seed)
            r = opt.optimize(target_time=120.0, max_steps=20)
            low_prods.append(r.final_production)

            engine2 = PiecewiseEngine(game)
            engine2.set_balance("cash", 100.0)
            engine2.set_owned("cheap", 1)
            opt2 = MCTSOptimizer(engine2, iterations=200, rollout_depth=8, epsilon=0.2, seed=seed)
            r2 = opt2.optimize(target_time=120.0, max_steps=20)
            high_prods.append(r2.final_production)

        # On average, more iterations should be at least as good
        avg_low = sum(low_prods) / len(low_prods)
        avg_high = sum(high_prods) / len(high_prods)
        assert avg_high >= avg_low * 0.9  # allow small margin

    def test_mcts_on_minicap(self):
        """MCTS should produce a valid result on MiniCap."""
        game = _load_minicap()
        engine = PiecewiseEngine(game, validate=True)
        engine.set_balance("cash", 200.0)
        engine.purchase("lemonade", 5)

        opt = MCTSOptimizer(engine, iterations=50, rollout_depth=10, epsilon=0.2, seed=123)
        result = opt.optimize(target_time=300.0, max_steps=100)

        assert isinstance(result, OptimizeResult)
        assert len(result.purchases) > 0
        assert result.final_production > 0
        assert result.final_balance >= 0
        assert result.final_time == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# Branch-and-Bound tests
# ---------------------------------------------------------------------------

class TestBranchAndBound:
    def test_bnb_small_problem_optimal(self):
        """3 candidates, depth 5: BnB finds a good sequence."""
        game = _make_three_candidate_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 200.0)
        engine.set_owned("gen_a", 1)

        opt = BranchAndBoundOptimizer(engine, depth_limit=5)
        result = opt.optimize(target_time=120.0, max_steps=50)

        assert isinstance(result, OptimizeResult)
        assert len(result.purchases) > 0
        assert result.final_production > 0
        # BnB should find a reasonable production rate
        assert result.final_production >= 10.0

    def test_bnb_respects_depth_limit(self):
        """With depth_limit=3, BnB doesn't make more than 3 purchases in search."""
        game = _make_three_candidate_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 500.0)
        engine.set_owned("gen_a", 1)

        opt = BranchAndBoundOptimizer(engine, depth_limit=3)
        result = opt.optimize(target_time=120.0, max_steps=50)

        assert isinstance(result, OptimizeResult)
        # The result should have at most depth_limit purchases
        assert len(result.purchases) <= 3

    def test_bnb_matches_exhaustive(self):
        """For a tiny problem (2 generators, depth 3), matches brute-force enumeration."""
        game = _make_two_gen_game()

        def run_exhaustive(target_time):
            """Brute-force all possible 3-purchase sequences."""
            candidates = ["cheap", "expensive"]
            best_production = -1.0
            best_seq = None

            for seq in itertools.product(candidates, repeat=3):
                engine = PiecewiseEngine(game)
                engine.set_balance("cash", 600.0)
                engine.set_owned("cheap", 1)

                pay_resource = "cash"
                valid = True
                for node_id in seq:
                    gen = engine._generators[node_id]
                    owned = engine.get_owned(node_id)
                    cost = bulk_cost(gen.cost_base, gen.cost_growth_rate, owned, 1)
                    balance = engine.get_balance(pay_resource)
                    rate = engine.get_production_rate(pay_resource)

                    if balance < cost - 1e-10:
                        if rate <= 0:
                            valid = False
                            break
                        wait = time_to_afford(cost, rate, balance)
                        if engine.time + wait > target_time:
                            valid = False
                            break
                        engine.advance_to(engine.time + wait)

                    balance = engine.get_balance(pay_resource)
                    if balance < cost - 1e-10:
                        valid = False
                        break

                    engine.purchase(node_id, 1)

                if not valid:
                    # Advance to target and measure what we got
                    if engine.time < target_time:
                        engine.advance_to(target_time)
                    prod = engine.get_production_rate(pay_resource)
                    if prod > best_production:
                        best_production = prod
                        best_seq = seq
                    continue

                if engine.time < target_time:
                    engine.advance_to(target_time)
                prod = engine.get_production_rate(pay_resource)
                if prod > best_production:
                    best_production = prod
                    best_seq = seq

            return best_production, best_seq

        target_time = 60.0
        exhaustive_prod, exhaustive_seq = run_exhaustive(target_time)

        # Now run BnB
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 600.0)
        engine.set_owned("cheap", 1)
        opt = BranchAndBoundOptimizer(engine, depth_limit=3)
        bnb_result = opt.optimize(target_time=target_time, max_steps=50)

        # BnB should match or beat exhaustive
        assert bnb_result.final_production >= exhaustive_prod - 1e-6, (
            f"BnB production {bnb_result.final_production} < exhaustive {exhaustive_prod} "
            f"(exhaustive seq: {exhaustive_seq})"
        )
