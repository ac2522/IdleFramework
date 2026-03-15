"""Integration tests exercising all Phase 5 mechanics together."""

from fixtures.fullmechanics import make_fullmechanics_game

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.state import GameState
from idleframework.optimizer.greedy import GreedyOptimizer


def test_fullmechanics_game_loads():
    game = make_fullmechanics_game()
    assert len(game.nodes) == 15
    state = GameState.from_game(game)
    assert "gold" in state.node_states


def test_fullmechanics_engine_runs():
    game = make_fullmechanics_game()
    state = GameState.from_game(game)
    state.get("miner").owned = 1
    state.get("smith").owned = 1
    state.get("wizard").owned = 1
    engine = PiecewiseEngine(game, state)
    engine.advance_to(60.0)
    assert engine.get_balance("gold") > 100.0


def test_fullmechanics_greedy_optimizer():
    """Greedy optimizer should make purchase decisions on gold-producing generators.

    The greedy optimizer is a single-currency optimizer. We use a gold-only
    sub-game from the fixture (miner + smith + upgrades) to verify it works.
    """
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.nodes import Generator, Resource, Upgrade

    # Build a gold-only subset of the FullMechanics game
    nodes = [
        Resource(id="gold", name="Gold", initial_value=0.0),
        Generator(
            id="miner", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15
        ),
        Generator(
            id="smith", name="Smith", base_production=5.0, cost_base=100, cost_growth_rate=1.15
        ),
        Upgrade(
            id="upg_speed",
            name="Speed Boost",
            upgrade_type="multiplicative",
            magnitude=2.0,
            cost=500.0,
            target="miner",
            stacking_group="speed",
        ),
    ]
    edges = [
        Edge(id="e_miner_gold", source="miner", target="gold", edge_type="production_target"),
        Edge(id="e_smith_gold", source="smith", target="gold", edge_type="production_target"),
    ]
    game = GameDefinition(
        schema_version="1.0",
        name="GoldOnly",
        nodes=nodes,
        edges=edges,
        stacking_groups={"speed": "multiplicative"},
    )
    state = GameState.from_game(game)
    state.get("miner").owned = 5
    opt = GreedyOptimizer(game, state)
    steps = opt.run(target_time=300.0, max_steps=50)
    assert len(steps) > 0


def test_fullmechanics_drains_mana():
    """Mana should be drained by the drain node."""
    game = make_fullmechanics_game()
    state = GameState.from_game(game)
    state.get("wizard").owned = 0  # no production
    engine = PiecewiseEngine(game, state)
    initial_mana = engine.get_balance("mana")
    engine.advance_to(10.0)
    # Drain should reduce mana (rate=1.0/s, no production)
    assert engine.get_balance("mana") < initial_mana


def test_fullmechanics_capacity_clamps_mana():
    """Mana capacity should clamp at 500."""
    game = make_fullmechanics_game()
    state = GameState.from_game(game)
    state.get("wizard").owned = 100  # lots of production
    engine = PiecewiseEngine(game, state)
    engine.advance_to(100.0)
    assert engine.get_balance("mana") <= 500.0


def test_fullmechanics_prestige():
    """Should be able to prestige and reset scope."""
    game = make_fullmechanics_game()
    state = GameState.from_game(game)
    state.get("miner").owned = 10
    state.get("gold").current_value = 5000.0
    state.lifetime_earnings["gold"] = 10000.0
    engine = PiecewiseEngine(game, state)
    gain = engine.execute_prestige("prestige")
    assert gain > 0
    assert engine.get_owned("miner") == 0  # reset
    assert engine.get_balance("prestige_pts") > 0
