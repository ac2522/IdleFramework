"""FullMechanics fixture — exercises all new Phase 5 mechanics together.

3 generators, 2 resources, 1 prestige layer, 1 tickspeed, 1 drain,
1 buff, 1 synergy, 1 autobuyer, 1 probability node, and various upgrades.
"""
from idleframework.model.nodes import (
    Resource, Generator, Upgrade, PrestigeLayer,
    TickspeedNode, AutobuyerNode, DrainNode, BuffNode,
    SynergyNode, ProbabilityNode,
)
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition


def make_fullmechanics_game() -> GameDefinition:
    nodes = [
        # Resources
        Resource(id="gold", name="Gold", initial_value=100.0),
        Resource(id="prestige_pts", name="Prestige Points"),
        Resource(id="mana", name="Mana", initial_value=50.0, capacity=500.0),

        # Generators
        Generator(id="miner", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        Generator(id="smith", name="Smith", base_production=5.0, cost_base=100, cost_growth_rate=1.15),
        Generator(id="wizard", name="Wizard", base_production=2.0, cost_base=50, cost_growth_rate=1.2),

        # Tickspeed
        TickspeedNode(id="tickspeed"),

        # Upgrades
        Upgrade(id="upg_speed", name="Speed Boost", upgrade_type="multiplicative",
                magnitude=2.0, cost=500.0, target="miner", stacking_group="speed"),
        Upgrade(id="upg_tick", name="Tick Upgrade", upgrade_type="multiplicative",
                magnitude=1.5, cost=1000.0, target="tickspeed", stacking_group="tick"),

        # Drain
        DrainNode(id="mana_drain", name="Mana Drain", rate=1.0),

        # Buff
        BuffNode(id="frenzy", name="Frenzy", buff_type="timed",
                 duration=10.0, multiplier=3.0, cooldown=50.0, target="miner"),

        # Synergy
        SynergyNode(id="syn_miner_smith", name="Miner-Smith Synergy",
                    sources=["miner"], formula_expr="owned_miner * 0.01", target="smith"),

        # Probability
        ProbabilityNode(id="crit_miner", expected_value=1.0, crit_chance=0.1, crit_multiplier=2.0),

        # Autobuyer
        AutobuyerNode(id="auto_miner", target="miner", interval=5.0),

        # Prestige
        PrestigeLayer(
            id="prestige", name="Prestige",
            formula_expr="floor(sqrt(lifetime_gold))",
            layer_index=1, reset_scope=["miner", "smith", "gold"],
            persistence_scope=["prestige_pts"],
            currency_id="prestige_pts",
        ),
    ]
    edges = [
        Edge(id="e_miner_gold", source="miner", target="gold", edge_type="production_target"),
        Edge(id="e_smith_gold", source="smith", target="gold", edge_type="production_target"),
        Edge(id="e_wizard_mana", source="wizard", target="mana", edge_type="production_target"),
        Edge(id="e_drain_mana", source="mana_drain", target="mana", edge_type="consumption"),
        Edge(id="e_crit", source="crit_miner", target="miner", edge_type="state_modifier",
             formula="1 + 0.1 * (2.0 - 1)", target_property="base_production", modifier_mode="multiply"),
    ]
    return GameDefinition(
        schema_version="1.0", name="FullMechanics",
        nodes=nodes, edges=edges,
        stacking_groups={"speed": "multiplicative", "tick": "multiplicative"},
    )
