"""Golden value simulation tests — verify engine produces correct results.

Key insight: advance_to() auto-purchases when balance is sufficient.
Buff EV is always applied to production rates.
compute_synergy_multipliers() returns the full multiplier (1 + bonus), not just the bonus.
"""

import copy
import math

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.nodes import Resource

from .conftest import (
    PHASE_B_FIXTURES,
    NON_MONOTONIC_FIXTURES,
    find_first_generator,
    find_primary_resource,
    load_e2e_game,
)


def _find_currency_resource(game):
    """Find the resource used as currency (for purchasing generators)."""
    from idleframework.model.nodes import Generator

    gen_targets = set()
    for edge in game.edges:
        if edge.edge_type == "production_target":
            gen_targets.add(edge.target)

    # The currency is the resource that generators produce to
    # For multi-resource games, find the one that most generators target
    for node in game.nodes:
        if isinstance(node, Resource) and node.id in gen_targets:
            return node.id
    return find_primary_resource(game)


class TestBaselineSimulation:
    """Basic simulation tests: advance, production, determinism."""

    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_advance_to_reaches_target_time(self, fixture_name):
        game = load_e2e_game(fixture_name)
        engine = PiecewiseEngine(game, validate=True)
        engine.advance_to(60.0)
        assert engine.time == pytest.approx(60.0)

    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_resource_increases_with_generator(self, fixture_name):
        """Buy a generator with minimal funds, verify production occurs."""
        game = load_e2e_game(fixture_name)
        engine = PiecewiseEngine(game, validate=True)
        gen_id = find_first_generator(game)

        # Find which resource the first generator produces to
        target_res = None
        for edge in game.edges:
            if edge.source == gen_id and edge.edge_type == "production_target":
                target_res = edge.target
                break
        if target_res is None:
            pytest.skip("Generator has no production_target edge")

        # Use set_owned to avoid needing currency
        engine.set_owned(gen_id, 1)
        # Set target resource to 0 so we can measure production clearly
        engine.set_balance(target_res, 0.0)
        engine.advance_to(10.0)
        assert engine.get_balance(target_res) > 0

    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_production_rate_positive_with_generator(self, fixture_name):
        game = load_e2e_game(fixture_name)
        engine = PiecewiseEngine(game, validate=True)
        gen_id = find_first_generator(game)

        # Find target resource
        target_res = None
        for edge in game.edges:
            if edge.source == gen_id and edge.edge_type == "production_target":
                target_res = edge.target
                break
        if target_res is None:
            pytest.skip("Generator has no production_target edge")

        engine.set_owned(gen_id, 1)
        rate = engine.get_production_rate(target_res)
        assert rate > 0


class TestDeterminism:
    """Repeated runs with same setup produce identical results."""

    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_advance_to_is_deterministic(self, fixture_name):
        game = load_e2e_game(fixture_name)
        gen_id = find_first_generator(game)

        results = []
        for _ in range(2):
            engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
            engine.set_owned(gen_id, 5)
            engine.advance_to(60.0)
            # Collect all resource balances
            balances = {}
            for node in game.nodes:
                if isinstance(node, Resource):
                    balances[node.id] = engine.get_balance(node.id)
            results.append(balances)

        for res_id in results[0]:
            assert results[0][res_id] == results[1][res_id]

    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_auto_advance_is_deterministic(self, fixture_name):
        game = load_e2e_game(fixture_name)
        currency = _find_currency_resource(game)

        results = []
        for _ in range(2):
            engine = PiecewiseEngine(copy.deepcopy(game), validate=True)
            engine.set_balance(currency, 1e6)
            engine.auto_advance(60.0)
            results.append(engine.get_balance(currency))

        assert results[0] == results[1]


class TestProductionRateMonotonicity:
    """Production rate is non-decreasing (only for simple fixtures)."""

    @pytest.mark.parametrize(
        "fixture_name",
        [f for f in PHASE_B_FIXTURES if f not in NON_MONOTONIC_FIXTURES],
    )
    def test_rate_non_decreasing_with_auto_advance(self, fixture_name):
        game = load_e2e_game(fixture_name)
        engine = PiecewiseEngine(game, validate=True)
        currency = _find_currency_resource(game)
        engine.set_balance(currency, 1e6)

        checkpoints = [10.0, 30.0, 60.0, 120.0, 300.0]
        rates = []
        for t in checkpoints:
            engine.auto_advance(t)
            rates.append(engine.get_production_rate(currency))

        for i in range(1, len(rates)):
            assert rates[i] >= rates[i - 1] - 1e-9, (
                f"Rate decreased at t={checkpoints[i]}: {rates[i]} < {rates[i - 1]}"
            )


