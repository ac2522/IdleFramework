"""Smoke tests: all E2E fixtures load, validate, and create engines."""

from idleframework.engine.segments import PiecewiseEngine


class TestE2EFixtureValidation:
    """Verify each E2E fixture passes Pydantic validation and engine init."""

    def test_fixture_loads(self, e2e_game):
        assert e2e_game.name
        assert len(e2e_game.nodes) > 0
        assert len(e2e_game.edges) > 0

    def test_engine_creates(self, e2e_game):
        engine = PiecewiseEngine(e2e_game, validate=True)
        assert engine.time == 0.0

    def test_engine_can_advance(self, e2e_game):
        engine = PiecewiseEngine(e2e_game, validate=True)
        engine.advance_to(10.0)
        assert engine.time == 10.0

    def test_all_node_ids_in_state(self, e2e_game):
        engine = PiecewiseEngine(e2e_game, validate=True)
        for node in e2e_game.nodes:
            state = engine.state.get(node.id)
            assert state is not None, f"Node {node.id!r} missing from engine state"
