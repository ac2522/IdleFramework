"""Unit tests for BigFloat number type."""

import math

import pytest

from idleframework.bigfloat import BigFloat, format_bigfloat

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_from_int(self):
        bf = BigFloat(100)
        assert bf.mantissa == pytest.approx(1.0)
        assert bf.exponent == 2

    def test_from_float(self):
        bf = BigFloat(3.14)
        assert bf.mantissa == pytest.approx(3.14)
        assert bf.exponent == 0

    def test_zero(self):
        bf = BigFloat(0)
        assert bf.mantissa == 0.0
        assert bf.exponent == 0

    def test_negative(self):
        bf = BigFloat(-42)
        assert bf.mantissa == pytest.approx(-4.2)
        assert bf.exponent == 1

    def test_very_small(self):
        bf = BigFloat(0.001)
        assert bf.mantissa == pytest.approx(1.0)
        assert bf.exponent == -3

    def test_normalization(self):
        """Mantissa should always be in [1, 10) for positive values."""
        bf = BigFloat(99.9)
        assert 1.0 <= bf.mantissa < 10.0
        assert bf.exponent == 1

    def test_from_components(self):
        bf = BigFloat.from_components(2.5, 100)
        assert bf.mantissa == pytest.approx(2.5)
        assert bf.exponent == 100

    def test_from_components_renormalizes(self):
        """from_components should re-normalize if mantissa is out of range."""
        bf = BigFloat.from_components(25.0, 3)
        assert 1.0 <= bf.mantissa < 10.0
        assert float(bf) == pytest.approx(25000.0)

    def test_from_bigfloat(self):
        original = BigFloat(123)
        copy = BigFloat(original)
        assert copy.mantissa == original.mantissa
        assert copy.exponent == original.exponent


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_add_same_exponent(self):
        a = BigFloat(100)
        b = BigFloat(200)
        result = a + b
        assert float(result) == pytest.approx(300.0)

    def test_add_different_exponent(self):
        a = BigFloat(1000)
        b = BigFloat(1)
        result = a + b
        assert float(result) == pytest.approx(1001.0)

    def test_add_huge_exponent_gap(self):
        """When exponent gap > 15, smaller value is negligible."""
        a = BigFloat.from_components(1.0, 100)
        b = BigFloat.from_components(1.0, 0)
        result = a + b
        assert result.exponent == 100
        assert result.mantissa == pytest.approx(1.0)

    def test_sub(self):
        a = BigFloat(500)
        b = BigFloat(200)
        result = a - b
        assert float(result) == pytest.approx(300.0)

    def test_sub_to_zero(self):
        a = BigFloat(42)
        result = a - a
        assert float(result) == pytest.approx(0.0)

    def test_mul(self):
        a = BigFloat(6)
        b = BigFloat(7)
        result = a * b
        assert float(result) == pytest.approx(42.0)

    def test_mul_huge(self):
        a = BigFloat.from_components(3.0, 500)
        b = BigFloat.from_components(2.0, 300)
        result = a * b
        assert result.mantissa == pytest.approx(6.0)
        assert result.exponent == 800

    def test_div(self):
        a = BigFloat(100)
        b = BigFloat(4)
        result = a / b
        assert float(result) == pytest.approx(25.0)

    def test_div_by_zero(self):
        a = BigFloat(1)
        b = BigFloat(0)
        with pytest.raises(ZeroDivisionError):
            a / b

    def test_mul_by_zero(self):
        a = BigFloat(999)
        b = BigFloat(0)
        result = a * b
        assert float(result) == pytest.approx(0.0)

    def test_neg(self):
        a = BigFloat(42)
        result = -a
        assert float(result) == pytest.approx(-42.0)

    def test_abs_negative(self):
        a = BigFloat(-42)
        result = abs(a)
        assert float(result) == pytest.approx(42.0)

    def test_abs_positive(self):
        a = BigFloat(42)
        result = abs(a)
        assert float(result) == pytest.approx(42.0)


# ---------------------------------------------------------------------------
# Reverse operators
# ---------------------------------------------------------------------------

class TestReverseOperators:
    def test_radd(self):
        result = 10 + BigFloat(5)
        assert float(result) == pytest.approx(15.0)

    def test_rmul(self):
        result = 3 * BigFloat(7)
        assert float(result) == pytest.approx(21.0)

    def test_rsub(self):
        result = 100 - BigFloat(30)
        assert float(result) == pytest.approx(70.0)

    def test_rtruediv(self):
        result = 100 / BigFloat(4)
        assert float(result) == pytest.approx(25.0)


# ---------------------------------------------------------------------------
# Pow / Log
# ---------------------------------------------------------------------------

