"""Tests for engine upgrade purchasing and stacking group integration.

These tests verify that the PiecewiseEngine correctly:
1. Tracks upgrade ownership (purchased = True, not a count)
2. Applies upgrade multipliers via stacking groups to production rates
3. Handles _all target upgrades (apply to every generator)
4. Handles per-generator target upgrades
5. Computes effective production = base * count / cycle * stacking_multiplier
"""
import pytest
from idleframework.model.game import GameDefinition
from idleframework.engine.segments import PiecewiseEngine


def _make_upgrade_game():
    """Game with 1 generator, 2 upgrades in same stacking group."""
    return GameDefinition(
        schema_version="1.0",
        name="UpgradeTest",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "miner", "type": "generator", "name": "Miner",
             "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
            {"id": "x3_miner", "type": "upgrade", "name": "x3 Miner",
             "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 500.0,
             "target": "miner", "stacking_group": "cash_upgrades"},
            {"id": "x2_miner", "type": "upgrade", "name": "x2 Miner",
             "upgrade_type": "multiplicative", "magnitude": 2.0, "cost": 1000.0,
             "target": "miner", "stacking_group": "cash_upgrades"},
        ],
        edges=[
            {"id": "e1", "source": "miner", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={"cash_upgrades": "multiplicative"},
    )


def _make_all_target_game():
    """Game with 2 generators and an _all upgrade."""
    return GameDefinition(
        schema_version="1.0",
        name="AllTargetTest",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "miner", "type": "generator", "name": "Miner",
             "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
            {"id": "factory", "type": "generator", "name": "Factory",
             "base_production": 50.0, "cost_base": 500.0, "cost_growth_rate": 1.15,
             "cycle_time": 2.0},
            {"id": "x3_all", "type": "upgrade", "name": "x3 All",
             "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 2000.0,
             "target": "_all", "stacking_group": "cash_upgrades"},
        ],
        edges=[
            {"id": "e1", "source": "miner", "target": "cash", "edge_type": "production_target"},
            {"id": "e2", "source": "factory", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={"cash_upgrades": "multiplicative"},
    )


def _make_multi_group_game():
    """Game with upgrades across multiple stacking groups (AdCap-style)."""
    return GameDefinition(
        schema_version="1.0",
        name="MultiGroupTest",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "miner", "type": "generator", "name": "Miner",
             "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
            {"id": "x3_miner", "type": "upgrade", "name": "x3 Cash",
             "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 500.0,
             "target": "miner", "stacking_group": "cash_upgrades"},
            {"id": "angel_x2", "type": "upgrade", "name": "Angel x2",
             "upgrade_type": "multiplicative", "magnitude": 2.0, "cost": 100.0,
             "target": "miner", "stacking_group": "angel_upgrades"},
        ],
        edges=[
            {"id": "e1", "source": "miner", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={
            "cash_upgrades": "multiplicative",
            "angel_upgrades": "multiplicative",
        },
    )


def _make_additive_group_game():
    """Game with additive stacking group (like AdCap angel bonus)."""
    return GameDefinition(
        schema_version="1.0",
        name="AdditiveTest",
        nodes=[
            {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
            {"id": "miner", "type": "generator", "name": "Miner",
             "base_production": 10.0, "cost_base": 100.0, "cost_growth_rate": 1.15,
             "cycle_time": 1.0},
            {"id": "bonus_2pct", "type": "upgrade", "name": "+2% Bonus",
             "upgrade_type": "additive", "magnitude": 0.02, "cost": 50.0,
             "target": "miner", "stacking_group": "angel_bonus"},
            {"id": "bonus_5pct", "type": "upgrade", "name": "+5% Bonus",
             "upgrade_type": "additive", "magnitude": 0.05, "cost": 100.0,
             "target": "miner", "stacking_group": "angel_bonus"},
        ],
        edges=[
            {"id": "e1", "source": "miner", "target": "cash", "edge_type": "production_target"},
        ],
        stacking_groups={"angel_bonus": "additive"},
    )


class TestUpgradePurchasing:
    def test_purchase_upgrade(self):
        """Can buy an upgrade, deducting cost from balance."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 600.0)
        engine.purchase_upgrade("x3_miner")
        assert engine.is_upgrade_owned("x3_miner")
        assert engine.get_balance("cash") == pytest.approx(100.0)

    def test_purchase_upgrade_insufficient_funds(self):
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 100.0)
        with pytest.raises(ValueError, match="[Aa]fford"):
            engine.purchase_upgrade("x3_miner")

    def test_purchase_upgrade_already_owned(self):
        """Can't buy the same upgrade twice."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_balance("cash", 2000.0)
        engine.purchase_upgrade("x3_miner")
        with pytest.raises(ValueError, match="[Aa]lready"):
            engine.purchase_upgrade("x3_miner")

    def test_purchase_unknown_upgrade(self):
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        with pytest.raises(ValueError):
            engine.purchase_upgrade("nonexistent")


class TestStackingMultipliers:
    def test_no_upgrades_base_rate(self):
        """Without upgrades, production = count * base / cycle."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        # 5 * 10.0 / 1.0 = 50.0
        assert engine.get_production_rate("cash") == pytest.approx(50.0)

    def test_single_multiplicative_upgrade(self):
        """x3 upgrade: production = count * base / cycle * 3."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        engine.set_balance("cash", 500.0)
        engine.purchase_upgrade("x3_miner")
        # 5 * 10.0 / 1.0 * 3.0 = 150.0
        assert engine.get_production_rate("cash") == pytest.approx(150.0)

    def test_two_multiplicative_upgrades_same_group(self):
        """x3 and x2 in same multiplicative group: 3 * 2 = 6x."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        engine.set_balance("cash", 2000.0)
        engine.purchase_upgrade("x3_miner")
        engine.purchase_upgrade("x2_miner")
        # 5 * 10.0 / 1.0 * (3.0 * 2.0) = 300.0
        assert engine.get_production_rate("cash") == pytest.approx(300.0)

    def test_all_target_applies_to_all_generators(self):
        """_all upgrade multiplies every generator's output."""
        game = _make_all_target_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 2)
        engine.set_owned("factory", 1)
        # Base: miner = 2*10/1 = 20, factory = 1*50/2 = 25, total = 45
        assert engine.get_production_rate("cash") == pytest.approx(45.0)

        engine.set_balance("cash", 2000.0)
        engine.purchase_upgrade("x3_all")
        # After x3_all: miner = 20*3 = 60, factory = 25*3 = 75, total = 135
        assert engine.get_production_rate("cash") == pytest.approx(135.0)

    def test_multi_group_between_groups_multiply(self):
        """Upgrades in different groups: final = product(group_mults)."""
        game = _make_multi_group_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 1)
        engine.set_balance("cash", 1000.0)
        engine.purchase_upgrade("x3_miner")   # cash_upgrades group: 3x
        engine.purchase_upgrade("angel_x2")   # angel_upgrades group: 2x
        # 1 * 10.0 / 1.0 * 3.0 * 2.0 = 60.0
        assert engine.get_production_rate("cash") == pytest.approx(60.0)

    def test_additive_group(self):
        """Additive group: group_mult = 1 + sum(bonuses)."""
        game = _make_additive_group_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 1)
        engine.set_balance("cash", 200.0)
        engine.purchase_upgrade("bonus_2pct")
        engine.purchase_upgrade("bonus_5pct")
        # additive: 1 + 0.02 + 0.05 = 1.07
        # 1 * 10.0 / 1.0 * 1.07 = 10.7
        assert engine.get_production_rate("cash") == pytest.approx(10.7)


class TestUpgradeProductionIntegration:
    def test_production_accumulates_with_upgrade(self):
        """Buy upgrade, then advance time — balance reflects multiplied rate."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        engine.set_balance("cash", 500.0)
        engine.purchase_upgrade("x3_miner")
        remaining = engine.get_balance("cash")
        engine.advance_to(10.0)
        # 5 * 10 / 1 * 3 = 150/sec, 10s = 1500, plus remaining
        assert engine.get_balance("cash") == pytest.approx(remaining + 1500.0, rel=1e-3)

    def test_upgrade_timing_matters(self):
        """Production before upgrade uses old rate, after uses new rate."""
        game = _make_upgrade_game()
        engine = PiecewiseEngine(game)
        engine.set_owned("miner", 5)
        engine.set_balance("cash", 500.0)

        # Advance 5 seconds at base rate (50/sec)
        engine.advance_to(5.0)
        balance_at_5 = engine.get_balance("cash")
        assert balance_at_5 == pytest.approx(500.0 + 250.0, rel=1e-3)

        # Buy upgrade at t=5
        engine.purchase_upgrade("x3_miner")
        balance_after_buy = engine.get_balance("cash")

        # Advance 5 more seconds at 3x rate (150/sec)
        engine.advance_to(10.0)
        assert engine.get_balance("cash") == pytest.approx(
            balance_after_buy + 750.0, rel=1e-3
        )
