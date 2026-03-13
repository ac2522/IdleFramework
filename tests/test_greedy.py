"""Tests for GreedyOptimizer — TDD-first."""

from __future__ import annotations

import pytest

from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.optimizer.greedy import GreedyOptimizer, PurchaseStep

# ---------------------------------------------------------------------------
# Helper: build a minimal 2-generator game for unit tests
# ---------------------------------------------------------------------------

def _two_gen_game() -> GameDefinition:
    """Two generators producing into one resource.

    gen_a: base_production=10, cost_base=100, cost_growth_rate=1.07, cycle_time=1
       => efficiency of first unit = (10/1) / 100 = 0.1
    gen_b: base_production=5, cost_base=20, cost_growth_rate=1.07, cycle_time=1
       => efficiency of first unit = (5/1) / 20 = 0.25   <-- better
    """
    data = {
        "schema_version": "1.0",
        "name": "TwoGen",
        "description": "Two-generator test game",
        "stacking_groups": {"upgrades": "multiplicative"},
        "nodes": [
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 1000.0},
            {
                "id": "gen_a", "type": "generator", "name": "Gen A",
                "base_production": 10.0, "cost_base": 100.0,
                "cost_growth_rate": 1.07, "cycle_time": 1.0,
            },
            {
                "id": "gen_b", "type": "generator", "name": "Gen B",
                "base_production": 5.0, "cost_base": 20.0,
                "cost_growth_rate": 1.07, "cycle_time": 1.0,
            },
        ],
        "edges": [
            {"id": "e_a", "source": "gen_a", "target": "cash", "edge_type": "production_target"},
            {"id": "e_b", "source": "gen_b", "target": "cash", "edge_type": "production_target"},
        ],
    }
    return GameDefinition.model_validate(data)


def _two_gen_with_mult_upgrade() -> GameDefinition:
    """Two generators + a x3 multiplicative upgrade targeting gen_a."""
    data = {
        "schema_version": "1.0",
        "name": "TwoGenUpg",
        "description": "Two-generator game with multiplicative upgrade",
        "stacking_groups": {"upgrades": "multiplicative"},
        "nodes": [
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 5000.0},
            {
                "id": "gen_a", "type": "generator", "name": "Gen A",
                "base_production": 10.0, "cost_base": 100.0,
                "cost_growth_rate": 1.07, "cycle_time": 1.0,
            },
            {
                "id": "gen_b", "type": "generator", "name": "Gen B",
                "base_production": 5.0, "cost_base": 20.0,
                "cost_growth_rate": 1.07, "cycle_time": 1.0,
            },
            {
                "id": "x3_a", "type": "upgrade", "name": "x3 Gen A",
                "upgrade_type": "multiplicative", "magnitude": 3.0,
                "cost": 500.0, "target": "gen_a", "stacking_group": "upgrades",
            },
        ],
        "edges": [
            {"id": "e_a", "source": "gen_a", "target": "cash", "edge_type": "production_target"},
            {"id": "e_b", "source": "gen_b", "target": "cash", "edge_type": "production_target"},
        ],
    }
    return GameDefinition.model_validate(data)


def _two_gen_with_additive_upgrade() -> GameDefinition:
    """Two generators + an additive upgrade targeting gen_a."""
    data = {
        "schema_version": "1.0",
        "name": "TwoGenAdd",
        "description": "Two-generator game with additive upgrade",
        "stacking_groups": {"upgrades": "additive"},
        "nodes": [
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 5000.0},
            {
                "id": "gen_a", "type": "generator", "name": "Gen A",
                "base_production": 10.0, "cost_base": 100.0,
                "cost_growth_rate": 1.07, "cycle_time": 1.0,
            },
            {
                "id": "gen_b", "type": "generator", "name": "Gen B",
                "base_production": 5.0, "cost_base": 20.0,
                "cost_growth_rate": 1.07, "cycle_time": 1.0,
            },
            {
                "id": "add_a", "type": "upgrade", "name": "+50 Gen A",
                "upgrade_type": "additive", "magnitude": 50.0,
                "cost": 200.0, "target": "gen_a", "stacking_group": "upgrades",
            },
        ],
        "edges": [
            {"id": "e_a", "source": "gen_a", "target": "cash", "edge_type": "production_target"},
            {"id": "e_b", "source": "gen_b", "target": "cash", "edge_type": "production_target"},
        ],
    }
    return GameDefinition.model_validate(data)