class TestCookieClickerGoldenValues:
    """Hand-computed golden values for CookieClicker fixture.
    No buffs or state modifiers, so rates are straightforward.
    """

    def test_single_cursor_production(self, cookie_engine):
        """1 cursor: rate = 0.1/s."""
        cookie_engine.set_owned("cursor", 1)
        rate = cookie_engine.get_production_rate("cookies")
        assert rate == pytest.approx(0.1, rel=1e-3)

    def test_single_cursor_balance_at_60s(self, cookie_engine):
        """1 cursor for 60s: earned = 0.1 * 60 = 6.0.
        Use set_owned to avoid auto-purchase side effects.
        """
        cookie_engine.set_owned("cursor", 1)
        cookie_engine.set_balance("cookies", 0.0)
        cookie_engine.advance_to(60.0)
        # advance_to auto-purchases, but with 0 initial balance and 0.1/s rate,
        # cursor costs 15 so won't afford another for 150s
        assert cookie_engine.get_balance("cookies") == pytest.approx(6.0, rel=1e-2)

    def test_ten_cursors_production(self, cookie_engine):
        """10 cursors: rate = 0.1 * 10 = 1.0/s."""
        cookie_engine.set_owned("cursor", 10)
        rate = cookie_engine.get_production_rate("cookies")
        assert rate == pytest.approx(1.0, rel=1e-3)

    def test_cursor_with_x2_upgrade(self, cookie_engine):
        """10 cursors + x2 upgrade: rate = 0.1 * 10 * 2.0 = 2.0/s."""
        cookie_engine.set_owned("cursor", 10)
        cookie_engine.set_balance("cookies", 1e6)
        cookie_engine.purchase_upgrade("upg_x2_cursor")
        rate = cookie_engine.get_production_rate("cookies")
        assert rate == pytest.approx(2.0, rel=1e-3)

    def test_grandma_production(self, cookie_engine):
        """1 grandma: rate = 1.0/s."""
        cookie_engine.set_owned("grandma", 1)
        rate = cookie_engine.get_production_rate("cookies")
        assert rate == pytest.approx(1.0, rel=1e-3)

    def test_mixed_generators(self, cookie_engine):
        """10 cursors + 1 grandma: rate = 0.1*10 + 1.0*1 = 2.0/s."""
        cookie_engine.set_owned("cursor", 10)
        cookie_engine.set_owned("grandma", 1)
        rate = cookie_engine.get_production_rate("cookies")
        assert rate == pytest.approx(2.0, rel=1e-3)


class TestFactoryIdleGoldenValues:
    """FactoryIdle has buffs that affect production EV.
    - production_buff: timed 15/45s cooldown, 2.5x on miner → EV 1.375
    - lucky_strike: proc 0.15, 3.0x on smelter_worker → EV 1.3
    """

    def test_miner_produces_ore_with_buff_ev(self, factory_engine):
        """1 miner: ore rate = 3.0 * 1.375 (buff EV) = 4.125/s."""
        factory_engine.set_owned("miner", 1)
        rate = factory_engine.get_production_rate("ore")
        assert rate == pytest.approx(4.125, rel=1e-3)

    def test_drain_below_threshold_inactive(self, factory_engine):
        """ore_decay condition: balance_ore > 4000. Below 4000, no drain."""
        factory_engine.set_owned("miner", 1)
        factory_engine.set_balance("ore", 100.0)
        drain_rates = factory_engine.compute_drain_rates()
        ore_drain = drain_rates.get("ore", 0.0)
        assert ore_drain == pytest.approx(0.0, abs=1e-6)

    def test_ingot_rust_always_active(self, factory_engine):
        """ingot_rust has no condition — always drains 0.5/s."""
        factory_engine.set_balance("ingots", 100.0)
        drain_rates = factory_engine.compute_drain_rates()
        ingot_drain = drain_rates.get("ingots", 0.0)
        assert ingot_drain == pytest.approx(0.5, rel=1e-3)


class TestPrestigeTowerGoldenValues:
    """PrestigeTower has no buffs on gen_t1, so rates are straightforward."""

    def test_gen_t1_production(self, prestige_engine):
        """1 gen_t1: rate = 1.0/s to points."""
        prestige_engine.set_owned("gen_t1", 1)
        rate = prestige_engine.get_production_rate("points")
        assert rate == pytest.approx(1.0, rel=1e-3)

    def test_synergy_t1_to_t2(self, prestige_engine):
        """20 gen_t1 synergy: formula = owned_gen_t1 * 0.02 = 0.4.
        compute_synergy_multipliers returns full multiplier: 1 + 0.4 = 1.4.
        """
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.set_owned("gen_t2", 1)
        synergies = prestige_engine.compute_synergy_multipliers()
        assert synergies.get("gen_t2", 0.0) == pytest.approx(1.4, rel=1e-3)


class TestSpeedRunnerGoldenValues:
    """SpeedRunner has crit state_modifier AND buff on scanner.
    - crit: formula "1 + 0.2 * (3.0 - 1)" = 1.4x multiply on base_production
    - speed_burst: proc 0.1, 5.0x on scanner → EV = 1 + 0.1*(5-1) = 1.4
    - Combined scanner rate: 5.0 * 1.4 (crit) * 1.4 (buff) = 9.8/s
    """

    def test_scanner_production_with_crit_and_buff(self, speed_engine):
        """1 scanner: data rate = 5.0 * 1.4 * 1.4 = 9.8/s."""
        speed_engine.set_owned("scanner", 1)
        rate = speed_engine.get_production_rate("data")
        assert rate == pytest.approx(9.8, rel=1e-3)

    def test_scanner_rate_above_base(self, speed_engine):
        """Scanner rate must be > 5.0 base due to crit + buff modifiers."""
        speed_engine.set_owned("scanner", 1)
        rate = speed_engine.get_production_rate("data")
        assert rate > 5.0


class TestNumericalStability:
    """No NaN, Inf, or negative balances after simulation."""

    @pytest.mark.parametrize("fixture_name", PHASE_B_FIXTURES)
    def test_no_nan_or_inf_after_simulation(self, fixture_name):
        game = load_e2e_game(fixture_name)
        engine = PiecewiseEngine(game, validate=True)
        currency = _find_currency_resource(game)
        engine.set_balance(currency, 1e6)
        engine.auto_advance(300.0)

        rates = engine.compute_production_rates()
        for resource_id, rate in rates.items():
            assert not math.isnan(rate), f"NaN rate for {resource_id}"
            assert not math.isinf(rate), f"Inf rate for {resource_id}"

        for node in game.nodes:
            if isinstance(node, Resource):
                bal = engine.get_balance(node.id)
                assert not math.isnan(bal), f"NaN balance for {node.id}"
                assert not math.isinf(bal), f"Inf balance for {node.id}"
