"""Evaluate state_modifier edges to compute modified node properties."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from typing import TYPE_CHECKING

from idleframework.dsl.compiler import compile_formula, evaluate_formula
from idleframework.engine.variables import build_state_variables, sanitize_var_name

if TYPE_CHECKING:
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState


@dataclass
class PropertyModification:
    """A resolved modification to a node property."""
    value: float
    mode: str  # "set", "add", "multiply"


def evaluate_state_edges(
    game: GameDefinition,
    state: GameState,
) -> dict[str, dict[str, list[PropertyModification]]]:
    """Evaluate all state_modifier edges and return modifications per node per property.

    Returns: {node_id: {property_name: [PropertyModification, ...]}}
    """
    variables = build_state_variables(game, state)
    modified: dict[str, dict[str, list[PropertyModification]]] = {}

    # Collect and topologically sort state_modifier edges
    sm_edges = [e for e in game.edges if e.edge_type == "state_modifier" and e.formula]
    sm_edges = _topological_sort_edges(sm_edges, game)

    for edge in sm_edges:
        compiled = compile_formula(edge.formula)
        result = float(evaluate_formula(compiled, variables))

        target_id = edge.target
        prop = edge.target_property
        mode = edge.modifier_mode or "multiply"  # backward compat default

        if target_id not in modified:
            modified[target_id] = {}

        if prop is None:
            prop = "_general_multiplier"

        if prop not in modified[target_id]:
            modified[target_id][prop] = []
        modified[target_id][prop].append(PropertyModification(value=result, mode=mode))

    return modified


def apply_property_modifications(
    base_value: float,
    mods: list[PropertyModification],
) -> float:
    """Apply a list of property modifications to a base value.

    Order: set overrides first, then multiply, then add.
    """
    result = base_value

    # Apply set first (last set wins)
    for mod in mods:
        if mod.mode == "set":
            result = mod.value

    # Apply multipliers
    for mod in mods:
        if mod.mode == "multiply":
            result *= mod.value

    # Apply additives
    for mod in mods:
        if mod.mode == "add":
            result += mod.value

    return result


def _topological_sort_edges(edges, game):
    """Topological sort of state_modifier edges by dependency.

    Uses Kahn's algorithm. Edge A depends on edge B if A's formula
    references a variable derived from B's target node.
    """
    if not edges:
        return edges

    # Build variable prefixes each edge's target produces
    edge_targets = {}
    for e in edges:
        sid = sanitize_var_name(e.target)
        edge_targets[e.id] = {f"owned_{sid}", f"balance_{sid}", f"level_{sid}",
                              f"total_production_{sid}", f"lifetime_{sid}"}

    # Build adjacency: edge A depends on edge B if A's formula contains
    # any variable that B's target produces
    deps = defaultdict(set)  # edge_id -> set of edge_ids it depends on
    edge_map = {e.id: e for e in edges}

    for e in edges:
        if not e.formula:
            continue
        for other in edges:
            if other.id == e.id:
                continue
            for var in edge_targets.get(other.id, set()):
                if var in e.formula:
                    deps[e.id].add(other.id)

    # Kahn's algorithm
    in_degree = {e.id: len(deps[e.id]) for e in edges}
    queue = [e for e in edges if in_degree[e.id] == 0]
    result = []
    visited = set()

    while queue:
        e = queue.pop(0)
        if e.id in visited:
            continue
        visited.add(e.id)
        result.append(e)
        for other in edges:
            if e.id in deps[other.id]:
                deps[other.id].discard(e.id)
                in_degree[other.id] -= 1
                if in_degree[other.id] == 0:
                    queue.append(other)

    # Detect cycles
    if len(result) != len(edges):
        cycle_edges = [e.id for e in edges if e.id not in visited]
        raise ValueError(f"Cycle detected in state_modifier edges: {cycle_edges}")

    return result
