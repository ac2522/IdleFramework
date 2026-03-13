"""Tests for variable name sanitization and state variable building."""
import pytest
from idleframework.engine.variables import sanitize_var_name, build_state_variables


def test_sanitize_simple():
    assert sanitize_var_name("gen1") == "gen1"


def test_sanitize_hyphens():
    assert sanitize_var_name("my-generator") == "my_generator"


def test_sanitize_special_chars():
    assert sanitize_var_name("node.with.dots") == "node_with_dots"
    assert sanitize_var_name("node@special!") == "node_special_"


def test_build_state_variables():
    from idleframework.model.nodes import Resource, Generator
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState, NodeState

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(id="gen-1", name="Miner", base_production=1, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[], stacking_groups={},
    )
    state = GameState(
        node_states={
            "gold": NodeState(current_value=100.0),
            "gen-1": NodeState(owned=5),
        },
        elapsed_time=60.0,
        run_time=30.0,
        lifetime_earnings={"gold": 500.0},
    )
    vs = build_state_variables(game, state)
    assert vs["owned_gen_1"] == 5.0
    assert vs["balance_gold"] == 100.0
    assert vs["lifetime_gold"] == 500.0
    assert vs["elapsed_time"] == 60.0
