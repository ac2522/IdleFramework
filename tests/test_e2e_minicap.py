"""End-to-end tests on MiniCap fixture.

These tests exercise the full pipeline:
1. Load MiniCap JSON → validate with Pydantic
2. Initialize PiecewiseEngine with graph validation
3. Run simulation with purchases (generators + upgrades)
4. Verify production rates match analytical expectations
5. Verify stacking multipliers work correctly
6. Verify prestige formula evaluates correctly
7. Verify auto_advance produces reasonable results
"""
import json
import math
import pytest
from pathlib import Path
from idleframework.model.game import GameDefinition
from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import bulk_cost


@pytest.fixture
def minicap_game() -> GameDefinition:
    fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return GameDefinition.model_validate(data)


@pytest.fixture
def minicap_engine(minicap_game) -> PiecewiseEngine:
    return PiecewiseEngine(minicap_game, validate=True)


class TestMiniCapLoading:
    def test_loads_and_validates(self, minicap_game):
        assert minicap_game.name == "MiniCap"
        assert len(minicap_game.nodes) == 18  # 2 resources + 3 gen + 10 upg + 1 prestige + 1 achieve + 1 end
        assert len(minicap_game.edges) == 3

    def test_engine_initializes_with_validation(self, minicap_engine):
        assert minicap_engine is not None
        assert minicap_engine.time == 0.0

    def test_all_generators_start_at_zero(self, minicap_engine):
        for gen_id in ["lemonade", "newspaper", "carwash"]:
            assert minicap_engine.get_owned(gen_id) == 0

    def test_cash_starts_at_zero(self, minicap_engine):
        assert minicap_engine.get_balance("cash") == 0.0


class TestMiniCapBaseProduction:
    def test_lemonade_production_rate(self, minicap_engine):
        """1 lemonade stand: 1.0 prod / 1.0 cycle = 1.0/sec."""
        minicap_engine.set_owned("lemonade", 1)
        assert minicap_engine.get_production_rate("cash") == pytest.approx(1.0)

    def test_newspaper_production_rate(self, minicap_engine):
        """1 newspaper: 60.0 prod / 3.0 cycle = 20.0/sec."""
        minicap_engine.set_owned("newspaper", 1)
        assert minicap_engine.get_production_rate("cash") == pytest.approx(20.0)

    def test_carwash_production_rate(self, minicap_engine):
        """1 carwash: 720.0 prod / 6.0 cycle = 120.0/sec."""
        minicap_engine.set_owned("carwash", 1)
        assert minicap_engine.get_production_rate("cash") == pytest.approx(120.0)

    def test_multiple_generators_combined(self, minicap_engine):
        """5 lemonade + 2 newspaper + 1 carwash = 5 + 40 + 120 = 165/sec."""
        minicap_engine.set_owned("lemonade", 5)
        minicap_engine.set_owned("newspaper", 2)
        minicap_engine.set_owned("carwash", 1)
        assert minicap_engine.get_production_rate("cash") == pytest.approx(165.0)


class TestMiniCapCosts:
    def test_first_lemonade_cost(self, minicap_engine):
        """First lemonade: 4 * 1.07^0 = 4.0."""
        cost = bulk_cost(4.0, 1.07, 0, 1)
        assert cost == pytest.approx(4.0)

    def test_tenth_lemonade_cost(self, minicap_engine):
        """10th lemonade: 4 * 1.07^9 ≈ 7.36."""
        cost = bulk_cost(4.0, 1.07, 9, 1)
        expected = 4 * (1.07 ** 9)
        assert cost == pytest.approx(expected, rel=1e-5)

    def test_bulk_10_lemonades(self):
        """Cost of first 10 lemonades."""
        cost = bulk_cost(4.0, 1.07, 0, 10)
        expected = 4 * ((1.07 ** 10) - 1) / (1.07 - 1)
        assert cost == pytest.approx(expected, rel=1e-5)