class TestPowLog:
    def test_integer_pow(self):
        a = BigFloat(2)
        result = a ** 10
        assert float(result) == pytest.approx(1024.0)

    def test_large_exponent_pow(self):
        a = BigFloat(10)
        result = a ** 100
        assert result.exponent == 100
        assert result.mantissa == pytest.approx(1.0)

    def test_beyond_float_pow(self):
        """1.15^5000 is astronomically large — must not overflow."""
        a = BigFloat(1.15)
        result = a ** 5000
        # log10(1.15^5000) = 5000 * log10(1.15) ≈ 5000 * 0.06070 ≈ 303.5
        expected_log = 5000 * math.log10(1.15)
        actual_log = result.log10()
        assert actual_log == pytest.approx(expected_log, rel=1e-5)

    def test_pow_zero(self):
        a = BigFloat(42)
        result = a ** 0
        assert float(result) == pytest.approx(1.0)

    def test_pow_one(self):
        a = BigFloat(42)
        result = a ** 1
        assert float(result) == pytest.approx(42.0)

    def test_pow_fractional(self):
        a = BigFloat(100)
        result = a ** 0.5
        assert float(result) == pytest.approx(10.0, rel=1e-5)

    def test_log10(self):
        a = BigFloat(1000)
        assert a.log10() == pytest.approx(3.0)

    def test_log10_one(self):
        a = BigFloat(1)
        assert a.log10() == pytest.approx(0.0)

    def test_log10_zero(self):
        a = BigFloat(0)
        with pytest.raises(ValueError):
            a.log10()

    def test_log10_negative(self):
        a = BigFloat(-5)
        with pytest.raises(ValueError):
            a.log10()

    def test_log10_huge(self):
        a = BigFloat.from_components(5.0, 1000000)
        result = a.log10()
        assert result == pytest.approx(1000000 + math.log10(5.0))


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

class TestComparison:
    def test_lt(self):
        assert BigFloat(1) < BigFloat(2)

    def test_gt_huge(self):
        a = BigFloat.from_components(1.0, 1000)
        b = BigFloat.from_components(9.0, 999)
        assert a > b

    def test_eq(self):
        assert BigFloat(42) == BigFloat(42)

    def test_eq_zero(self):
        assert BigFloat(0) == BigFloat(0)

    def test_negative_ordering(self):
        assert BigFloat(-10) < BigFloat(-1)
        assert BigFloat(-1) < BigFloat(0)
        assert BigFloat(-1) < BigFloat(1)

    def test_hash_equal(self):
        a = BigFloat(42)
        b = BigFloat(42)
        assert hash(a) == hash(b)

    def test_hash_usable_in_set(self):
        s = {BigFloat(1), BigFloat(2), BigFloat(1)}
        assert len(s) == 2


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

class TestConversion:
    def test_float_roundtrip(self):
        for val in [0, 1, -1, 42, 0.001, 1e10, -3.14]:
            bf = BigFloat(val)
            assert float(bf) == pytest.approx(val, rel=1e-10, abs=1e-15)

    def test_str(self):
        bf = BigFloat(1000)
        s = str(bf)
        assert "1" in s  # At minimum contains the mantissa digit

    def test_repr(self):
        bf = BigFloat(1000)
        r = repr(bf)
        assert "BigFloat" in r


# ---------------------------------------------------------------------------
# Edge cases: idle game formulas
# ---------------------------------------------------------------------------

class TestIdleGameFormulas:
    def test_geometric_series_rate_1(self):
        """Geometric series with rate=1 degenerates to n*base_cost.
        sum = base * n  (not base * (r^n - 1)/(r - 1) which divides by zero)
        """
        base_cost = BigFloat(100)
        rate = BigFloat(1)
        n = 10
        # With rate=1, total cost = base * n
        if float(rate) == 1.0:
            total = base_cost * n
        else:
            total = base_cost * (rate ** n - BigFloat(1)) / (rate - BigFloat(1))
        assert float(total) == pytest.approx(1000.0)

    def test_bulk_cost_formula(self):
        """Standard idle game bulk cost: base * (rate^n - 1) / (rate - 1)."""
        base = BigFloat(10)
        rate = BigFloat(1.15)
        n = 50
        # Expected: 10 * (1.15^50 - 1) / (1.15 - 1)
        expected = 10 * (1.15 ** 50 - 1) / (1.15 - 1)
        result = base * (rate ** n - BigFloat(1)) / (rate - BigFloat(1))
        assert float(result) == pytest.approx(expected, rel=1e-5)

    def test_max_affordable(self):
        """Given currency c, base cost b, rate r:
        max n where b*(r^n-1)/(r-1) <= c
        For c=1000, b=10, r=1.15: solve analytically.
        n = floor(log(c*(r-1)/b + 1) / log(r))
        """
        c, b, r = 1000.0, 10.0, 1.15
        n_expected = int(math.log(c * (r - 1) / b + 1) / math.log(r))

        c_bf = BigFloat(c)
        b_bf = BigFloat(b)
        r_bf = BigFloat(r)
        # n = floor(log10(c*(r-1)/b + 1) / log10(r))
        numerator = (c_bf * (r_bf - BigFloat(1)) / b_bf + BigFloat(1)).log10()
        denominator = r_bf.log10()
        n_result = int(numerator / denominator)
        assert n_result == n_expected


