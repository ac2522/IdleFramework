"""Tests for buff expected value processing in PiecewiseEngine."""

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.nodes import BuffNode, Generator, Resource
from idleframework.model.state import GameState


def test_timed_buff_expected_value():
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(
                id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15
            ),
            BuffNode(
                id="buff1",
                buff_type="timed",
                duration=10.0,
                multiplier=3.0,
                cooldown=40.0,
                target="gen1",
            ),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    buffs = engine.evaluate_buffs()
    # EV = 1 + (3-1) * (10/(10+40)) = 1 + 2 * 0.2 = 1.4
    assert buffs.per_generator["gen1"] == pytest.approx(1.4)


def test_proc_buff_expected_value():
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(
                id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15
            ),
            BuffNode(id="buff1", buff_type="proc", proc_chance=0.1, multiplier=5.0),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    buffs = engine.evaluate_buffs()
    # EV = 1 + 0.1 * (5-1) = 1.4, global
    assert buffs.global_multiplier == pytest.approx(1.4)


def test_zero_cooldown_always_active():
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(
                id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15
            ),
            BuffNode(
                id="buff1",
                buff_type="timed",
                duration=10.0,
                multiplier=3.0,
                cooldown=0.0,
                target="gen1",
            ),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    buffs = engine.evaluate_buffs()
    assert buffs.per_generator["gen1"] == pytest.approx(3.0)


def test_buff_affects_production_rate():
    """Buff multiplier should actually change the computed production rate."""
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(
                id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15
            ),
            BuffNode(
                id="buff1",
                buff_type="timed",
                duration=10.0,
                multiplier=3.0,
                cooldown=40.0,
                target="gen1",
            ),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    # base=10, buff EV=1.4, rate=14.0
    assert rates["gold"] == pytest.approx(14.0)


def test_no_buffs_no_change():
    """Games without buffs should work as before."""
    game = GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(
                id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15
            ),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    assert rates["gold"] == pytest.approx(10.0)
