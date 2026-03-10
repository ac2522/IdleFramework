"""Procedurally generated large game fixture for stress testing."""
from __future__ import annotations

from idleframework.model.game import GameDefinition


def make_largecap(
    num_generators: int = 10,
    upgrades_per_gen: int = 10,
    include_dead_upgrade: bool = True,
    include_progression_wall: bool = True,
) -> GameDefinition:
    """Generate a large game fixture with known properties."""
    nodes = [
        {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
    ]
    edges = []

    for i in range(num_generators):
        gen_id = f"gen_{i}"
        base_prod = 1.0 * (12.0 ** i)
        cost_base = 4.0 * (12.0 ** i)
        growth_rate = 1.07 + 0.01 * i
        cycle_time = 1.0 + i * 0.5

        if include_progression_wall and i == num_generators - 1:
            growth_rate = 1.50

        nodes.append({
            "id": gen_id,
            "type": "generator",
            "name": f"Generator {i}",
            "base_production": base_prod,
            "cost_base": cost_base,
            "cost_growth_rate": growth_rate,
            "cycle_time": cycle_time,
        })
        edges.append({
            "id": f"e_{gen_id}",
            "source": gen_id,
            "target": "cash",
            "edge_type": "production_target",
        })

    for i in range(num_generators):
        gen_id = f"gen_{i}"
        for j in range(upgrades_per_gen):
            upg_id = f"upg_{i}_{j}"
            magnitude = 3.0
            cost = 100.0 * (10.0 ** j) * (12.0 ** i)
            nodes.append({
                "id": upg_id,
                "type": "upgrade",
                "name": f"x3 Gen{i} #{j}",
                "upgrade_type": "multiplicative",
                "magnitude": magnitude,
                "cost": cost,
                "target": gen_id,
                "stacking_group": "cash_upgrades",
            })

    if include_dead_upgrade:
        nodes.append({
            "id": "dead_upgrade",
            "type": "upgrade",
            "name": "Overpriced x1.001",
            "upgrade_type": "multiplicative",
            "magnitude": 1.001,
            "cost": 1e30,
            "target": "gen_0",
            "stacking_group": "cash_upgrades",
        })

    return GameDefinition(
        schema_version="1.0",
        name="LargeCap",
        nodes=nodes,
        edges=edges,
        stacking_groups={"cash_upgrades": "multiplicative"},
    )