def _empty_game() -> GameDefinition:
    """A game with only a resource and no generators or upgrades."""
    data = {
        "schema_version": "1.0",
        "name": "Empty",
        "description": "Empty game",
        "stacking_groups": {},
        "nodes": [
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0.0},
        ],
        "edges": [],
    }
    return GameDefinition.model_validate(data)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGreedyEfficiency:
    """Test efficiency calculations."""

    def test_greedy_buys_best_efficiency(self):
        """With 2 generators of known efficiency, greedy picks the better one first.

        gen_a: efficiency = 10/100 = 0.1
        gen_b: efficiency = 5/20  = 0.25  <-- should be picked first
        """
        game = _two_gen_game()
        # Give initial generators so there's production
        state = GameState.from_game(game)
        state.get("gen_a").owned = 1
        state.get("gen_b").owned = 1

        opt = GreedyOptimizer(game, state)
        result = opt.find_best_purchase()

        assert result is not None
        node_id, efficiency = result
        assert node_id == "gen_b", (
            f"Expected gen_b (eff=0.25) to be picked over gen_a (eff=0.1), got {node_id}"
        )

    def test_greedy_multiplicative_formula(self):
        """Verify multiplicative upgrade efficiency = production * (mult - 1) / cost.

        gen_a with 5 owned: rate = 10 * 5 / 1.0 = 50/sec
        x3_a upgrade: efficiency = 50 * (3 - 1) / 500 = 0.2
        """
        game = _two_gen_with_mult_upgrade()
        state = GameState.from_game(game)
        state.get("gen_a").owned = 5
        state.get("gen_b").owned = 1

        opt = GreedyOptimizer(game, state)
        eff = opt.compute_upgrade_efficiency("x3_a")

        # production of gen_a = 10 * 5 / 1.0 = 50
        # efficiency = 50 * (3-1) / 500 = 0.2
        assert eff == pytest.approx(0.2, rel=1e-6)

    def test_greedy_additive_formula(self):
        """Verify additive upgrade efficiency = (bonus * base_production) / cost.

        gen_a with 5 owned: base_production per generator per second = 10/1 = 10
        add_a: bonus=50, cost=200
        efficiency = (50 * 10) / 200 = 2.5

        NOTE: For additive upgrades, we treat the bonus as adding that many
        units worth of base_production.
        """
        game = _two_gen_with_additive_upgrade()
        state = GameState.from_game(game)
        state.get("gen_a").owned = 5
        state.get("gen_b").owned = 1

        opt = GreedyOptimizer(game, state)
        eff = opt.compute_upgrade_efficiency("add_a")

        # additive: bonus * (base_production / cycle_time) / cost
        # = 50 * (10 / 1) / 200 = 2.5
        assert eff == pytest.approx(2.5, rel=1e-6)


class TestGreedyOnMinicap:
    """Integration tests using the MiniCap fixture."""

    def test_greedy_on_minicap(self, minicap):
        """Run optimizer on minicap fixture, produces non-empty purchase sequence.

        Start with 1 lemonade so there's initial production.
        """
        state = GameState.from_game(minicap)
        state.get("lemonade").owned = 1
        state.get("cash").current_value = 5.0  # small starting cash

        opt = GreedyOptimizer(minicap, state)
        steps = opt.run(target_time=600.0, max_steps=20)

        assert len(steps) > 0, "Should produce at least one purchase"
        # paid_x10 is free (cost=0), so it gets infinite efficiency and is bought first
        # After that, lemonade should be among early purchases (cheapest generator)
        node_ids = [s.node_id for s in steps]
        assert "paid_x10" in node_ids, "Free upgrade should be purchased"
        # Should also buy at least one generator
        gen_ids = {"lemonade", "newspaper", "carwash"}
        assert any(nid in gen_ids for nid in node_ids), "Should buy at least one generator"


