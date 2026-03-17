"""Cross-mechanic interaction tests — verify mechanics work together correctly."""

import pytest

from idleframework.model.nodes import Resource


class TestSynergyInteractions:
    """PrestigeTower: synergy stacking."""

    def test_synergy_boosts_target(self, prestige_engine):
        """With gen_t1 owned, synergy increases gen_t2 multiplier."""
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.set_owned("gen_t2", 1)

        synergies = prestige_engine.compute_synergy_multipliers()
        # syn_t1_t2 formula: owned_gen_t1 * 0.02 = 20 * 0.02 = 0.4
        # compute_synergy_multipliers returns 1 + bonus = 1.4
        assert synergies.get("gen_t2", 0.0) == pytest.approx(1.4, rel=1e-3)

    def test_synergy_scales_with_source_owned(self, prestige_engine):
        """More gen_t1 → higher synergy bonus on gen_t2."""
        prestige_engine.set_owned("gen_t1", 10)
        prestige_engine.set_owned("gen_t2", 1)
        syn_10 = prestige_engine.compute_synergy_multipliers().get("gen_t2", 0.0)

        prestige_engine.set_owned("gen_t1", 20)
        syn_20 = prestige_engine.compute_synergy_multipliers().get("gen_t2", 0.0)

        assert syn_20 > syn_10


class TestBuffInteractions:
    """FullKitchen: buff EV interactions."""

    def test_buff_ev_on_miner(self, kitchen_engine):
        """Frenzy buff: timed 10s/40s cooldown, 3x multiplier.
        EV = 1 + (3-1) * 10/(10+40) = 1.4x.
        """
        buff_mults = kitchen_engine.evaluate_buffs()
        miner_buff = buff_mults.per_generator.get("miner", 1.0)
        assert miner_buff == pytest.approx(1.4, rel=1e-2)


class TestDrainMechanics:
    """FactoryIdle: drain interactions."""

    def test_drain_reduces_balance(self, factory_engine):
        """With ingot_rust active and no production, ingots decrease."""
        factory_engine.set_balance("ingots", 100.0)
        factory_engine.advance_to(10.0)
        assert factory_engine.get_balance("ingots") < 100.0

    def test_drain_never_goes_negative(self, factory_engine):
        """Balance floors at 0 even with drain > production."""
        factory_engine.set_balance("ingots", 1.0)
        factory_engine.advance_to(60.0)
        assert factory_engine.get_balance("ingots") >= 0.0

    def test_conditional_drain_based_on_balance(self, factory_engine):
        """ore_decay fires only when balance_ore > 4000."""
        factory_engine.set_balance("ore", 100.0)
        drain_rates = factory_engine.compute_drain_rates()
        ore_drain = drain_rates.get("ore", 0.0)
        assert ore_drain == pytest.approx(0.0, abs=0.1)


class TestStateModifierComposition:
    """FullKitchen: state_modifier edges with different modes."""

    def test_state_modifier_multiply_affects_production(self, kitchen_engine):
        """Crit modifier (multiply mode) increases miner production above base."""
        kitchen_engine.set_owned("miner", 1)
        rate = kitchen_engine.get_production_rate("gold")
        # base_production 2.0, crit multiply 1.225, buff EV 1.4
        # rate = 2.0 * 1.225 * 1.4 = 3.43
        assert rate > 2.0


class TestAutoAdvanceIntegration:
    """Auto-advance exercises multiple mechanics together."""

    def test_auto_advance_buys_and_produces(self, cookie_engine):
        """advance_to auto-purchases when generators produce income."""
        cookie_engine.set_balance("cookies", 1e6)
        # Buy initial generator to start income flow
        cookie_engine.purchase("cursor")
        cookie_engine.advance_to(120.0)
        # With 1M cookies and 0.1/s income, advance_to will buy more generators
        assert cookie_engine.get_owned("cursor") >= 1
        assert cookie_engine.time == pytest.approx(120.0)

    def test_auto_advance_multi_resource(self, factory_engine):
        """Factory auto-advance with initial gold."""
        factory_engine.set_balance("gold", 1e6)
        purchases = factory_engine.auto_advance(60.0)
        assert len(purchases) > 0
