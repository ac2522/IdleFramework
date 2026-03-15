"""Tests for drain processing in PiecewiseEngine."""

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.nodes import DrainNode, Generator, Resource
from idleframework.model.state import GameState


def _make_drain_game(production=10.0, drain_rate=3.0):
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(
                id="gen1",
                name="Miner",
                base_production=production,
                cost_base=10000,
                cost_growth_rate=1.15,
            ),
            DrainNode(id="drain1", rate=drain_rate),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="drain1", target="gold", edge_type="consumption"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    return game, state


def test_drain_reduces_net_rate():
    game, state = _make_drain_game(production=10.0, drain_rate=3.0)
    engine = PiecewiseEngine(game, state)
    gross = engine.compute_gross_rates()
    drains = engine.compute_drain_rates()
    assert gross["gold"] == pytest.approx(10.0)
    assert drains["gold"] == pytest.approx(3.0)


def test_drain_accumulation():
    game, state = _make_drain_game(production=10.0, drain_rate=3.0)
    engine = PiecewiseEngine(game, state)
    engine.advance_to(10.0)
    # Net rate = 10 - 3 = 7/s, initial = 100, after 10s = 100 + 70 = 170
    assert engine.get_balance("gold") == pytest.approx(170.0, rel=0.05)


def test_drain_exceeds_production():
    """When drain > production, resource depletes."""
    game, state = _make_drain_game(production=1.0, drain_rate=5.0)
    engine = PiecewiseEngine(game, state)
    engine.advance_to(30.0)
    # Net rate = 1 - 5 = -4/s, initial = 100, depletes at t=25s
    # Resource should be clamped at 0
    assert engine.get_balance("gold") >= 0.0


def test_drain_condition_true_drains():
    """DrainNode with condition that evaluates to true should drain."""
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(
                id="gen1",
                name="Miner",
                base_production=10.0,
                cost_base=10000,
                cost_growth_rate=1.15,
            ),
            DrainNode(id="drain1", rate=3.0, condition="balance_gold > 50"),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="drain1", target="gold", edge_type="consumption"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    drains = engine.compute_drain_rates()
    # balance_gold = 100 > 50, so drain should be active
    assert drains["gold"] == pytest.approx(3.0)


def test_drain_condition_false_no_drain():
    """DrainNode with condition that evaluates to false should not drain."""
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=10.0),
            Generator(
                id="gen1",
                name="Miner",
                base_production=10.0,
                cost_base=10000,
                cost_growth_rate=1.15,
            ),
            DrainNode(id="drain1", rate=3.0, condition="balance_gold > 50"),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="drain1", target="gold", edge_type="consumption"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    drains = engine.compute_drain_rates()
    # balance_gold = 10 < 50, so drain should NOT be active
    assert "gold" not in drains or drains.get("gold", 0.0) == pytest.approx(0.0)


def test_no_drains_no_change():
    """Games without drains should work as before."""
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=0.0),
            Generator(
                id="gen1",
                name="Miner",
                base_production=10.0,
                cost_base=10000,
                cost_growth_rate=1.15,
            ),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    engine.advance_to(10.0)
    assert engine.get_balance("gold") == pytest.approx(100.0, rel=0.01)
