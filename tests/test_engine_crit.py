"""Tests for ProbabilityNode crit integration into production rates."""
import pytest
from idleframework.model.nodes import Resource, Generator, ProbabilityNode
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def test_crit_modifies_production():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
            ProbabilityNode(id="prob1", expected_value=1.0, crit_chance=0.2, crit_multiplier=3.0),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="prob1", target="gen1", edge_type="state_modifier",
                 formula="1 + 0.2 * (3 - 1)", target_property="base_production", modifier_mode="multiply"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    # crit_ev = 1 + 0.2 * (3-1) = 1.4
    # rate = 10 * 1 * 1.4 = 14.0
    assert rates["gold"] == pytest.approx(14.0)


def test_no_state_modifier_no_change():
    """Without state modifier edges, production is unchanged."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    assert rates["gold"] == pytest.approx(10.0)


def test_additive_state_modifier():
    """State modifier with add mode should add to base_production."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="sm1", source="gold", target="gen1", edge_type="state_modifier",
                 formula="5.0", target_property="base_production", modifier_mode="add"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    # base_production = 10 + 5 = 15
    assert rates["gold"] == pytest.approx(15.0)
