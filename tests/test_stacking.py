"""Stacking group calculation tests.

Formula:
  additive group: group_mult = 1 + sum(bonuses)
  multiplicative group: group_mult = product(bonuses)
  percentage group: group_mult = 1 + sum(pcts/100)
  final = base * product(all_group_mults)

Reference: AdCap stacking model.
"""
import pytest
from idleframework.model.stacking import compute_final_multiplier


class TestStackingGroups:
    def test_single_multiplicative_group(self):
        groups = {
            "cash_upgrades": {"rule": "multiplicative", "bonuses": [3.0, 2.0, 5.0]},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(30.0)  # 3 * 2 * 5

    def test_single_additive_group(self):
        groups = {
            "angel_bonus": {"rule": "additive", "bonuses": [0.02, 0.02, 0.02]},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(1.06)  # 1 + 0.02 + 0.02 + 0.02

    def test_single_percentage_group(self):
        groups = {
            "gems": {"rule": "percentage", "bonuses": [10, 20, 5]},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(1.35)  # 1 + (10+20+5)/100

    def test_adcap_multi_group(self):
        """AdCap: final = base * (1 + angels*0.02) * product(cash) * product(angel_upg) * product(milestones)"""
        groups = {
            "angel_bonus": {"rule": "additive", "bonuses": [0.02] * 100},  # 100 angels * 2%
            "cash_upgrades": {"rule": "multiplicative", "bonuses": [3.0, 3.0]},
            "angel_upgrades": {"rule": "multiplicative", "bonuses": [7.77]},
            "milestones": {"rule": "multiplicative", "bonuses": [2.0, 3.0]},
        }
        result = compute_final_multiplier(groups)
        # (1 + 2.0) * 9.0 * 7.77 * 6.0 = 3 * 9 * 7.77 * 6 = 1258.74
        expected = (1 + 100 * 0.02) * (3.0 * 3.0) * 7.77 * (2.0 * 3.0)
        assert result == pytest.approx(expected, rel=1e-5)

    def test_empty_group(self):
        groups = {
            "empty_mult": {"rule": "multiplicative", "bonuses": []},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(1.0)  # Identity

    def test_no_groups(self):
        result = compute_final_multiplier({})
        assert result == pytest.approx(1.0)

    def test_additive_gold_mults(self):
        """AdCap gold multipliers: x12 + x12 = x24, NOT x144."""
        groups = {
            "gold_mults": {"rule": "additive", "bonuses": [12, 12]},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(25.0)  # 1 + 12 + 12
