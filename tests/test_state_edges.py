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


def test_general_multiplier_affects_production():
    """State modifier without target_property should multiply generator production."""
    from idleframework.engine.segments import PiecewiseEngine

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=0.0),
            Generator(id="gen1", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="sm1", source="gold", target="gen1", edge_type="state_modifier", formula="3.0"),
        ],
        stacking_groups={},
    )
    state = GameState(
        node_states={"gold": NodeState(current_value=0.0), "gen1": NodeState(owned=1)},
    )
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    # Without state modifier: rate = 1.0 * 1 / 1.0 = 1.0
    # With general_multiplier of 3.0 (multiply mode): rate = 1.0 * 3.0 = 3.0
    assert rates["gold"] == pytest.approx(3.0)


def test_topological_sort_no_false_positive_on_prefix():
    """Variable 'owned_gen' should not match formula containing 'owned_general'."""
    from idleframework.engine.state_edges import _topological_sort_edges

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen", name="Gen", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
            Generator(id="general", name="General", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[
            Edge(id="e1", source="gen", target="gold", edge_type="production_target"),
            Edge(id="e2", source="general", target="gold", edge_type="production_target"),
            # sm1 targets "gen", sm2 targets "general"
            # sm2's formula uses "owned_general" which should NOT create a dependency on sm1 (which produces owned_gen)
            Edge(id="sm1", source="gold", target="gen", edge_type="state_modifier",
                 formula="2.0", target_property="base_production", modifier_mode="multiply"),
            Edge(id="sm2", source="gold", target="general", edge_type="state_modifier",
                 formula="owned_general * 1.5", target_property="base_production", modifier_mode="multiply"),
        ],
        stacking_groups={},
    )
    sm_edges = [e for e in game.edges if e.edge_type == "state_modifier"]
    # Pass sm2 first — if there's a false dependency (sm2 depends on sm1),
    # sm1 would be forced before sm2, changing the input order.
    sm_edges = list(reversed(sm_edges))
    result = _topological_sort_edges(sm_edges, game)
    # Both should be independent (no dependency between them)
    # If substring matching is used, sm2 would falsely depend on sm1
    assert len(result) == 2
    # With no false dependency, input order should be preserved (sm2 first)
    assert result[0].id == "sm2"


def test_topological_sort_cycle_detection():
    """Cycle in state_modifier edges should raise ValueError."""
    from idleframework.engine.state_edges import _topological_sort_edges

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen1", name="Gen1", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
            Generator(id="gen2", name="Gen2", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="gen2", target="gold", edge_type="production_target"),
            # sm1 targets gen1, formula references gen2 vars -> depends on sm2
            Edge(id="sm1", source="gold", target="gen1", edge_type="state_modifier",
                 formula="owned_gen2 * 2", target_property="base_production", modifier_mode="multiply"),
            # sm2 targets gen2, formula references gen1 vars -> depends on sm1 -> CYCLE
            Edge(id="sm2", source="gold", target="gen2", edge_type="state_modifier",
                 formula="owned_gen1 * 3", target_property="base_production", modifier_mode="multiply"),
        ],
        stacking_groups={},
    )
    sm_edges = [e for e in game.edges if e.edge_type == "state_modifier"]

    with pytest.raises(ValueError, match="Cycle detected"):
        _topological_sort_edges(sm_edges, game)
