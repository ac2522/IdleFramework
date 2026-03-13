"""Tests for tickspeed resolution in PiecewiseEngine."""
import pytest
from idleframework.model.nodes import Resource, Generator, TickspeedNode, Upgrade
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def _make_tickspeed_game(base_tickspeed=1.0, with_upgrade=False):
    nodes = [
        Resource(id="gold", name="Gold", initial_value=0.0),
        Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
        TickspeedNode(id="ts1", base_tickspeed=base_tickspeed),
    ]
    edges = [Edge(id="e1", source="gen1", target="gold", edge_type="production_target")]
    stacking = {}
    if with_upgrade:
        nodes.append(Upgrade(
            id="ts_upg", name="Tick Boost", upgrade_type="multiplicative",
            magnitude=2.0, cost=0.0, target="ts1", stacking_group="tick",
        ))
        stacking["tick"] = "multiplicative"
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=nodes, edges=edges, stacking_groups=stacking,
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    return game, state


def test_tickspeed_doubles_production():
    game, state = _make_tickspeed_game(base_tickspeed=2.0)
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    # 10.0 base_production * 1 owned / 1.0 cycle * 2.0 tickspeed = 20.0
    assert rates["gold"] == pytest.approx(20.0)


def test_tickspeed_default_no_change():
    game, state = _make_tickspeed_game(base_tickspeed=1.0)
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    assert rates["gold"] == pytest.approx(10.0)


def test_tickspeed_upgrade_multiplies():
    game, state = _make_tickspeed_game(base_tickspeed=1.0, with_upgrade=True)
    engine = PiecewiseEngine(game, state)
    # Purchase the free upgrade
    state.get("ts_upg").purchased = True
    rates = engine.compute_production_rates()
    # tickspeed = 1.0 * 2.0 (upgrade) = 2.0, production = 10 * 1 * 2.0 = 20.0
    assert rates["gold"] == pytest.approx(20.0)


def test_no_tickspeed_node_returns_1():
    """Games without TickspeedNode should still work (tickspeed = 1.0)."""
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
    assert engine.compute_tickspeed() == 1.0
    rates = engine.compute_production_rates()
    assert rates["gold"] == pytest.approx(10.0)