class TestGreedyConstraints:
    """Test optimizer constraints and edge cases."""

    def test_greedy_respects_max_steps(self):
        """max_steps parameter limits the number of purchases."""
        game = _two_gen_game()
        state = GameState.from_game(game)
        state.get("gen_a").owned = 1
        state.get("gen_b").owned = 1

        opt = GreedyOptimizer(game, state)
        steps = opt.run(target_time=10000.0, max_steps=5)

        assert len(steps) <= 5

    def test_greedy_records_purchase_steps(self):
        """Each PurchaseStep has valid time, node_id, cost, efficiency."""
        game = _two_gen_game()
        state = GameState.from_game(game)
        state.get("gen_a").owned = 1
        state.get("gen_b").owned = 1

        opt = GreedyOptimizer(game, state)
        steps = opt.run(target_time=10000.0, max_steps=10)

        assert len(steps) > 0
        for step in steps:
            assert isinstance(step, PurchaseStep)
            assert step.time >= 0.0
            assert isinstance(step.node_id, str)
            assert step.cost > 0.0
            assert step.efficiency > 0.0
            assert step.cash_before >= step.cost  # must have enough to buy
            assert step.cash_after >= 0.0  # non-negative after purchase

    def test_greedy_production_increases(self):
        """Total production rate increases monotonically over purchases."""
        game = _two_gen_game()
        state = GameState.from_game(game)
        state.get("gen_a").owned = 1
        state.get("gen_b").owned = 1

        opt = GreedyOptimizer(game, state)

        prev_rate = opt.total_production_rate()
        opt.run(target_time=10000.0, max_steps=10)

        # After the full run, production should be higher than initial
        final_rate = opt.total_production_rate()
        assert final_rate > prev_rate, (
            f"Production should increase: initial={prev_rate}, final={final_rate}"
        )

    def test_greedy_handles_no_purchases(self):
        """Empty game or game with nothing affordable returns empty sequence."""
        game = _empty_game()
        state = GameState.from_game(game)

        opt = GreedyOptimizer(game, state)
        steps = opt.run(target_time=100.0, max_steps=10)

        assert steps == []


def test_greedy_tickspeed_upgrade_efficiency():
    """Tickspeed upgrade should be valued based on total production impact."""
    from idleframework.model.nodes import Resource, Generator, TickspeedNode, Upgrade
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState
    from idleframework.optimizer.greedy import GreedyOptimizer

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=1000.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
            TickspeedNode(id="ts1"),
            Upgrade(id="ts_upg", name="Tick Boost", upgrade_type="multiplicative",
                    magnitude=2.0, cost=500.0, target="ts1", stacking_group="tick"),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={"tick": "multiplicative"},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 5
    opt = GreedyOptimizer(game, state)
    eff = opt.compute_upgrade_efficiency("ts_upg")
    assert eff > 0  # Should have positive efficiency


def test_greedy_prestige_candidate():
    """Prestige should appear as a candidate when gain > 0."""
    from idleframework.model.nodes import Resource, Generator, PrestigeLayer
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState
    from idleframework.optimizer.greedy import GreedyOptimizer

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=0.0),
            Resource(id="pp", name="PP"),
            Generator(id="gen1", name="G", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
            PrestigeLayer(id="p1", formula_expr="floor(sqrt(lifetime_gold))",
                         layer_index=1, reset_scope=["gen1", "gold"],
                         currency_id="pp"),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    state.lifetime_earnings["gold"] = 10000.0
    opt = GreedyOptimizer(game, state)
    candidates = opt.get_candidates()
    prestige_candidates = [c for c in candidates if c.get("type") == "prestige"]
    assert len(prestige_candidates) > 0


def test_approximation_level_exact():
    from idleframework.model.nodes import Resource, Generator
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState
    from idleframework.optimizer.greedy import GreedyOptimizer

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=0.0),
            Generator(id="gen1", name="G", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    opt = GreedyOptimizer(game, state)
    result = opt.optimize(target_time=60.0, max_steps=10)
    assert result.approximation_level == "exact"


def test_greedy_skips_autobuyer_targets():
    """Greedy should not recommend purchasing nodes managed by autobuyers."""
    from idleframework.model.nodes import Resource, Generator, AutobuyerNode
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState
    from idleframework.optimizer.greedy import GreedyOptimizer

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=10000.0),
            Generator(id="gen1", name="Auto-Miner", base_production=10.0, cost_base=10, cost_growth_rate=1.15),
            Generator(id="gen2", name="Manual-Logger", base_production=5.0, cost_base=10, cost_growth_rate=1.15),
            AutobuyerNode(id="ab1", target="gen1", interval=1.0),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="gen2", target="gold", edge_type="production_target"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen2").owned = 1
    opt = GreedyOptimizer(game, state)
    best = opt.find_best_purchase()
    assert best is not None
    assert best[0] == "gen2"  # Should skip gen1 (autobuyer-managed)
