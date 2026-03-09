"""Property-based tests for BigFloat using Hypothesis."""

import math
import pytest
from hypothesis import given, assume, settings
from hypothesis.strategies import floats, integers, composite

from idleframework.bigfloat import BigFloat


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

mantissas = floats(min_value=1.0, max_value=9.999, allow_nan=False, allow_infinity=False)
exponents = integers(min_value=-1_000_000, max_value=1_000_000)


@composite
def bigfloats(draw):
    """Strategy that generates valid positive BigFloat values."""
    m = draw(mantissas)
    e = draw(exponents)
    return BigFloat.from_components(m, e)


@composite
def nonzero_bigfloats(draw):
    """Strategy that generates non-zero positive BigFloat values."""
    bf = draw(bigfloats())
    assume(float(bf) != 0.0)
    return bf


# ---------------------------------------------------------------------------
# Algebraic properties
# ---------------------------------------------------------------------------

class TestAlgebraicProperties:
    @given(a=bigfloats(), b=bigfloats())
    def test_addition_commutativity(self, a, b):
        """a + b == b + a (exact)."""
        r1 = a + b
        r2 = b + a
        assert r1 == r2

    @given(a=bigfloats(), b=bigfloats())
    def test_multiplication_commutativity(self, a, b):
        """a * b == b * a (exact)."""
        r1 = a * b
        r2 = b * a
        assert r1 == r2

    @given(a=bigfloats())
    def test_additive_identity(self, a):
        """a + 0 == a."""
        zero = BigFloat(0)
        result = a + zero
        assert result == a

    @given(a=bigfloats())
    def test_multiplicative_identity(self, a):
        """a * 1 == a."""
        one = BigFloat(1)
        result = a * one
        assert result == a

    @given(a=bigfloats())
    def test_zero_product(self, a):
        """a * 0 == 0."""
        zero = BigFloat(0)
        result = a * zero
        assert result == zero

    @given(a=bigfloats(), b=bigfloats())
    def test_positive_addition_monotonicity(self, a, b):
        """For positive a, b: a + b >= a (when b is not negligible)."""
        result = a + b
        # Due to exponent gap, b might be negligible, so result >= a - epsilon
        assert result >= a or a.exponent - b.exponent > 15

    @given(a=nonzero_bigfloats(), b=nonzero_bigfloats())
    def test_log_product_rule(self, a, b):
        """log10(a * b) ≈ log10(a) + log10(b)."""
        product = a * b
        log_product = product.log10()
        log_sum = a.log10() + b.log10()
        assert log_product == pytest.approx(log_sum, abs=1e-9)

    @given(a=nonzero_bigfloats(), b=nonzero_bigfloats())
    @settings(max_examples=50)
    def test_multiply_divide_roundtrip(self, a, b):
        """(a * b) / b ≈ a."""
        product = a * b
        result = product / b
        # Compare via log10 for huge values
        log_a = a.log10()
        log_result = result.log10()
        assert log_result == pytest.approx(log_a, rel=1e-10, abs=1e-9)

    @given(a=nonzero_bigfloats())
    @settings(max_examples=50)
    def test_pow_log_consistency(self, a):
        """log10(a^2) ≈ 2 * log10(a)."""
        squared = a ** 2
        log_sq = squared.log10()
        expected = 2.0 * a.log10()
        assert log_sq == pytest.approx(expected, rel=1e-10, abs=1e-9)
