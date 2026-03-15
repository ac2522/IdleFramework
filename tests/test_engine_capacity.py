"""Tests for resource capacity clamping in PiecewiseEngine."""

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.nodes import Generator, Resource
from idleframework.model.state import GameState


def test_resource_clamped_at_capacity():
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=90.0, capacity=100.0),
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
    engine.advance_to(100.0)
    # Should be clamped at 100, not 90 + 10*100 = 1090
    assert engine.get_balance("gold") <= 100.0


def test_resource_no_capacity_unlimited():
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
    engine.advance_to(100.0)
    assert engine.get_balance("gold") == pytest.approx(1000.0, rel=0.01)


def test_capacity_waste_overflow():
    """overflow_behavior='waste' should also clamp at capacity."""
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(
                id="gold", name="Gold", initial_value=0.0, capacity=50.0, overflow_behavior="waste"
            ),
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
    assert engine.get_balance("gold") <= 50.0