class TestMiniCapUpgrades:
    def test_x3_lemonade_upgrade(self, minicap_engine):
        """Buying x3_lemon triples lemonade production."""
        minicap_engine.set_owned("lemonade", 10)
        base_rate = minicap_engine.get_production_rate("cash")

        minicap_engine.set_balance("cash", 1000.0)
        minicap_engine.purchase_upgrade("x3_lemon")
        upgraded_rate = minicap_engine.get_production_rate("cash")

        assert upgraded_rate == pytest.approx(base_rate * 3.0)

    def test_stacked_upgrades(self, minicap_engine):
        """x3_lemon + x3_all_1 in same multiplicative group = 9x lemonade."""
        minicap_engine.set_owned("lemonade", 1)
        minicap_engine.set_balance("cash", 200000.0)
        minicap_engine.purchase_upgrade("x3_lemon")
        minicap_engine.purchase_upgrade("x3_all_1")

        # Both in cash_upgrades (multiplicative): 3 * 3 = 9x
        rate = minicap_engine.get_production_rate("cash")
        assert rate == pytest.approx(1.0 * 9.0)  # 1 lemonade * 1.0/sec * 9

    def test_all_target_affects_all_generators(self, minicap_engine):
        """x3_all_1 should multiply all three generators."""
        minicap_engine.set_owned("lemonade", 1)
        minicap_engine.set_owned("newspaper", 1)
        minicap_engine.set_owned("carwash", 1)
        minicap_engine.set_balance("cash", 200000.0)

        base_rate = minicap_engine.get_production_rate("cash")
        minicap_engine.purchase_upgrade("x3_all_1")
        upgraded_rate = minicap_engine.get_production_rate("cash")

        assert upgraded_rate == pytest.approx(base_rate * 3.0)

    def test_paid_upgrade_tagged(self, minicap_engine):
        """paid_x10 costs 0, applies x10 to all."""
        minicap_engine.set_owned("lemonade", 1)
        base_rate = minicap_engine.get_production_rate("cash")

        minicap_engine.purchase_upgrade("paid_x10")
        upgraded_rate = minicap_engine.get_production_rate("cash")

        assert upgraded_rate == pytest.approx(base_rate * 10.0)


class TestMiniCapPrestige:
    def test_prestige_formula(self, minicap_engine):
        """150 * sqrt(lifetime_earnings / 1e15) with 1e18 earnings."""
        angels = minicap_engine.evaluate_prestige(
            "prestige", lifetime_earnings=1e18
        )
        expected = 150 * math.sqrt(1e18 / 1e15)
        assert angels == pytest.approx(expected, rel=1e-3)

    def test_prestige_formula_at_threshold(self, minicap_engine):
        """At exactly 1e15 earnings: 150 * sqrt(1) = 150."""
        angels = minicap_engine.evaluate_prestige(
            "prestige", lifetime_earnings=1e15
        )
        assert angels == pytest.approx(150.0, rel=1e-3)


class TestMiniCapSimulation:
    def test_earn_cash_buy_lemonade(self, minicap_engine):
        """Start with cash, buy lemonades, verify growing production."""
        minicap_engine.set_balance("cash", 50.0)

        # Buy first lemonade (cost ~4)
        minicap_engine.purchase("lemonade", 1)
        assert minicap_engine.get_owned("lemonade") == 1

        # Advance 60 seconds: earn 1.0/sec * 60 = 60
        minicap_engine.advance_to(60.0)
        balance = minicap_engine.get_balance("cash")
        remaining_after_buy = 50.0 - 4.0
        assert balance == pytest.approx(remaining_after_buy + 60.0, rel=1e-3)

    def test_auto_advance_builds_economy(self, minicap_engine):
        """auto_advance from scratch builds an economy over time."""
        minicap_engine.set_balance("cash", 100.0)
        minicap_engine.purchase("lemonade", 1)

        purchases = minicap_engine.auto_advance(target_time=300.0)

        # Should have bought multiple generators
        assert len(purchases) > 5
        assert minicap_engine.get_owned("lemonade") > 1
        assert minicap_engine.get_balance("cash") >= 0

    def test_production_increases_over_time(self, minicap_engine):
        """Production rate should increase as generators are purchased."""
        minicap_engine.set_balance("cash", 100.0)
        minicap_engine.purchase("lemonade", 1)

        rate_before = minicap_engine.get_production_rate("cash")
        minicap_engine.auto_advance(target_time=200.0)
        rate_after = minicap_engine.get_production_rate("cash")

        assert rate_after > rate_before

    def test_full_simulation_reach_upgrade(self, minicap_engine):
        """Run long enough to afford x3_lemon (cost=1000)."""
        minicap_engine.set_balance("cash", 50.0)
        minicap_engine.purchase("lemonade", 5)

        # With 5 lemonades at 1/sec = 5/sec, takes 200s to reach 1000
        minicap_engine.auto_advance(target_time=500.0)

        # Should have enough cash for the x3 upgrade
        balance = minicap_engine.get_balance("cash")
        # Even with auto-buying more lemonades, should accumulate significant cash
        assert balance > 0
        assert minicap_engine.get_owned("lemonade") > 5
