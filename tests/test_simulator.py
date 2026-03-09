"""RK4 test simulator — exists ONLY for test validation.

This is NOT the production engine. It's a simple numerical simulator used
for convergence testing: run at multiple step sizes and verify results
converge toward the math engine's analytical answer.
"""
import json
import pytest
from pathlib import Path


def rk4_step(state: dict, production_rates: dict, dt: float) -> dict:
    """Single RK4 step for resource accumulation.

    state: {resource_id: current_value}
    production_rates: {resource_id: production_per_second}
    """

    def deriv(s):
        return {k: production_rates.get(k, 0.0) for k in s}

    k1 = deriv(state)
    s2 = {k: state[k] + k1[k] * dt / 2 for k in state}
    k2 = deriv(s2)
    s3 = {k: state[k] + k2[k] * dt / 2 for k in state}
    k3 = deriv(s3)
    s4 = {k: state[k] + k3[k] * dt for k in state}
    k4 = deriv(s4)

    return {
        k: state[k] + (k1[k] + 2 * k2[k] + 2 * k3[k] + k4[k]) * dt / 6
        for k in state
    }


class TestRK4Basic:
    def test_constant_production(self):
        """1 unit/sec for 10 seconds = 10 units."""
        state = {"cash": 0.0}
        rates = {"cash": 1.0}
        dt = 0.1
        for _ in range(100):  # 100 steps * 0.1 = 10 seconds
            state = rk4_step(state, rates, dt)
        assert state["cash"] == pytest.approx(10.0, rel=1e-5)

    def test_known_production_rate(self):
        """Lemonade: 1/sec. After 60s with 5 owned: 5*1*60 = 300."""
        state = {"cash": 0.0}
        rates = {"cash": 5.0}  # 5 lemonade stands at 1/sec each
        dt = 0.01
        for _ in range(6000):  # 60 seconds
            state = rk4_step(state, rates, dt)
        assert state["cash"] == pytest.approx(300.0, rel=1e-5)

    def test_convergence_with_step_size(self):
        """RK4 should converge as step size decreases."""
        state_init = {"cash": 0.0}
        rates = {"cash": 100.0}
        target_time = 5.0
        results = []
        for dt in [1.0, 0.1, 0.01]:
            state = dict(state_init)
            steps = int(target_time / dt)
            for _ in range(steps):
                state = rk4_step(state, rates, dt)
            results.append(state["cash"])
        # All should converge to 500.0 (constant rate = exact for any step)
        for r in results:
            assert r == pytest.approx(500.0, rel=1e-5)


class TestMiniCapFixture:
    def test_fixture_loads(self):
        fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
        with open(fixture_path) as f:
            data = json.load(f)
        from idleframework.model.game import GameDefinition
        game = GameDefinition.model_validate(data)
        assert game.name == "MiniCap"
        assert len([n for n in game.nodes if n.type == "generator"]) == 3
