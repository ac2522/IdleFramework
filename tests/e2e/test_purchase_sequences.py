"""Purchase sequence tests — verify buy logic, costs, and state transitions.

Key insight: SpeedRunner's currency resource is 'energy' (first resource),
but scanner produces 'data'. Use the correct resource for purchases.
"""

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.nodes import Generator, Resource

from .conftest import (
    PHASE_B_FIXTURES,
    find_first_generator,
    load_e2e_game,
)


def _find_currency_for_gen(game, gen_id):
    """Find the resource used as currency for purchasing a generator.
    Generators cost is paid from a resource — we need to find which one.
    The engine uses the first Resource node as the purchase currency.
    """
    for node in game.nodes:
        if isinstance(node, Resource):
            return node.id
    raise ValueError("No Resource node found")


class TestAffordabilityChecks:
    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_purchase_with_insufficient_funds_raises(self, fixture_name):
        game = load_e2e_game(fixture_name)
        engine = PiecewiseEngine(game, validate=True)
        gen_id = find_first_generator(game)
        # Zero out all resources
        for node in game.nodes:
            if isinstance(node, Resource):
                engine.set_balance(node.id, 0.0)
        with pytest.raises(ValueError):
            engine.purchase(gen_id)

    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_purchase_with_ample_funds_succeeds(self, fixture_name):
        game = load_e2e_game(fixture_name)
        engine = PiecewiseEngine(game, validate=True)
        gen_id = find_first_generator(game)
        # Set all resources high to ensure affordability
        for node in game.nodes:
            if isinstance(node, Resource):
                engine.set_balance(node.id, 1e9)
        engine.purchase(gen_id)
        assert engine.get_owned(gen_id) == 1


class TestCookieClickerPurchases:
    def test_cursor_cost_deducted(self, cookie_engine):
        """Buying cursor deducts cost_base=15.0."""
        cookie_engine.set_balance("cookies", 1000.0)
        before = cookie_engine.get_balance("cookies")
        cookie_engine.purchase("cursor")
        after = cookie_engine.get_balance("cookies")
        assert before - after == pytest.approx(15.0, rel=1e-3)

    def test_second_cursor_costs_more(self, cookie_engine):
        """Second cursor costs 15.0 * 1.15 = 17.25."""
        cookie_engine.set_balance("cookies", 1e6)
        cookie_engine.purchase("cursor")
        before = cookie_engine.get_balance("cookies")
        cookie_engine.purchase("cursor")
        after = cookie_engine.get_balance("cookies")
        cost_2nd = before - after
        assert cost_2nd == pytest.approx(15.0 * 1.15, rel=1e-3)

    def test_bulk_purchase_owned_count(self, cookie_engine):
        """Bulk purchase of 10 cursors gives owned=10."""
        cookie_engine.set_balance("cookies", 1e6)
        cookie_engine.purchase("cursor", 10)
        assert cookie_engine.get_owned("cursor") == 10

    def test_upgrade_changes_production(self, cookie_engine):
        """x2 upgrade doubles cursor production rate."""
        cookie_engine.set_owned("cursor", 10)
        rate_before = cookie_engine.get_production_rate("cookies")
        cookie_engine.set_balance("cookies", 1e6)
        cookie_engine.purchase_upgrade("upg_x2_cursor")
        rate_after = cookie_engine.get_production_rate("cookies")
        assert rate_after == pytest.approx(rate_before * 2.0, rel=1e-3)

    def test_upgrade_already_purchased_raises(self, cookie_engine):
        """Can't buy same upgrade twice."""
        cookie_engine.set_balance("cookies", 1e6)
        cookie_engine.purchase_upgrade("upg_x2_cursor")
        with pytest.raises(ValueError):
            cookie_engine.purchase_upgrade("upg_x2_cursor")

    def test_opening_sequence(self, cookie_engine):
        """Buy cursor, verify production, buy more, verify scaling."""
        cookie_engine.set_balance("cookies", 1e6)
        cookie_engine.purchase("cursor")
        assert cookie_engine.get_owned("cursor") == 1
        assert cookie_engine.get_production_rate("cookies") == pytest.approx(0.1, rel=1e-3)

        cookie_engine.purchase("cursor", 5)
        assert cookie_engine.get_owned("cursor") == 6
        assert cookie_engine.get_production_rate("cookies") == pytest.approx(0.1 * 6, rel=1e-3)


class TestFactoryIdlePurchases:
    def test_miner_produces_ore(self, factory_engine):
        """Miner's production_target is ore. Rate includes buff EV."""
        factory_engine.set_owned("miner", 1)
        ore_rate = factory_engine.get_production_rate("ore")
        # Buff EV: 1 + (2.5-1)*15/60 = 1.375. Rate = 3.0 * 1.375 = 4.125
        assert ore_rate == pytest.approx(4.125, rel=1e-3)

    def test_smelter_produces_ingots(self, factory_engine):
        """Smelter worker produces ingots. Rate includes buff EV."""
        factory_engine.set_owned("smelter_worker", 1)
        ingot_rate = factory_engine.get_production_rate("ingots")
        # base_production=1.0, cycle_time=2.0 → base_rate = 0.5/s
        # lucky_strike buff EV: 1 + 0.15*(3.0-1) = 1.3. Rate = 0.5 * 1.3 = 0.65
        assert ingot_rate == pytest.approx(0.65, rel=1e-3)


class TestSpeedRunnerPurchases:
    def test_tickspeed_upgrade_increases_production(self, speed_engine):
        """Tickspeed upgrade should boost production rates."""
        speed_engine.set_owned("scanner", 5)
        rate_before = speed_engine.get_production_rate("data")

        speed_engine.set_balance("energy", 1e9)
        speed_engine.purchase_upgrade("upg_tick_x1_5")
        rate_after = speed_engine.get_production_rate("data")

        assert rate_after > rate_before
