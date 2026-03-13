"""Tests for multi-layer prestige in PiecewiseEngine."""
import pytest
from idleframework.model.nodes import Resource, Generator, PrestigeLayer, Upgrade
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def _make_two_layer_game():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=1000.0),
            Resource(id="prestige_pts", name="Prestige Points"),
            Resource(id="transcend_pts", name="Transcend Points"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10, cost_growth_rate=1.15),
            PrestigeLayer(
                id="prestige", formula_expr="floor(sqrt(lifetime_gold))",
                layer_index=1, reset_scope=["gen1", "gold"],
                persistence_scope=["prestige_pts"],
                currency_id="prestige_pts",
            ),
            PrestigeLayer(
                id="transcend", formula_expr="floor(sqrt(lifetime_prestige_pts))",
                layer_index=2, reset_scope=["gen1", "gold", "prestige_pts"],
                persistence_scope=["transcend_pts"],
                currency_id="transcend_pts",
            ),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    return game


def test_prestige_resets_lower_scope():
    game = _make_two_layer_game()
    state = GameState.from_game(game)
    state.get("gen1").owned = 10
    state.get("gold").current_value = 5000.0
    state.lifetime_earnings["gold"] = 10000.0
    engine = PiecewiseEngine(game, state)

    gain = engine.execute_prestige("prestige")

    # Gold and gen1 should be reset
    assert engine.get_owned("gen1") == 0
    assert engine.get_balance("gold") == pytest.approx(1000.0)  # reset to initial_value
    # Prestige points gained: floor(sqrt(10000)) = 100
    assert engine.get_balance("prestige_pts") == pytest.approx(100.0)
    assert gain == pytest.approx(100.0)


def test_higher_layer_resets_lower_layers():
    game = _make_two_layer_game()
    state = GameState.from_game(game)
    state.get("gen1").owned = 10
    state.get("gold").current_value = 5000.0
    state.get("prestige_pts").current_value = 100.0
    state.lifetime_earnings["gold"] = 10000.0
    state.lifetime_earnings["prestige_pts"] = 200.0
    engine = PiecewiseEngine(game, state)

    engine.execute_prestige("transcend")

    # Everything reset except transcend_pts
    assert engine.get_owned("gen1") == 0
    assert engine.get_balance("gold") == pytest.approx(1000.0)  # reset to initial_value
    assert engine.get_balance("prestige_pts") == pytest.approx(0.0)  # reset to initial_value=0
    # Transcend pts: floor(sqrt(200)) = 14
    assert engine.get_balance("transcend_pts") == pytest.approx(14.0)


def test_prestige_non_prestige_raises():
    game = _make_two_layer_game()
    state = GameState.from_game(game)
    engine = PiecewiseEngine(game, state)
    with pytest.raises(ValueError, match="not a PrestigeLayer"):
        engine.execute_prestige("gold")


def test_layer_run_times_reset():
    game = _make_two_layer_game()
    state = GameState.from_game(game)
    state.lifetime_earnings["gold"] = 10000.0
    engine = PiecewiseEngine(game, state)

    engine.execute_prestige("prestige")
    assert state.layer_run_times["prestige"] == 0.0
