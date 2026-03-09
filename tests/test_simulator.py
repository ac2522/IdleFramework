"""Tests for RK4 simulator and MiniCap fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from idleframework.model.game import GameDefinition
from idleframework.model.nodes import Generator, Upgrade
from idleframework.model.state import GameState

from simulator import rk4_step, simulate_constant_production, simulate_with_events


# ---------- RK4 Core Tests ----------


class TestRK4ConstantProduction:
    """RK4 with constant rates should be exact (linear ODE)."""

    def test_constant_production_1_unit_per_sec(self):
        """1 unit/sec for 10 sec = 10 units."""
        result = simulate_constant_production(
            initial={"gold": 0.0},
            rates={"gold": 1.0},
            duration=10.0,
            dt=0.01,
        )
        assert abs(result["gold"] - 10.0) < 1e-9

    def test_known_production_rate(self):
        """5 lemonades at 1/sec each for 60s = 300 total."""
        result = simulate_constant_production(
            initial={"cash": 0.0},
            rates={"cash": 5.0},  # 5 generators * 1/sec
            duration=60.0,
            dt=0.01,
        )
        assert abs(result["cash"] - 300.0) < 1e-6

    def test_multiple_resources(self):
        """Multiple resources accumulate independently."""
        result = simulate_constant_production(
            initial={"gold": 100.0, "wood": 0.0},
            rates={"gold": 10.0, "wood": 5.0},
            duration=20.0,
            dt=0.01,
        )
        assert abs(result["gold"] - 300.0) < 1e-6
        assert abs(result["wood"] - 100.0) < 1e-6

    def test_zero_rate_unchanged(self):
        """Resources with zero rate stay at initial value."""
        result = simulate_constant_production(
            initial={"gold": 42.0},
            rates={"gold": 0.0},
            duration=100.0,
            dt=0.1,
        )
        assert abs(result["gold"] - 42.0) < 1e-12


class TestRK4Convergence:
    """Results converge as dt decreases."""

    def test_convergence_with_step_sizes(self):
        """All step sizes produce the same result for constant rates.

        For constant production (linear ODE), RK4 is exact regardless of
        step size, so all should converge to 500.0.
        """
        expected = 500.0
        for dt in [1.0, 0.1, 0.01]:
            result = simulate_constant_production(
                initial={"cash": 0.0},
                rates={"cash": 50.0},
                duration=10.0,
                dt=dt,
            )
            assert abs(result["cash"] - expected) < 1e-6, (
                f"dt={dt}: got {result['cash']}, expected {expected}"
            )


class TestRK4VsAnalytical:
    """Compare RK4 against known analytical solutions."""

    def test_rk4_vs_analytical_single_generator(self):
        """1 generator, 10 owned, known production.

        Analytical: production_per_unit * count * time
        = 1.0 * 10 * 100.0 = 1000.0
        RK4 at dt=0.001 should match within 1e-5.
        """
        count = 10
        production_per_unit = 1.0
        total_rate = production_per_unit * count
        duration = 100.0

        # Analytical
        analytical = total_rate * duration

        # RK4
        result = simulate_constant_production(
            initial={"cash": 0.0},
            rates={"cash": total_rate},
            duration=duration,
            dt=0.001,
        )

        assert abs(result["cash"] - analytical) < 1e-5, (
            f"RK4={result['cash']}, analytical={analytical}"
        )


class TestRK4WithEvents:
    """Event-driven simulation tests."""

    def test_rate_change_event(self):
        """Rate doubles at t=5, so total = 5*1 + 5*2 = 15."""
        rate_changed = False

        def checker(t, state):
            nonlocal rate_changed
            if t >= 5.0 and not rate_changed:
                rate_changed = True
                return [{"type": "set_rate", "resource": "gold", "value": 2.0}]
            return []

        result = simulate_with_events(
            initial={"gold": 0.0},
            rates={"gold": 1.0},
            duration=10.0,
            dt=0.01,
            event_checker=checker,
        )
        assert abs(result["gold"] - 15.0) < 0.1  # Looser tolerance due to step boundary

    def test_set_value_event(self):
        """Reset resource to 0 at t=5, then accumulate for 5 more seconds."""
        reset_done = False

        def checker(t, state):
            nonlocal reset_done
            if t >= 5.0 and not reset_done:
                reset_done = True
                return [{"type": "set_value", "resource": "gold", "value": 0.0}]
            return []

        result = simulate_with_events(
            initial={"gold": 0.0},
            rates={"gold": 10.0},
            duration=10.0,
            dt=0.01,
            event_checker=checker,
        )
        # After reset at t=5: ~5 seconds * 10/sec = ~50
        assert abs(result["gold"] - 50.0) < 0.5


class TestSingleRK4Step:
    """Test the raw rk4_step function."""

    def test_single_step(self):
        """A single step of size 1.0 at rate 5.0 adds 5.0."""
        state = {"x": 0.0}
        rates = {"x": 5.0}
        new = rk4_step(state, rates, dt=1.0)
        assert abs(new["x"] - 5.0) < 1e-12

    def test_does_not_mutate_input(self):
        """rk4_step should return a new dict, not modify the input."""
        state = {"x": 10.0}
        rates = {"x": 1.0}
        new = rk4_step(state, rates, dt=1.0)
        assert state["x"] == 10.0
        assert new["x"] == 11.0


# ---------- MiniCap Fixture Tests ----------


class TestMiniCapFixtureLoads:
    """Loading and validating the MiniCap JSON fixture."""

    def test_minicap_fixture_loads(self, minicap):
        """Load JSON, validate via GameDefinition, check structure."""
        assert minicap.name == "MiniCap"
        assert minicap.schema_version == "1.0"

        generators = [n for n in minicap.nodes if isinstance(n, Generator)]
        assert len(generators) == 3, f"Expected 3 generators, got {len(generators)}"

        upgrades = [n for n in minicap.nodes if isinstance(n, Upgrade)]
        assert len(upgrades) == 10, f"Expected 10 upgrades, got {len(upgrades)}"

    def test_minicap_has_prestige_layer(self, minicap):
        from idleframework.model.nodes import PrestigeLayer

        prestige_nodes = [n for n in minicap.nodes if isinstance(n, PrestigeLayer)]
        assert len(prestige_nodes) == 1
        assert prestige_nodes[0].id == "prestige"

    def test_minicap_has_achievement(self, minicap):
        from idleframework.model.nodes import Achievement

        achievements = [n for n in minicap.nodes if isinstance(n, Achievement)]
        assert len(achievements) == 1
        assert achievements[0].id == "milestone_25_lemon"

    def test_minicap_has_end_condition(self, minicap):
        from idleframework.model.nodes import EndCondition

        end_nodes = [n for n in minicap.nodes if isinstance(n, EndCondition)]
        assert len(end_nodes) == 1

    def test_minicap_stacking_groups(self, minicap):
        assert "cash_upgrades" in minicap.stacking_groups
        assert "milestones" in minicap.stacking_groups
        assert minicap.stacking_groups["cash_upgrades"] == "multiplicative"

    def test_minicap_edges(self, minicap):
        assert len(minicap.edges) == 3
        targets = {e.target for e in minicap.edges}
        assert targets == {"cash"}


class TestMiniCapGameState:
    """GameState initialization from MiniCap."""

    def test_minicap_gamestate_init(self, minicap):
        """GameState.from_game(minicap) initializes all node states."""
        state = GameState.from_game(minicap)
        # Every node should have a state entry
        for node in minicap.nodes:
            assert node.id in state.node_states, f"Missing state for {node.id}"

    def test_minicap_initial_cash_zero(self, minicap):
        state = GameState.from_game(minicap)
        assert state.get_resource_value("cash") == 0.0

    def test_minicap_initial_angels_zero(self, minicap):
        state = GameState.from_game(minicap)
        assert state.get_resource_value("angels") == 0.0

    def test_minicap_elapsed_time_zero(self, minicap):
        state = GameState.from_game(minicap)
        assert state.elapsed_time == 0.0


class TestMiniCapGraphValidation:
    """Graph validation on MiniCap fixture."""

    def test_minicap_graph_validates(self, minicap):
        """validate_graph returns no errors for MiniCap."""
        from idleframework.graph.validation import validate_graph

        errors = validate_graph(minicap)
        assert errors == [], f"Unexpected validation errors: {errors}"
