"""Property-based tests for new Phase 5 mechanics."""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.nodes import (
    DrainNode,
    Generator,
    Resource,
    TickspeedNode,
)
from idleframework.model.state import GameState


@given(tickspeed=st.floats(min_value=0.1, max_value=100.0))
@settings(max_examples=50)
def test_tickspeed_always_scales_production(tickspeed):
    """Higher tickspeed always means higher production."""
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="g1", name="G", base_production=1.0, cost_base=100, cost_growth_rate=1.15),
            TickspeedNode(id="ts1", base_tickspeed=tickspeed),
        ],
        edges=[Edge(id="e1", source="g1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("g1").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    assert rates["gold"] == pytest.approx(tickspeed * 1.0, rel=1e-6)


@given(
    multiplier=st.floats(min_value=1.01, max_value=100.0),
    duration=st.floats(min_value=0.1, max_value=1000.0),
    cooldown=st.floats(min_value=0.01, max_value=1000.0),
)
@settings(max_examples=50)
def test_buff_ev_between_1_and_multiplier(multiplier, duration, cooldown):
    """Timed buff EV is always between 1.0 and the raw multiplier."""
    ev = 1.0 + (multiplier - 1.0) * (duration / (duration + cooldown))
    assert 1.0 <= ev <= multiplier


@given(drain_rate=st.floats(min_value=0.01, max_value=100.0))
@settings(max_examples=20)
def test_drain_exceeding_production_depletes(drain_rate):
    """When drain > production, resource decreases."""
    assume(drain_rate > 1.0)
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(
                id="g1", name="G", base_production=1.0, cost_base=10000, cost_growth_rate=1.15
            ),
            DrainNode(id="d1", rate=drain_rate),
        ],
        edges=[
            Edge(id="e1", source="g1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="d1", target="gold", edge_type="consumption"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("g1").owned = 1
    engine = PiecewiseEngine(game, state)
    initial = engine.get_balance("gold")
    engine.advance_to(10.0)
    assert engine.get_balance("gold") < initial