# ---------------------------------------------------------------------------
# Display formatting
# ---------------------------------------------------------------------------

class TestFormatting:
    def test_scientific(self):
        bf = BigFloat.from_components(1.23, 15)
        s = format_bigfloat(bf, "scientific")
        assert "1.23" in s
        assert "e15" in s.lower() or "e+15" in s.lower()

    def test_named(self):
        bf = BigFloat.from_components(1.23, 12)
        s = format_bigfloat(bf, "named")
        assert "Trillion" in s or "trillion" in s.lower()

    def test_named_small(self):
        bf = BigFloat(42)
        s = format_bigfloat(bf, "named")
        assert "42" in s

    def test_engineering(self):
        bf = BigFloat.from_components(1.23, 15)
        s = format_bigfloat(bf, "engineering")
        assert "Qa" in s or "qa" in s.lower()

    def test_scientific_zero(self):
        bf = BigFloat(0)
        s = format_bigfloat(bf, "scientific")
        assert "0" in s


class TestBigFloatImmutability:
    def test_cannot_set_mantissa(self):
        bf = BigFloat(42)
        with pytest.raises(AttributeError):
            bf.mantissa = 999.0

    def test_cannot_set_exponent(self):
        bf = BigFloat(42)
        with pytest.raises(AttributeError):
            bf.exponent = 100

    def test_cannot_delete_mantissa(self):
        bf = BigFloat(42)
        with pytest.raises(AttributeError):
            del bf.mantissa


class TestBigFloatNegativePow:
    def test_negative_base_even_power(self):
        result = BigFloat(-2) ** 2
        assert float(result) == pytest.approx(4.0)

    def test_negative_base_odd_power(self):
        result = BigFloat(-2) ** 3
        assert float(result) == pytest.approx(-8.0)

    def test_negative_base_fractional_power_raises(self):
        with pytest.raises(ValueError, match="non-integer"):
            BigFloat(-2) ** 0.5

    def test_negative_base_zero_power(self):
        result = BigFloat(-5) ** 0
        assert float(result) == pytest.approx(1.0)


class TestBigFloatFloorCeil:
    def test_floor_positive(self):
        assert BigFloat(3.7).floor() == 3

    def test_floor_negative(self):
        assert BigFloat(-3.2).floor() == -4

    def test_floor_integer(self):
        assert BigFloat(5).floor() == 5

    def test_ceil_positive(self):
        assert BigFloat(3.2).ceil() == 4

    def test_ceil_negative(self):
        assert BigFloat(-3.7).ceil() == -3

    def test_ceil_integer(self):
        assert BigFloat(5).ceil() == 5

    def test_floor_small_fraction(self):
        bf = BigFloat.from_components(5.0, -1)  # 0.5
        assert bf.floor() == 0

    def test_floor_zero(self):
        assert BigFloat(0).floor() == 0


class TestBigFloatMod:
    def test_mod_basic(self):
        result = BigFloat(10) % BigFloat(3)
        assert float(result) == pytest.approx(1.0)

    def test_mod_exact(self):
        result = BigFloat(12) % BigFloat(4)
        assert float(result) == pytest.approx(0.0)

    def test_rmod(self):
        result = 10 % BigFloat(3)
        assert float(result) == pytest.approx(1.0)


class TestNormalizationInvariant:
    """Verify mantissa is always in [1, 10) after all operations."""

    def test_from_components_edge_case(self):
        """Mantissa exactly at boundary should normalize correctly."""
        bf = BigFloat.from_components(10.0, 5)
        assert 1.0 <= bf.mantissa < 10.0
        assert float(bf) == pytest.approx(1e6)

    def test_from_components_very_small_mantissa(self):
        bf = BigFloat.from_components(0.001, 10)
        assert 1.0 <= bf.mantissa < 10.0
        assert float(bf) == pytest.approx(1e7)

    def test_after_subtraction_near_cancellation(self):
        """Subtracting nearly equal values must still normalize."""
        a = BigFloat.from_components(1.0000001, 10)
        b = BigFloat.from_components(1.0000000, 10)
        result = a - b
        if not result._is_zero():
            assert 1.0 <= abs(result.mantissa) < 10.0
