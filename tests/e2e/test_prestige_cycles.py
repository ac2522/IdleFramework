"""Prestige cycle tests — verify reset, currency, bonus, and replay mechanics."""

import copy

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.variables import build_state_variables


class TestSinglePrestigeCycle:
    def test_prestige_resets_generators(self, prestige_engine):
        """After prestige, generators in reset_scope have owned=0."""
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.advance_to(300.0)

        prestige_engine.execute_prestige("prestige_1")

        assert prestige_engine.get_owned("gen_t1") == 0
        assert prestige_engine.get_owned("gen_t2") == 0

    def test_prestige_grants_currency(self, prestige_engine):
        """After prestige with lifetime earnings, prestige currency > 0."""
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.advance_to(600.0)

        prestige_engine.execute_prestige("prestige_1")

        p1_balance = prestige_engine.get_balance("p1_currency")
        assert p1_balance > 0

    def test_prestige_currency_persists(self, prestige_engine):
        """p1_currency is in persistence_scope — not reset."""
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.advance_to(600.0)

        prestige_engine.execute_prestige("prestige_1")
        p1_after = prestige_engine.get_balance("p1_currency")

        # Owning generators after prestige shouldn't affect p1
        prestige_engine.set_owned("gen_t1", 10)
        assert prestige_engine.get_balance("p1_currency") == pytest.approx(p1_after)

    def test_replay_after_prestige(self, prestige_engine):
        """After prestige, can set generators and produce again."""
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.advance_to(300.0)

        prestige_engine.execute_prestige("prestige_1")

        # Set generators and produce
        prestige_engine.set_owned("gen_t1", 5)
        prestige_engine.advance_to(prestige_engine.time + 60.0)
        assert prestige_engine.get_balance("points") > 0


class TestPrestigeFormula:
    def test_prestige_gain_scales_with_earnings(self, prestige_game):
        """More lifetime earnings → more prestige points.
        Formula: floor(sqrt(lifetime_points))
        """
        # Run 1: short play
        engine1 = PiecewiseEngine(copy.deepcopy(prestige_game), validate=True)
        engine1.set_owned("gen_t1", 10)
        engine1.advance_to(60.0)
        vars1 = build_state_variables(prestige_game, engine1.state)
        gain1 = engine1.evaluate_prestige("prestige_1", **vars1)

        # Run 2: longer play
        engine2 = PiecewiseEngine(copy.deepcopy(prestige_game), validate=True)
        engine2.set_owned("gen_t1", 10)
        engine2.advance_to(600.0)
        vars2 = build_state_variables(prestige_game, engine2.state)
        gain2 = engine2.evaluate_prestige("prestige_1", **vars2)

        assert gain2 > gain1


class TestMultiLayerPrestige:
    def test_layer2_resets_layer1_currency(self, prestige_engine):
        """Layer 2 reset_scope includes p1_currency."""
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.advance_to(600.0)

        # Prestige layer 1 several times to accumulate p1_currency
        for _ in range(3):
            prestige_engine.execute_prestige("prestige_1")
            prestige_engine.set_owned("gen_t1", 20)
            prestige_engine.advance_to(prestige_engine.time + 300.0)

        p1_before = prestige_engine.get_balance("p1_currency")
        assert p1_before > 0

        # Now prestige layer 2
        prestige_engine.execute_prestige("prestige_2")

        # p1_currency should be reset (it's in prestige_2's reset_scope)
        assert prestige_engine.get_balance("p1_currency") == 0
        # p2_currency should be gained
        assert prestige_engine.get_balance("p2_currency") > 0

    def test_layer2_preserves_own_persistence(self, prestige_engine):
        """p2_currency and p3_currency are in layer 2's persistence_scope."""
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.advance_to(600.0)

        # Build up p1_currency
        for _ in range(3):
            prestige_engine.execute_prestige("prestige_1")
            prestige_engine.set_owned("gen_t1", 20)
            prestige_engine.advance_to(prestige_engine.time + 300.0)

        prestige_engine.execute_prestige("prestige_2")
        p2 = prestige_engine.get_balance("p2_currency")

        # p2 should persist through subsequent layer 1 prestiges
        prestige_engine.set_owned("gen_t1", 20)
        prestige_engine.advance_to(prestige_engine.time + 300.0)
        prestige_engine.execute_prestige("prestige_1")

        assert prestige_engine.get_balance("p2_currency") == pytest.approx(p2)
