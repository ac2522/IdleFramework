"""Tests that Numba-accelerated functions match pure-Python results."""

import pytest

from idleframework.engine._numba_accel import bulk_purchase_cost_fast
from idleframework.engine.solvers import bulk_cost


class TestNumbaAcceleration:
    @pytest.mark.parametrize(
        "base,rate,owned,count",
        [
            (10.0, 1.15, 0, 1),
            (10.0, 1.15, 0, 10),
            (100.0, 1.07, 5, 5),
            (10.0, 1.0, 0, 10),  # rate=1 edge case
            (1e6, 1.15, 50, 10),  # large values
        ],
    )
    def test_bulk_cost_matches_pure_python(self, base, rate, owned, count):
        expected = float(bulk_cost(base, rate, owned, count))
        result = bulk_purchase_cost_fast(base, rate, owned, count)
        assert result == pytest.approx(expected, rel=1e-9)

    def test_zero_count_returns_zero(self):
        assert bulk_purchase_cost_fast(10.0, 1.15, 0, 0) == 0.0

    def test_negative_count_returns_zero(self):
        assert bulk_purchase_cost_fast(10.0, 1.15, 0, -5) == 0.0
