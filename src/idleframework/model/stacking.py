"""Stacking group multiplier computation.

Formula:
  additive:       group_mult = 1 + sum(bonuses)
  multiplicative: group_mult = product(bonuses)
  percentage:     group_mult = 1 + sum(pcts) / 100
  Between groups: final = product(all group_mults)
"""
from __future__ import annotations

import math


def compute_final_multiplier(groups: dict[str, dict]) -> float:
    """Compute final multiplier from stacking groups.

    Args:
        groups: {"group_name": {"rule": "additive|multiplicative|percentage", "bonuses": [float, ...]}}

    Returns:
        Final multiplier (product of all group multipliers).
    """
    if not groups:
        return 1.0

    final = 1.0
    for group_name, group_data in groups.items():
        rule = group_data["rule"]
        bonuses = group_data["bonuses"]

        if rule == "additive":
            group_mult = 1.0 + sum(bonuses)
        elif rule == "multiplicative":
            group_mult = math.prod(bonuses) if bonuses else 1.0
        elif rule == "percentage":
            group_mult = 1.0 + sum(bonuses) / 100.0
        else:
            raise ValueError(f"Unknown stacking rule '{rule}' in group '{group_name}'")

        final *= group_mult

    return final
