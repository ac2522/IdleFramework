"""Edge case tests — capacity, drain-to-zero, empty games, numerical stability."""

import math

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.game import GameDefinition
from idleframework.model.nodes import Resource

from .conftest import PHASE_B_FIXTURES, load_e2e_game


class TestResourceCapacity:
    def test_balance_clamped_at_capacity(self, factory_engine):
        """Ore has capacity=5000. After long production, balance <= 5000."""
        factory_engine.set_owned("miner", 50)
        factory_engine.advance_to(3600.0)
        assert factory_engine.get_balance("ore") <= 5000.0 + 1e-6

    def test_waste_overflow_behavior(self, kitchen_engine):
        """Mana has overflow_behavior=waste, capacity=500."""
        kitchen_engine.set_owned("alchemist", 100)
        kitchen_engine.advance_to(3600.0)
        assert kitchen_engine.get_balance("mana") <= 500.0 + 1e-6


class TestDrainToZero:
    def test_drain_floors_at_zero(self, factory_engine):
        """Ingot rust drains at 0.5/s. Starting at 1.0, should not go negative."""
        factory_engine.set_balance("ingots", 1.0)
        factory_engine.advance_to(60.0)
        assert factory_engine.get_balance("ingots") >= -1e-9

    def test_drain_with_zero_initial_balance(self, factory_engine):
        """Starting at 0 with drain active doesn't go negative."""
        factory_engine.set_balance("ingots", 0.0)
        factory_engine.advance_to(10.0)
        assert factory_engine.get_balance("ingots") >= -1e-9


class TestEmptyGameBehavior:
    def test_no_generators_advance_succeeds(self):
        """A game with only a resource node can advance without error."""
        game = GameDefinition(
            schema_version="1.0",
            name="EmptyGame",
            nodes=[Resource(id="coins", name="Coins", initial_value=100.0)],
            edges=[],
            stacking_groups={},
        )
        engine = PiecewiseEngine(game, validate=True)
        engine.advance_to(60.0)
        assert engine.time == pytest.approx(60.0)
        assert engine.get_balance("coins") == pytest.approx(100.0)


class TestNoNegativeBalances:
    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_all_balances_non_negative_after_auto_advance(self, fixture_name):
        """After auto_advance, no resource has negative balance."""
        game = load_e2e_game(fixture_name)
        engine = PiecewiseEngine(game, validate=True)

        # Give initial funds to all resources
        for node in game.nodes:
            if isinstance(node, Resource):
                engine.set_balance(node.id, max(engine.get_balance(node.id), 1e6))

        engine.auto_advance(300.0)

        for node in game.nodes:
            if isinstance(node, Resource):
                bal = engine.get_balance(node.id)
                assert bal >= -1e-9, f"Negative balance for {node.id}: {bal}"
                assert not math.isnan(bal), f"NaN balance for {node.id}"
