"""Closed-form solver tests.

Formulas from design doc:
- bulk_cost = base * rate^owned * (rate^n - 1) / (rate - 1)
- max_affordable = floor(log_rate(currency * (rate-1) / (base * rate^owned) + 1))
- generator chain: t^n / n! (homogeneous), t^n / product(r_i) (heterogeneous)
- time_to_afford: cost / production_rate (constant), Brent's for complex
"""
import math
import pytest
from idleframework.bigfloat import BigFloat
from idleframework.engine.solvers import (
    bulk_cost,
    max_affordable,
    time_to_afford,
    generator_chain_output,
    production_accumulation,
)


class TestBulkCost:
    def test_single_purchase(self):
        """Cost of 1 unit: base * rate^owned."""
        cost = bulk_cost(base=4.0, rate=1.07, owned=0, count=1)
        assert cost == pytest.approx(4.0, rel=1e-5)

    def test_bulk_formula(self):
        """base * rate^owned * (rate^n - 1) / (rate - 1)"""
        cost = bulk_cost(base=4.0, rate=1.07, owned=10, count=5)
        expected = 4 * (1.07 ** 10) * ((1.07 ** 5) - 1) / (1.07 - 1)
        assert cost == pytest.approx(expected, rel=1e-5)

    def test_rate_one_singularity(self):
        """rate=1: cost = base * count (no geometric growth)."""
        cost = bulk_cost(base=100.0, rate=1.0, owned=0, count=10)
        assert cost == pytest.approx(1000.0, rel=1e-5)

    def test_rate_one_with_owned(self):
        """rate=1, owned=5: cost = base * count (all units same price)."""
        cost = bulk_cost(base=100.0, rate=1.0, owned=5, count=3)
        assert cost == pytest.approx(300.0, rel=1e-5)

    def test_zero_count(self):
        cost = bulk_cost(base=4.0, rate=1.07, owned=0, count=0)
        assert cost == pytest.approx(0.0)

    def test_large_values(self):
        """Should not overflow with BigFloat-scale inputs."""
        cost = bulk_cost(base=4.0, rate=1.15, owned=500, count=10)
        assert cost > 0  # Just ensure no crash


class TestMaxAffordable:
    def test_basic(self):
        """With 10000 cash, base=4, rate=1.07, owned=0: should afford many."""
        n = max_affordable(currency=10000.0, base=4.0, rate=1.07, owned=0)
        assert isinstance(n, int)
        assert n > 0
        # Verify: cost of n should be <= 10000, cost of n+1 should be > 10000
        assert bulk_cost(4.0, 1.07, 0, n) <= 10000.0 + 1e-5
        assert bulk_cost(4.0, 1.07, 0, n + 1) > 10000.0 - 1e-5

    def test_cant_afford_any(self):
        n = max_affordable(currency=1.0, base=100.0, rate=1.07, owned=0)
        assert n == 0

    def test_rate_one(self):
        """rate=1: max = floor(currency / base)."""
        n = max_affordable(currency=500.0, base=100.0, rate=1.0, owned=0)
        assert n == 5

    def test_large_currency(self):
        n = max_affordable(currency=1e15, base=4.0, rate=1.07, owned=0)
        assert n > 100


class TestTimeToAfford:
    def test_constant_production(self):
        """time = cost / rate for constant production."""
        t = time_to_afford(cost=100.0, production_rate=10.0)
        assert t == pytest.approx(10.0, rel=1e-5)

    def test_zero_production_raises(self):
        with pytest.raises(ValueError):
            time_to_afford(cost=100.0, production_rate=0.0)

    def test_already_affordable(self):
        """If current_balance >= cost, time = 0."""
        t = time_to_afford(cost=50.0, production_rate=10.0, current_balance=100.0)
        assert t == pytest.approx(0.0)

    def test_partial_balance(self):
        """Need 100, have 40, rate 10 → 6 seconds."""
        t = time_to_afford(cost=100.0, production_rate=10.0, current_balance=40.0)
        assert t == pytest.approx(6.0, rel=1e-5)


class TestGeneratorChain:
    def test_single_generator(self):
        """Chain depth 1: output = count * base_production * time."""
        output = generator_chain_output(
            chain_rates=[1.0],  # 1 unit/sec per generator
            counts=[5],         # 5 generators
            time=10.0,
        )
        assert output == pytest.approx(50.0, rel=1e-5)

    def test_homogeneous_chain(self):
        """Homogeneous chain: t^n / n! for n generators in chain."""
        # 2-level chain: outer produces inner, inner produces resource
        # With rate=1 each and 1 of each: output = t^2 / 2!
        output = generator_chain_output(
            chain_rates=[1.0, 1.0],
            counts=[1, 1],
            time=10.0,
        )
        assert output == pytest.approx(50.0, rel=1e-5)  # 10^2 / 2 = 50

    def test_heterogeneous_chain(self):
        """Different rates: t^n / product(rates)."""
        # 2-level chain with rates 2 and 3: output = count_product * t^2 / (2 * 3)
        # Actually for AdCap: output = c0 * c1 * r0 * r1 * t^2 / 2!
        output = generator_chain_output(
            chain_rates=[2.0, 3.0],
            counts=[1, 1],
            time=10.0,
        )
        # = 1 * 1 * 2 * 3 * 10^2 / 2! = 6 * 100 / 2 = 300
        assert output == pytest.approx(300.0, rel=1e-5)


class TestProductionAccumulation:
    def test_constant_rate(self):
        """Integral of constant rate over time = rate * time."""
        acc = production_accumulation(rate=10.0, duration=5.0)
        assert acc == pytest.approx(50.0, rel=1e-5)

    def test_zero_duration(self):
        acc = production_accumulation(rate=10.0, duration=0.0)
        assert acc == pytest.approx(0.0)
