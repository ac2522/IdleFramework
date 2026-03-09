"""Stacking group computation and bridge from GameState."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState


def compute_final_multiplier(
    groups: dict[str, dict[str, object]],
) -> float:
    """Compute the final multiplier from stacking groups.

    Each group entry: {"rule": "additive"|"multiplicative"|"percentage", "bonuses": [float, ...]}

    Rules per group:
      - additive:       group_mult = 1 + sum(bonuses)
      - multiplicative:  group_mult = product(bonuses)  (empty → 1.0)
      - percentage:      group_mult = 1 + sum(bonuses) / 100

    Between groups: final = product(all group_mults).
    Empty input → 1.0.
    """
    if not groups:
        return 1.0

    final = 1.0
    for group in groups.values():
        rule: str = group["rule"]  # type: ignore[assignment]
        bonuses: list[float] = group["bonuses"]  # type: ignore[assignment]

        if rule == "additive":
            group_mult = 1.0 + math.fsum(bonuses)
        elif rule == "multiplicative":
            group_mult = math.prod(bonuses) if bonuses else 1.0
        elif rule == "percentage":
            group_mult = 1.0 + math.fsum(bonuses) / 100.0
        else:
            raise ValueError(f"Unknown stacking rule: {rule!r}")

        final *= group_mult

    return final


def collect_stacking_bonuses(
    game: "GameDefinition",
    state: "GameState",
) -> dict[str, dict[str, object]]:
    """Build stacking-group data from a game definition and runtime state.

    Iterates over all Upgrade nodes. For each purchased upgrade, adds its
    magnitude to the appropriate stacking group (looked up from
    game.stacking_groups).

    Returns a dict ready for :func:`compute_final_multiplier`.
    """
    from idleframework.model.nodes import Upgrade

    result: dict[str, dict[str, object]] = {}

    for node in game.nodes:
        if not isinstance(node, Upgrade):
            continue

        node_state = state.get(node.id)
        if not node_state.purchased:
            continue

        sg = node.stacking_group
        rule = game.stacking_groups.get(sg)
        if rule is None:
            raise ValueError(
                f"Upgrade {node.id!r} references stacking_group {sg!r} "
                f"which is not defined in game.stacking_groups"
            )

        if sg not in result:
            result[sg] = {"rule": rule, "bonuses": []}

        result[sg]["bonuses"].append(node.magnitude)  # type: ignore[union-attr]

    return result
