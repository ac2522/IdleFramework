"""Tests for synergy evaluation in PiecewiseEngine."""
import pytest
from idleframework.model.nodes import Resource, Generator, SynergyNode
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def test_synergy_boosts_target():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="cursor", name="Cursor", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
            Generator(id="grandma", name="Grandma", base_production=5.0, cost_base=100, cost_growth_rate=1.15),
            SynergyNode(id="syn1", sources=["cursor"], formula_expr="owned_cursor * 0.01", target="grandma"),
        ],
        edges=[
            Edge(id="e1", source="cursor", target="gold", edge_type="production_target"),
            Edge(id="e2", source="grandma", target="gold", edge_type="production_target"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("cursor").owned = 100
    state.get("grandma").owned = 1
    engine = PiecewiseEngine(game, state)

    syn = engine.compute_synergy_multipliers()
    # synergy = owned_cursor * 0.01 = 100 * 0.01 = 1.0
    # multiplier = 1 + 1.0 = 2.0
    assert syn["grandma"] == pytest.approx(2.0)

    rates = engine.compute_production_rates()
    # Cursor: 1.0 * 100 = 100.0
    # Grandma: 5.0 * 1 * 2.0 (synergy) = 10.0
    # Total = 110
    assert rates["gold"] == pytest.approx(110.0)


def test_no_synergy_no_change():
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
    syn = engine.compute_synergy_multipliers()
    assert syn == {}
    rates = engine.compute_production_rates()
    assert rates["gold"] == pytest.approx(10.0)


def test_synergy_scales_with_source():
    """More sources owned = bigger synergy bonus."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="cursor", name="Cursor", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
            Generator(id="grandma", name="Grandma", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
            SynergyNode(id="syn1", sources=["cursor"], formula_expr="owned_cursor * 0.1", target="grandma"),
        ],
        edges=[
            Edge(id="e1", source="cursor", target="gold", edge_type="production_target"),
            Edge(id="e2", source="grandma", target="gold", edge_type="production_target"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("cursor").owned = 10
    state.get("grandma").owned = 1
    engine = PiecewiseEngine(game, state)

    # synergy = 10 * 0.1 = 1.0, mult = 2.0
    rates1 = engine.compute_production_rates()
    grandma_rate1 = rates1["gold"] - 10.0  # subtract cursor contribution

    state.get("cursor").owned = 50
    rates2 = engine.compute_production_rates()
    grandma_rate2 = rates2["gold"] - 50.0  # subtract cursor contribution

    assert grandma_rate2 > grandma_rate1
