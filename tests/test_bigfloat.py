"""BigFloat core arithmetic tests.

Design requirement: 5 significant digits relative error tolerance (~1e-5).
Reference: break_infinity.js — mantissa in [1, 10), exponent is int.
"""
import math
import pytest
from idleframework.bigfloat import BigFloat


class TestConstruction:
    def test_from_int(self):
        b = BigFloat(100)
        assert b.mantissa == pytest.approx(1.0)
        assert b.exponent == 2

    def test_from_float(self):
        b = BigFloat(3.14)
        assert b.mantissa == pytest.approx(3.14)
        assert b.exponent == 0

    def test_from_components(self):
        b = BigFloat.from_components(1.5, 10)
        assert b.mantissa == pytest.approx(1.5)
        assert b.exponent == 10

    def test_zero(self):
        b = BigFloat(0)
        assert b.mantissa == 0.0
        assert b.exponent == 0
        assert float(b) == 0.0

    def test_negative(self):
        b = BigFloat(-42)
        assert b.mantissa == pytest.approx(-4.2)
        assert b.exponent == 1

    def test_very_small(self):
        b = BigFloat(0.001)
        assert b.mantissa == pytest.approx(1.0)
        assert b.exponent == -3

    def test_normalization(self):
        """Mantissa must be in [1, 10) or (-10, -1] after construction."""
        b = BigFloat(99.9)
        assert 1.0 <= abs(b.mantissa) < 10.0


class TestArithmetic:
    def test_add_same_exponent(self):
        a = BigFloat(100)
        b = BigFloat(200)
        result = a + b
        assert float(result) == pytest.approx(300.0)

    def test_add_different_exponent(self):
        a = BigFloat(1e10)
        b = BigFloat(1e5)
        result = a + b
        assert float(result) == pytest.approx(1e10 + 1e5, rel=1e-5)

    def test_add_huge_exponent_gap(self):
        """When exponents differ by >15, smaller value is negligible."""
        a = BigFloat.from_components(1.0, 100)
        b = BigFloat.from_components(1.0, 50)
        result = a + b
        assert result.exponent == 100
        assert result.mantissa == pytest.approx(1.0)

    def test_sub(self):
        a = BigFloat(500)
        b = BigFloat(200)
        result = a - b
        assert float(result) == pytest.approx(300.0)

    def test_mul(self):
        a = BigFloat(300)
        b = BigFloat(400)
        result = a * b
        assert float(result) == pytest.approx(120000.0)

    def test_mul_huge(self):
        a = BigFloat.from_components(2.0, 500)
        b = BigFloat.from_components(3.0, 400)
        result = a * b
        assert result.mantissa == pytest.approx(6.0)
        assert result.exponent == 900

    def test_div(self):
        a = BigFloat(1000)
        b = BigFloat(4)
        result = a / b
        assert float(result) == pytest.approx(250.0)

    def test_div_by_zero_raises(self):
        with pytest.raises(ZeroDivisionError):
            BigFloat(1) / BigFloat(0)

    def test_mul_by_zero(self):
        result = BigFloat(1e50) * BigFloat(0)
        assert float(result) == 0.0


class TestPowLog:
    """These are the hot-path operations — BigFloat's raison d'être."""

    def test_pow_integer(self):
        b = BigFloat(10)
        result = b ** 3
        assert float(result) == pytest.approx(1000.0)

    def test_pow_large_exponent(self):
        """base=1.07, owned=700 → cost ~ 1.07^700 ≈ 1.14e20."""
        b = BigFloat(1.07)
        result = b ** 700
        expected = 1.07 ** 700  # within float range
        assert float(result) == pytest.approx(expected, rel=1e-5)

    def test_pow_beyond_float(self):
        """1.15^5000 overflows float64. BigFloat must handle it."""
        b = BigFloat(1.15)
        result = b ** 5000
        # log10(1.15^5000) = 5000 * log10(1.15) ≈ 5000 * 0.0607 = 303.5
        assert result.exponent == pytest.approx(303, abs=1)
        assert 1.0 <= result.mantissa < 10.0

    def test_log10(self):
        b = BigFloat.from_components(5.0, 42)
        result = b.log10()
        # log10(5e42) = log10(5) + 42 ≈ 42.699
        assert result == pytest.approx(42.699, rel=1e-5)

    def test_log10_of_one(self):
        assert BigFloat(1).log10() == pytest.approx(0.0)

    def test_log10_of_zero_raises(self):
        with pytest.raises(ValueError):
            BigFloat(0).log10()

    def test_pow_zero_returns_one(self):
        assert float(BigFloat(5) ** 0) == pytest.approx(1.0)

    def test_pow_negative_even(self):
        result = BigFloat(-3) ** 2
        assert float(result) == pytest.approx(9.0)

    def test_pow_negative_odd(self):
        result = BigFloat(-3) ** 3
        assert float(result) == pytest.approx(-27.0)

    def test_pow_negative_float_even(self):
        """Float-typed integer power: (-3)^2.0 = 9"""
        result = BigFloat(-3) ** 2.0
        assert float(result) == pytest.approx(9.0)

    def test_pow_negative_float_odd(self):
        """Float-typed integer power: (-3)^3.0 = -27"""
        result = BigFloat(-3) ** 3.0
        assert float(result) == pytest.approx(-27.0)

    def test_pow_negative_non_integer_raises(self):
        with pytest.raises(ValueError):
            BigFloat(-8) ** 0.5


