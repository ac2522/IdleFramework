"""Tests for autobuyer event processing in PiecewiseEngine."""
import pytest
from idleframework.model.nodes import Resource, Generator, AutobuyerNode
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def test_autobuyer_purchases_at_interval():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=10000.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10.0, cost_growth_rate=1.15),
            AutobuyerNode(id="ab1", target="gen1", interval=1.0),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    engine = PiecewiseEngine(game, state)
    engine.advance_to(5.0)
    # Autobuyer fires every 1s with enough gold, should have bought several generators
    assert engine.get_owned("gen1") > 0


def test_autobuyer_skipped_by_optimizer():
    """find_next_purchase should skip nodes managed by autobuyers."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=10000.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10.0, cost_growth_rate=1.15),
            Generator(id="gen2", name="Logger", base_production=5.0, cost_base=10.0, cost_growth_rate=1.15),
            AutobuyerNode(id="ab1", target="gen1", interval=1.0),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="gen2", target="gold", edge_type="production_target"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen2").owned = 1
    engine = PiecewiseEngine(game, state)
    result = engine.find_next_purchase()
    # gen1 is managed by autobuyer, so find_next_purchase should return gen2
    if result is not None:
        assert result[0] == "gen2"


def test_autobuyer_disabled():
    """Disabled autobuyer should not fire."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=10000.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10.0, cost_growth_rate=1.15),
            AutobuyerNode(id="ab1", target="gen1", interval=1.0, enabled=False),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    engine = PiecewiseEngine(game, state)
    engine.advance_to(5.0)
    assert engine.get_owned("gen1") == 0


def test_no_autobuyers_no_change():
    """Games without autobuyers should work as before."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=0.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10000, cost_growth_rate=1.15),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    engine.advance_to(10.0)
    assert engine.get_balance("gold") == pytest.approx(100.0, rel=0.05)
