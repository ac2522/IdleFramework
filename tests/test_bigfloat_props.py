"""Hypothesis property-based tests for BigFloat.

Tests approximate algebraic properties (float mantissa means exact
associativity/distributivity don't hold — we test within tolerance).
"""
import math
import pytest
from hypothesis import given, settings, assume
from hypothesis.strategies import floats, integers, composite
from idleframework.bigfloat import BigFloat

# Strategies
mantissas = floats(min_value=1.0, max_value=9.999, allow_nan=False, allow_infinity=False)
exponents = integers(min_value=-10**6, max_value=10**6)


@composite
def bigfloats(draw, positive=False):
    m = draw(mantissas)
    e = draw(exponents)
    if not positive:
        neg = draw(floats(min_value=0, max_value=1))
        if neg < 0.3:
            m = -m
    return BigFloat.from_components(m, e)


@composite
def positive_bigfloats(draw):
    return draw(bigfloats(positive=True))


def approx_eq(a: BigFloat, b: BigFloat, rel_tol: float = 1e-5) -> bool:
    """Check if two BigFloats are approximately equal within relative tolerance."""
    if a.is_zero and b.is_zero:
        return True
    if a.is_zero or b.is_zero:
        return False
    if a.exponent != b.exponent:
        diff = abs(a.exponent - b.exponent)
        if diff > 1:
            return False
    fa, fb = float(a), float(b)
    if math.isinf(fa) or math.isinf(fb):
        # Compare via log10
        la, lb = a.log10() if a.mantissa > 0 else 0, b.log10() if b.mantissa > 0 else 0
        return abs(la - lb) < abs(la) * rel_tol + 1e-10
    if fa == 0 and fb == 0:
        return True
    return abs(fa - fb) <= rel_tol * max(abs(fa), abs(fb))


class TestAlgebraicProperties:
    @given(a=bigfloats(), b=bigfloats())
    @settings(max_examples=200)
    def test_addition_commutativity(self, a, b):
        """a + b == b + a (exact for same-precision floats)."""
        assert approx_eq(a + b, b + a, rel_tol=1e-10)

    @given(a=bigfloats(), b=bigfloats())
    @settings(max_examples=200)
    def test_multiplication_commutativity(self, a, b):
        assert approx_eq(a * b, b * a, rel_tol=1e-10)

    @given(a=bigfloats())
    @settings(max_examples=200)
    def test_additive_identity(self, a):
        """a + 0 == a."""
        assert approx_eq(a + BigFloat(0), a)

    @given(a=bigfloats())
    @settings(max_examples=200)
    def test_multiplicative_identity(self, a):
        """a * 1 == a."""
        assert approx_eq(a * BigFloat(1), a)

    @given(a=bigfloats())
    @settings(max_examples=200)
    def test_zero_product(self, a):
        """a * 0 == 0."""
        result = a * BigFloat(0)
        assert result.is_zero

    @given(a=positive_bigfloats(), b=positive_bigfloats())
    @settings(max_examples=200)
    def test_positive_addition_monotonicity(self, a, b):
        """a > 0, b > 0 => a + b > a."""
        result = a + b
        # Only holds when b is not negligible relative to a
        if b.exponent >= a.exponent - 14:
            assert result >= a

    @given(a=positive_bigfloats(), b=positive_bigfloats())
    @settings(max_examples=200)
    def test_log_product_rule(self, a, b):
        """log10(a * b) ≈ log10(a) + log10(b)."""
        product = a * b
        if not product.is_zero:
            log_product = product.log10()
            log_sum = a.log10() + b.log10()
            assert log_product == pytest.approx(log_sum, abs=1e-9)


class TestArithmeticStability:
    @given(a=positive_bigfloats())
    @settings(max_examples=100)
    def test_multiply_divide_roundtrip(self, a):
        """(a * b) / b ≈ a for non-zero b."""
        b = BigFloat(7.3)
        result = (a * b) / b
        assert approx_eq(result, a, rel_tol=1e-10)

    @given(exp=integers(min_value=0, max_value=10000))
    @settings(max_examples=100)
    def test_pow_log_consistency(self, exp):
        """log10(10^exp) == exp."""
        b = BigFloat(10) ** exp
        if not b.is_zero:
            assert b.log10() == pytest.approx(float(exp), rel=1e-10)