class TestComparison:
    def test_lt(self):
        assert BigFloat(1) < BigFloat(2)

    def test_gt_huge(self):
        a = BigFloat.from_components(1.0, 100)
        b = BigFloat.from_components(9.99, 99)
        assert a > b

    def test_eq(self):
        assert BigFloat(42) == BigFloat(42)

    def test_negative_ordering(self):
        assert BigFloat(-10) < BigFloat(-1)
        assert BigFloat(-1) < BigFloat(0)
        assert BigFloat(0) < BigFloat(1)

    def test_zero_lt_small_positive(self):
        assert BigFloat(0) < BigFloat(0.5)

    def test_zero_lt_tiny_positive(self):
        assert BigFloat(0) < BigFloat(1e-300)

    def test_zero_gt_negative(self):
        assert BigFloat(0) > BigFloat(-1)

    def test_zero_not_lt_zero(self):
        assert not (BigFloat(0) < BigFloat(0))


class TestConversion:
    def test_float_roundtrip(self):
        for val in [0, 1, -1, 3.14, 1e100, 1e-50, -2.5e30]:
            b = BigFloat(val)
            if val == 0:
                assert float(b) == 0.0
            else:
                assert float(b) == pytest.approx(val, rel=1e-10)

    def test_str_scientific(self):
        b = BigFloat.from_components(1.23, 50)
        assert "1.23" in str(b)
        assert "50" in str(b)

    def test_repr(self):
        b = BigFloat(42)
        assert "BigFloat" in repr(b)


class TestEdgeCases:
    def test_rate_equals_one_geometric_series(self):
        """rate=1 is a singularity in (rate^n - 1)/(rate - 1). Must use n directly."""
        rate = BigFloat(1)
        n = 10
        # Geometric series with rate=1: cost = base * n
        base = BigFloat(100)
        # This should NOT divide by zero
        if float(rate) == 1.0:
            cost = base * BigFloat(n)
        else:
            cost = base * (rate ** n - BigFloat(1)) / (rate - BigFloat(1))
        assert float(cost) == pytest.approx(1000.0)

    def test_bulk_cost_formula(self):
        """cost = base * rate^owned * (rate^n - 1) / (rate - 1)"""
        base = BigFloat(4)
        rate = BigFloat(1.07)
        owned = 10
        n = 5
        result = base * (rate ** owned) * ((rate ** n) - BigFloat(1)) / (rate - BigFloat(1))
        # Verify against direct Python float math
        expected = 4 * (1.07 ** 10) * ((1.07 ** 5) - 1) / (1.07 - 1)
        assert float(result) == pytest.approx(expected, rel=1e-5)

    def test_max_affordable(self):
        """max = floor(log_rate(currency * (rate-1) / (base * rate^owned) + 1))"""
        currency = BigFloat(10000)
        base = BigFloat(4)
        rate = BigFloat(1.07)
        owned = 10
        inner = currency * (rate - BigFloat(1)) / (base * (rate ** owned))
        inner = inner + BigFloat(1)
        max_n = math.floor(inner.log10() / rate.log10())
        assert isinstance(max_n, int)
        assert max_n > 0


class TestDisplayFormatting:
    def test_named_notation(self):
        from idleframework.bigfloat import format_bigfloat
        assert format_bigfloat(BigFloat(1.5e12), style="named") == "1.50 Trillion"

    def test_scientific_notation(self):
        from idleframework.bigfloat import format_bigfloat
        assert format_bigfloat(BigFloat.from_components(4.56, 50), style="scientific") == "4.56e50"

    def test_engineering_notation(self):
        from idleframework.bigfloat import format_bigfloat
        result = format_bigfloat(BigFloat(1.23e15), style="engineering")
        assert "Qa" in result or "1.23" in result
