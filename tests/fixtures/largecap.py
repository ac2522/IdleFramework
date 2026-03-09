"""Procedurally generated large game fixture for stress testing.

Generates a game with configurable number of generators and upgrades
with known properties for testing analysis detectors.
"""
from __future__ import annotations

from idleframework.model.game import GameDefinition


def make_largecap(
    num_generators: int = 10,
    upgrades_per_gen: int = 10,
    include_dead_upgrade: bool = True,
    include_progression_wall: bool = True,
) -> GameDefinition:
    """Generate a large game fixture with known properties.

    Args:
        num_generators: Number of generators to create
        upgrades_per_gen: Number of upgrades per generator
        include_dead_upgrade: Add an intentionally overpriced upgrade
        include_progression_wall: Add a generator with very high cost growth
    """
    nodes = [
        {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
    ]
    edges = []

    # Generators with exponentially increasing base stats
    for i in range(num_generators):
        gen_id = f"gen_{i}"
        base_prod = 1.0 * (12.0 ** i)
        cost_base = 4.0 * (12.0 ** i)
        growth_rate = 1.07 + 0.01 * i  # 1.07 to 1.16
        cycle_time = 1.0 + i * 0.5

        if include_progression_wall and i == num_generators - 1:
            # Last generator has absurd cost growth — progression wall
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

    # Upgrades per generator
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

    # Dead upgrade: costs 1e30, gives only 1.001x to gen_0
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
