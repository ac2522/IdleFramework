"""Tests for the Formula DSL: Lark parser + bytecode compiler + AST whitelist."""

import math

import pytest

from idleframework.dsl.compiler import CompiledFormula, compile_formula, evaluate_formula


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eval(text: str, variables: dict | None = None) -> float:
    """Shorthand: compile + evaluate in one step."""
    formula = compile_formula(text)
    return evaluate_formula(formula, variables)


# ---------------------------------------------------------------------------
# TestBasicParsing
# ---------------------------------------------------------------------------

class TestBasicParsing:
    def test_literal_int(self):
        assert _eval("42") == 42

    def test_literal_float(self):
        assert _eval("3.14") == pytest.approx(3.14)

    def test_scientific_notation(self):
        assert _eval("1e15") == 1e15

    def test_scientific_notation_with_decimal(self):
        assert _eval("2.5e3") == 2500.0

    def test_negative_number(self):
        assert _eval("-7") == -7


# ---------------------------------------------------------------------------
# TestOperators
# ---------------------------------------------------------------------------

class TestOperators:
    def test_add(self):
        assert _eval("2 + 3") == 5

    def test_subtract(self):
        assert _eval("10 - 4") == 6

    def test_multiply(self):
        assert _eval("3 * 7") == 21

    def test_divide(self):
        assert _eval("20 / 4") == 5.0

    def test_precedence_mul_over_add(self):
        assert _eval("2 + 3 * 4") == 14

    def test_parentheses_override_precedence(self):
        assert _eval("(2 + 3) * 4") == 20

    def test_power(self):
        assert _eval("2 ** 10") == 1024

    def test_modulo(self):
        assert _eval("17 % 5") == 2

    def test_power_higher_than_unary(self):
        # -2**2 should be -(2**2) = -4
        assert _eval("-2 ** 2") == -4

    def test_nested_parentheses(self):
        assert _eval("((1 + 2) * (3 + 4))") == 21


# ---------------------------------------------------------------------------
# TestFunctions
# ---------------------------------------------------------------------------

class TestFunctions:
    def test_sqrt(self):
        assert _eval("sqrt(144)") == 12.0

    def test_log10(self):
        assert _eval("log10(1000)") == pytest.approx(3.0)

    def test_ln(self):
        assert _eval("ln(1)") == 0.0

    def test_log_alias(self):
        # log() is an alias for ln() (natural log)
        assert _eval("log(1)") == 0.0

    def test_abs(self):
        assert _eval("abs(-42)") == 42

    def test_min(self):
        assert _eval("min(3, 7)") == 3

    def test_max(self):
        assert _eval("max(3, 7)") == 7

    def test_floor(self):
        assert _eval("floor(3.7)") == 3

    def test_ceil(self):
        assert _eval("ceil(3.2)") == 4

    def test_clamp(self):
        assert _eval("clamp(15, 0, 10)") == 10
        assert _eval("clamp(-5, 0, 10)") == 0
        assert _eval("clamp(5, 0, 10)") == 5

    def test_cbrt(self):
        assert _eval("cbrt(27)") == pytest.approx(3.0)

    def test_round(self):
        assert _eval("round(3.7)") == 4

    def test_sum(self):
        assert _eval("sum(1, 2, 3, 4)") == 10

    def test_prod(self):
        assert _eval("prod(2, 3, 4)") == 24


# ---------------------------------------------------------------------------
# TestConditionals
# ---------------------------------------------------------------------------

class TestConditionals:
    def test_if_true(self):
        assert _eval("if(1 > 0, 10, 20)") == 10

    def test_if_false(self):
        assert _eval("if(1 > 2, 10, 20)") == 20

    def test_piecewise_three_tiers(self):
        # piecewise(x < 10, 1, x < 100, 2, 3)
        assert _eval("piecewise(x < 10, 1, x < 100, 2, 3)", {"x": 5}) == 1
        assert _eval("piecewise(x < 10, 1, x < 100, 2, 3)", {"x": 50}) == 2
        assert _eval("piecewise(x < 10, 1, x < 100, 2, 3)", {"x": 500}) == 3

    def test_comparison_gte(self):
        assert _eval("if(x >= 10, 1, 0)", {"x": 10}) == 1
        assert _eval("if(x >= 10, 1, 0)", {"x": 9}) == 0

    def test_comparison_eq(self):
        assert _eval("if(x == 5, 1, 0)", {"x": 5}) == 1

    def test_comparison_neq(self):
        assert _eval("if(x != 5, 1, 0)", {"x": 3}) == 1


# ---------------------------------------------------------------------------
# TestVariables
# ---------------------------------------------------------------------------

class TestVariables:
    def test_single_variable(self):
        assert _eval("x * 2", {"x": 5}) == 10

    def test_multiple_variables(self):
        assert _eval("x + y * z", {"x": 1, "y": 2, "z": 3}) == 7

    def test_predefined_names(self):
        result = _eval(
            "lifetime_earnings * multiplier",
            {"lifetime_earnings": 1e18, "multiplier": 150},
        )
        assert result == pytest.approx(1.5e20)

    def test_undefined_variable_raises(self):
        with pytest.raises(NameError):
            _eval("undefined_var + 1")


