"""Tests for the piecewise analytical engine.

TDD-first: these tests are written before the implementation.
"""

from __future__ import annotations


import pytest

from idleframework.engine.events import (
    classify_formula_tier,
)
from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from simulator import simulate_constant_production


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_game(
    *,
    generators: list[dict] | None = None,
    upgrades: list[dict] | None = None,
    resources: list[dict] | None = None,
    edges: list[dict] | None = None,
    stacking_groups: dict | None = None,
    event_epsilon: float = 0.001,
    free_purchase_threshold: float = 1e-5,
) -> GameDefinition:
    """Build a minimal GameDefinition for test purposes."""
    nodes: list[dict] = []
    if resources is None:
        resources = [{"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0}]
    nodes.extend(resources)

    if generators is not None:
        nodes.extend(generators)
    if upgrades is not None:
        nodes.extend(upgrades)

    if edges is None:
        edges = []
    if stacking_groups is None:
        stacking_groups = {"cash_upgrades": "multiplicative"}

    return GameDefinition.model_validate(
        {
            "schema_version": "1.0",
            "name": "TestGame",
            "nodes": nodes,
            "edges": edges,
            "stacking_groups": stacking_groups,
            "event_epsilon": event_epsilon,
            "free_purchase_threshold": free_purchase_threshold,
        }
    )


# ---------------------------------------------------------------------------
# 1. test_single_segment_constant
# ---------------------------------------------------------------------------


class TestSingleSegmentConstant:
    """One generator, compute production over T seconds."""

    def test_one_lemonade_10s(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 1e15,  # Very expensive so no purchases happen
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
            ],
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 1

        engine = PiecewiseEngine(game, state)
        segments = engine.advance_to(10.0)

        # 1 lemonade producing 1/sec for 10s = 10 cash
        assert engine.state.get_resource_value("cash") == pytest.approx(10.0)
        # There should be exactly 1 segment (no purchases happened)
        assert len(segments) == 1


# ---------------------------------------------------------------------------
# 2. test_purchase_creates_new_segment
# ---------------------------------------------------------------------------


class TestPurchaseCreatesNewSegment:
    """Buying a generator creates a new segment with updated rates."""

    def test_purchase_adds_segment(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 4.0,
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
            ],
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 1
        # Give enough initial cash so we can afford a 2nd lemonade (cost = 4*1.07^1 = 4.28)
        state.node_states["cash"].current_value = 0.0

        engine = PiecewiseEngine(game, state)
        # Advance far enough that we can buy a second lemonade
        # At 1/sec, cost ~4.28 => takes ~4.28s. Advance to 20s.
        segments = engine.advance_to(20.0)

        # Should have multiple segments (initial + at least one purchase)
        assert len(segments) >= 2
        # Should own 2+ lemonades now (auto-purchased)
        assert engine.state.get("lemonade").owned >= 2


# ---------------------------------------------------------------------------
# 3. test_free_purchase_threshold
# ---------------------------------------------------------------------------


class TestFreePurchaseThreshold:
    """Items where cost/balance < threshold auto-purchased without advancing time."""

    def test_free_purchase_no_time_advance(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 4.0,
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
            ],
            free_purchase_threshold=1e-5,
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 1
        # Balance is vastly more than cost (4.0). Ratio = 4 / 1e9 = 4e-9 < 1e-5
        state.node_states["cash"].current_value = 1e9

        engine = PiecewiseEngine(game, state)
        purchased = engine.apply_free_purchases()

        # Should auto-purchase lemonades without time advancing
        assert len(purchased) > 0
        assert engine.current_time == 0.0


# ---------------------------------------------------------------------------
# 4. test_chattering_detection
# ---------------------------------------------------------------------------


class TestChatteringDetection:
    """Max 100 purchases per epsilon window triggers chattering handling."""

    def test_chattering_raises_or_handles(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 0.001,
                    "cost_growth_rate": 1.001,
                    "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
            ],
            event_epsilon=0.001,
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 1
        # Huge balance -> many purchases in one epsilon window
        state.node_states["cash"].current_value = 1e12

        engine = PiecewiseEngine(game, state)
        # Should NOT raise but handle chattering (batch-evaluate)
        # Or raise ChatteringError — either approach is valid
        # We just verify the engine doesn't loop forever
        engine.advance_to(1.0)
        # If chattering was detected, engine should still complete
        assert engine.current_time == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# 5. test_stale_event_recomputation
# ---------------------------------------------------------------------------


class TestStaleEventRecomputation:
    """After a purchase, time-to-next-affordable is recomputed."""

    def test_recomputation_after_purchase(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 4.0,
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
                {
                    "id": "newspaper",
                    "type": "generator",
                    "name": "Newspaper",
                    "base_production": 60.0,
                    "cost_base": 60.0,
                    "cost_growth_rate": 1.15,
                    "cycle_time": 3.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
                {"id": "e2", "source": "newspaper", "target": "cash", "edge_type": "production_target"},
            ],
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 1
        # Start with 0 cash — everything requires waiting
        state.node_states["cash"].current_value = 0.0

        engine = PiecewiseEngine(game, state)

        # Rates before: 1 lemonade * 1.0/sec = 1.0/sec for cash
        rates_before = engine.compute_production_rates()
        assert rates_before["cash"] == pytest.approx(1.0)

        # Lemonade cost = 4*1.07^1 ≈ 4.28, time = 4.28/1.0 = 4.28s
        # Newspaper cost = 60, time = 60/1.0 = 60s
        # Greedy picks by efficiency, but let's capture the state
        first_candidate = engine.find_next_purchase()
        assert first_candidate is not None
        first_id, first_time = first_candidate

        # Give enough cash and buy lemonade to change production
        engine._state.get("cash").current_value = 10.0
        engine.purchase("lemonade")

        # Now 2 lemonades → 2.0/sec, cash ≈ 5.72
        # Next purchase times should differ from before
        second_candidate = engine.find_next_purchase()
        assert second_candidate is not None
        second_id, second_time = second_candidate

        # Key assertion: after purchase, candidates are recomputed
        # Either the target changed, or the time changed
        assert (second_id, second_time) != (first_id, first_time)


# ---------------------------------------------------------------------------
# 6. test_formula_tier_classification
# ---------------------------------------------------------------------------


class TestFormulaTierClassification:
    """Classify formulas as Tier 1/2/3."""

    def test_tier1_discrete(self):
        """Formulas using only count/level/owned are Tier 1."""
        assert classify_formula_tier("count * 2") == 1

    def test_tier2_current_value(self):
        """Formulas using current_value are Tier 2."""
        assert classify_formula_tier("current_value * 0.02") == 2

    def test_tier3_feedback(self):
        """Formulas with self-referential or tightly coupled terms are Tier 3."""
        assert classify_formula_tier("current_value * production_rate") == 3

    def test_tier1_simple_constant(self):
        """Plain constants are Tier 1."""
        assert classify_formula_tier("42") == 1


# ---------------------------------------------------------------------------
# 7. test_convergence_vs_rk4
# ---------------------------------------------------------------------------


class TestConvergenceVsRK4:
    """Piecewise engine matches RK4 simulator for constant production."""

    def test_constant_production_matches_rk4(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 1e15,  # Very expensive so no purchases happen
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
            ],
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 5

        # Piecewise engine
        engine = PiecewiseEngine(game, state)
        engine.advance_to(100.0)
        piecewise_cash = engine.state.get_resource_value("cash")

        # RK4 simulator
        rk4_final = simulate_constant_production(
            initial={"cash": 0.0},
            rates={"cash": 5.0},  # 5 lemonades * 1.0/sec
            duration=100.0,
            dt=0.01,
        )

        assert piecewise_cash == pytest.approx(rk4_final["cash"], rel=1e-6)


# ---------------------------------------------------------------------------
# 8. test_advance_to_with_minicap
# ---------------------------------------------------------------------------


class TestAdvanceToWithMinicap:
    """Use minicap fixture — advance time, verify cash accumulation."""

    def test_minicap_cash_accumulation(self, minicap):
        state = GameState.from_game(minicap)
        # Give initial owned counts
        state.node_states["lemonade"].owned = 1
        state.node_states["newspaper"].owned = 0
        state.node_states["carwash"].owned = 0

        engine = PiecewiseEngine(minicap, state)
        # Rate: 1 lemonade * 1.0/sec / 1.0 cycle = 1.0 /sec
        # Advance 5 seconds (cost of 2nd lemonade = 4*1.07 = 4.28)
        engine.advance_to(5.0)

        # After 4.28s, should afford 2nd lemonade. Then 2/sec for remaining time.
        # At 4.28s: cash = 4.28, buy lemonade (cost 4.28), cash = 0
        # From 4.28 to 5.0: 0.72s * 2/sec = 1.44 cash
        # (plus possibly a 3rd lemonade purchase if affordable)
        # Just verify cash > 0 and engine ran
        assert engine.state.get_resource_value("cash") >= 0.0
        assert engine.current_time == pytest.approx(5.0)
        assert len(engine.segments) >= 1


# ---------------------------------------------------------------------------
# 9. test_multiple_generators_combined_rate
# ---------------------------------------------------------------------------


class TestMultipleGeneratorsCombinedRate:
    """Multiple generators with different rates contributing to same resource."""

    def test_combined_rate_computation(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 1e15,
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
                {
                    "id": "newspaper",
                    "type": "generator",
                    "name": "Newspaper",
                    "base_production": 60.0,
                    "cost_base": 1e15,
                    "cost_growth_rate": 1.15,
                    "cycle_time": 3.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
                {"id": "e2", "source": "newspaper", "target": "cash", "edge_type": "production_target"},
            ],
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 2
        state.node_states["newspaper"].owned = 1

        engine = PiecewiseEngine(game, state)
        rates = engine.compute_production_rates()

        # lemonade: 2 * 1.0 / 1.0 = 2.0
        # newspaper: 1 * 60.0 / 3.0 = 20.0
        # total cash rate = 22.0
        assert rates["cash"] == pytest.approx(22.0)

    def test_combined_rate_accumulation(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 1e15,
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
                {
                    "id": "newspaper",
                    "type": "generator",
                    "name": "Newspaper",
                    "base_production": 60.0,
                    "cost_base": 1e15,
                    "cost_growth_rate": 1.15,
                    "cycle_time": 3.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
                {"id": "e2", "source": "newspaper", "target": "cash", "edge_type": "production_target"},
            ],
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 2
        state.node_states["newspaper"].owned = 1

        engine = PiecewiseEngine(game, state)
        engine.advance_to(10.0)

        # 22.0/sec * 10s = 220.0
        assert engine.state.get_resource_value("cash") == pytest.approx(220.0)


# ---------------------------------------------------------------------------
# 10. test_upgrade_purchase_changes_multiplier
# ---------------------------------------------------------------------------


class TestUpgradePurchaseChangesMultiplier:
    """Buying an upgrade changes the stacking multiplier for subsequent segments."""

    def test_upgrade_multiplier_applied(self):
        game = _simple_game(
            generators=[
                {
                    "id": "lemonade",
                    "type": "generator",
                    "name": "Lemonade",
                    "base_production": 1.0,
                    "cost_base": 1e15,
                    "cost_growth_rate": 1.07,
                    "cycle_time": 1.0,
                },
            ],
            upgrades=[
                {
                    "id": "x3_lemon",
                    "type": "upgrade",
                    "name": "x3 Lemonade",
                    "upgrade_type": "multiplicative",
                    "magnitude": 3.0,
                    "cost": 100.0,
                    "target": "lemonade",
                    "stacking_group": "cash_upgrades",
                },
            ],
            edges=[
                {"id": "e1", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
            ],
        )
        state = GameState.from_game(game)
        state.node_states["lemonade"].owned = 10
        state.node_states["cash"].current_value = 0.0

        engine = PiecewiseEngine(game, state)
        rates_before = engine.compute_production_rates()

        # Rate before: 10 * 1.0 / 1.0 = 10.0
        assert rates_before["cash"] == pytest.approx(10.0)

        # Advance enough time to afford the upgrade (100 cash at 10/sec = 10s)
        # Then more time to see the multiplied rate
        engine.advance_to(30.0)

        # The upgrade should have been purchased (~10s), then production = 10 * 3 = 30/sec
        assert engine.state.get("x3_lemon").purchased is True
        # Total cash should be more than 10*30=300 (no upgrade case)
        # With upgrade bought at ~10s: 10*10 - 100 (buy) + 30*20 = 0 + 600 = 600
        assert engine.state.get_resource_value("cash") > 300.0
