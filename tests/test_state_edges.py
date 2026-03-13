"""Tests for state edge evaluation engine."""
import pytest
from idleframework.model.nodes import Resource, Generator
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState, NodeState
from idleframework.engine.state_edges import (
    evaluate_state_edges,
    apply_property_modifications,
    PropertyModification,
)


def _make_game_with_state_edge(formula, target_property, modifier_mode):
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(id="gen1", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(
                id="sm1", source="gold", target="gen1",
                edge_type="state_modifier", formula=formula,
                target_property=target_property, modifier_mode=modifier_mode,
            ),
        ],
        stacking_groups={},
    )
    state = GameState(
        node_states={"gold": NodeState(current_value=100.0), "gen1": NodeState(owned=5)},
    )
    return game, state


def test_state_edge_multiply():
    game, state = _make_game_with_state_edge("2.0", "base_production", "multiply")
    modified = evaluate_state_edges(game, state)
    # Should have a multiply modification with value 2.0
    mods = modified["gen1"]["base_production"]
    assert len(mods) == 1
    assert mods[0].value == pytest.approx(2.0)
    assert mods[0].mode == "multiply"


def test_state_edge_add():
    game, state = _make_game_with_state_edge("0.5", "base_production", "add")
    modified = evaluate_state_edges(game, state)
    mods = modified["gen1"]["base_production"]
    assert mods[0].value == pytest.approx(0.5)
    assert mods[0].mode == "add"


def test_state_edge_set():
    game, state = _make_game_with_state_edge("99.0", "base_production", "set")
    modified = evaluate_state_edges(game, state)
    mods = modified["gen1"]["base_production"]
    assert mods[0].value == pytest.approx(99.0)
    assert mods[0].mode == "set"


def test_apply_property_modifications_multiply():
    mods = [PropertyModification(value=2.0, mode="multiply")]
    assert apply_property_modifications(10.0, mods) == pytest.approx(20.0)


def test_apply_property_modifications_add():
    mods = [PropertyModification(value=5.0, mode="add")]
    assert apply_property_modifications(10.0, mods) == pytest.approx(15.0)


def test_apply_property_modifications_set():
    mods = [PropertyModification(value=99.0, mode="set")]
    assert apply_property_modifications(10.0, mods) == pytest.approx(99.0)


def test_apply_property_modifications_set_then_multiply():
    mods = [
        PropertyModification(value=50.0, mode="set"),
        PropertyModification(value=2.0, mode="multiply"),
    ]
    # set to 50, then multiply by 2 = 100
    assert apply_property_modifications(10.0, mods) == pytest.approx(100.0)


def test_apply_property_modifications_all_modes():
    mods = [
        PropertyModification(value=50.0, mode="set"),
        PropertyModification(value=2.0, mode="multiply"),
        PropertyModification(value=3.0, mode="add"),
    ]
    # set to 50, multiply by 2 = 100, add 3 = 103
    assert apply_property_modifications(10.0, mods) == pytest.approx(103.0)


def test_backward_compat_no_target_property():
    """State modifier without target_property uses _general_multiplier key."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(id="gen1", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="sm1", source="gold", target="gen1", edge_type="state_modifier", formula="3.0"),
        ],
        stacking_groups={},
    )
    state = GameState(
        node_states={"gold": NodeState(current_value=100.0), "gen1": NodeState(owned=5)},
    )
    modified = evaluate_state_edges(game, state)
    assert "_general_multiplier" in modified["gen1"]
    assert modified["gen1"]["_general_multiplier"][0].mode == "multiply"  # backward compat default
