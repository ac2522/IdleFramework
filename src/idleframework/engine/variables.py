"""Variable name sanitization and state variable building for formula evaluation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState


def sanitize_var_name(node_id: str) -> str:
    """Sanitize a node ID into a valid Python identifier for formula variables."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", node_id)


def build_state_variables(game: GameDefinition, state: GameState) -> dict[str, float]:
    """Build the variable namespace for formula evaluation from current game state.

    Variables:
    - owned_<node_id>: owned count
    - balance_<resource_id>: current value
    - level_<node_id>: level
    - lifetime_<resource_id>: lifetime earnings
    - total_production_<node_id>: total production
    - elapsed_time, run_time
    """
    from idleframework.model.nodes import Resource

    variables: dict[str, float] = {
        "elapsed_time": state.elapsed_time,
        "run_time": state.run_time,
    }

    for node in game.nodes:
        sid = sanitize_var_name(node.id)
        ns = state.get(node.id)
        variables[f"owned_{sid}"] = float(ns.owned)
        variables[f"level_{sid}"] = float(ns.level)
        variables[f"total_production_{sid}"] = ns.total_production

        if isinstance(node, Resource):
            variables[f"balance_{sid}"] = ns.current_value

    total_lifetime = 0.0
    for res_id, amount in state.lifetime_earnings.items():
        sid = sanitize_var_name(res_id)
        variables[f"lifetime_{sid}"] = amount
        total_lifetime += amount

    # Aggregate alias used by AdCap-style formulas (e.g. "lifetime_earnings")
    variables["lifetime_earnings"] = total_lifetime

    return variables