# ---------------------------------------------------------------------------
# TestSecurity
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_max_depth_rejects(self):
        # 60 nested parentheses should exceed depth limit of 50
        expr = "(" * 60 + "1" + ")" * 60
        with pytest.raises(ValueError, match="[Dd]epth"):
            compile_formula(expr)

    def test_no_attribute_access(self):
        with pytest.raises(Exception):
            _eval("x.__class__", {"x": 1})

    def test_no_import(self):
        with pytest.raises(Exception):
            _eval("__import__('os')")

    def test_no_subscript(self):
        with pytest.raises(Exception):
            _eval("x[0]", {"x": [1, 2, 3]})

    def test_ast_whitelist_enforced(self):
        # Attribute access should be caught by the whitelist
        with pytest.raises(Exception):
            compile_formula("x.__class__.__bases__")

    def test_dunder_names_forbidden(self):
        with pytest.raises(ValueError, match="[Dd]under"):
            compile_formula("__class__")


# ---------------------------------------------------------------------------
# TestPrestigeFormulas
# ---------------------------------------------------------------------------

class TestPrestigeFormulas:
    def test_adcap_angel_formula(self):
        # 150 * sqrt(lifetime_earnings / 1e15)
        result = _eval(
            "150 * sqrt(lifetime_earnings / 1e15)",
            {"lifetime_earnings": 1e18},
        )
        # sqrt(1e18 / 1e15) = sqrt(1000) ≈ 31.623
        # 150 * 31.623 ≈ 4743.4
        expected = 150 * math.sqrt(1e18 / 1e15)
        assert result == pytest.approx(expected)

    def test_cookie_clicker_formula(self):
        # cbrt(lifetime_earnings / 1e12)
        result = _eval(
            "cbrt(lifetime_earnings / 1e12)",
            {"lifetime_earnings": 1e18},
        )
        # cbrt(1e6) = 100
        expected = (1e18 / 1e12) ** (1 / 3)
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# TestCompiledFormula
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TestBigFloatVariables
# ---------------------------------------------------------------------------

class TestBigFloatVariables:
    """Formulas must work when variables are BigFloat values."""

    def test_sqrt_bigfloat(self):
        from idleframework.bigfloat import BigFloat
        result = _eval("sqrt(x)", {"x": BigFloat(16)})
        assert result == pytest.approx(4.0)

    def test_log10_bigfloat(self):
        from idleframework.bigfloat import BigFloat
        result = _eval("log10(x)", {"x": BigFloat(1000)})
        assert result == pytest.approx(3.0)

    def test_prestige_formula_with_bigfloat(self):
        """The actual prestige formula from MiniCap must work with BigFloat."""
        from idleframework.bigfloat import BigFloat
        result = _eval(
            "150 * sqrt(lifetime_earnings / 1e15)",
            {"lifetime_earnings": BigFloat(1e18)},
        )
        # 150 * sqrt(1e18 / 1e15) = 150 * sqrt(1000) ≈ 4743.4
        expected = 150 * math.sqrt(1000.0)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_floor_bigfloat(self):
        from idleframework.bigfloat import BigFloat
        result = _eval("floor(x)", {"x": BigFloat(3.7)})
        assert result == 3

    def test_abs_bigfloat(self):
        from idleframework.bigfloat import BigFloat
        result = _eval("abs(x)", {"x": BigFloat(-5)})
        assert result == pytest.approx(5.0)

    def test_min_max_bigfloat(self):
        from idleframework.bigfloat import BigFloat
        result = _eval("min(a, b)", {"a": BigFloat(10), "b": BigFloat(3)})
        assert result == pytest.approx(3.0)

    def test_arithmetic_with_bigfloat(self):
        """BigFloat arithmetic in formulas (no builtin calls) should work via operators."""
        from idleframework.bigfloat import BigFloat
        result = _eval("x * 2 + y", {"x": BigFloat(5), "y": BigFloat(3)})
        # BigFloat arithmetic returns BigFloat, which is fine
        assert float(result) == pytest.approx(13.0)

    def test_sqrt_large_bigfloat_not_inf(self):
        """sqrt of BigFloat beyond float range must not return inf."""
        from idleframework.bigfloat import BigFloat
        # 1.5e500 overflows float, but sqrt(1.5e500) = sqrt(1.5) * 10^250 is finite
        bf = BigFloat.from_components(1.5, 500)
        result = _eval("sqrt(x)", {"x": bf})
        assert result != float("inf"), "sqrt of large BigFloat must not return inf"
        assert result == pytest.approx(math.sqrt(1.5) * (10.0 ** 250), rel=1e-6)

    def test_log10_large_bigfloat(self):
        """log10 of BigFloat beyond float range must return correct result."""
        from idleframework.bigfloat import BigFloat
        bf = BigFloat.from_components(2.0, 500)
        result = _eval("log10(x)", {"x": bf})
        # log10(2e500) = log10(2) + 500
        expected = math.log10(2.0) + 500
        assert result == pytest.approx(expected, rel=1e-9)


class TestCompiledFormula:
    def test_has_source(self):
        f = compile_formula("x + 1")
        assert f.source == "x + 1"

    def test_has_code(self):
        f = compile_formula("42")
        assert f.code is not None

    def test_slots(self):
        assert hasattr(CompiledFormula, "__slots__")
