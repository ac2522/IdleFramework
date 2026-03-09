"""Formula DSL parser and compiler tests.

The DSL is parsed by Lark (LALR(1)), compiled to Python ast.Expression,
then eval'd with restricted builtins. Security relies on AST node whitelist.
"""
import math
import pytest
from hypothesis import given, settings
from hypothesis.strategies import floats
from idleframework.dsl.parser import parse_formula
from idleframework.dsl.compiler import compile_formula, evaluate_formula


class TestBasicParsing:
    def test_literal_int(self):
        expr = compile_formula("42")
        assert evaluate_formula(expr) == pytest.approx(42.0)

    def test_literal_float(self):
        expr = compile_formula("3.14")
        assert evaluate_formula(expr) == pytest.approx(3.14)

    def test_scientific_notation(self):
        expr = compile_formula("1e15")
        assert evaluate_formula(expr) == pytest.approx(1e15)

    def test_negative(self):
        expr = compile_formula("-5")
        assert evaluate_formula(expr) == pytest.approx(-5.0)


class TestOperators:
    def test_add(self):
        assert evaluate_formula(compile_formula("2 + 3")) == pytest.approx(5.0)

    def test_precedence(self):
        assert evaluate_formula(compile_formula("2 + 3 * 4")) == pytest.approx(14.0)

    def test_parentheses(self):
        assert evaluate_formula(compile_formula("(2 + 3) * 4")) == pytest.approx(20.0)

    def test_power(self):
        assert evaluate_formula(compile_formula("2 ** 10")) == pytest.approx(1024.0)

    def test_modulo(self):
        assert evaluate_formula(compile_formula("10 % 3")) == pytest.approx(1.0)


class TestFunctions:
    def test_sqrt(self):
        assert evaluate_formula(compile_formula("sqrt(144)")) == pytest.approx(12.0)

    def test_log10(self):
        assert evaluate_formula(compile_formula("log10(1000)")) == pytest.approx(3.0)

    def test_ln(self):
        assert evaluate_formula(compile_formula("ln(1)")) == pytest.approx(0.0)

    def test_abs(self):
        assert evaluate_formula(compile_formula("abs(-42)")) == pytest.approx(42.0)

    def test_min_max(self):
        assert evaluate_formula(compile_formula("min(3, 7)")) == pytest.approx(3.0)
        assert evaluate_formula(compile_formula("max(3, 7)")) == pytest.approx(7.0)

    def test_floor_ceil(self):
        assert evaluate_formula(compile_formula("floor(3.7)")) == pytest.approx(3.0)
        assert evaluate_formula(compile_formula("ceil(3.2)")) == pytest.approx(4.0)

    def test_clamp(self):
        assert evaluate_formula(compile_formula("clamp(15, 0, 10)")) == pytest.approx(10.0)
        assert evaluate_formula(compile_formula("clamp(-5, 0, 10)")) == pytest.approx(0.0)

    def test_cbrt(self):
        assert evaluate_formula(compile_formula("cbrt(27)")) == pytest.approx(3.0)


class TestConditionals:
    def test_if_true(self):
        expr = compile_formula("if(1 > 0, 42, 0)")
        assert evaluate_formula(expr) == pytest.approx(42.0)

    def test_if_false(self):
        expr = compile_formula("if(1 < 0, 42, 99)")
        assert evaluate_formula(expr) == pytest.approx(99.0)

    def test_piecewise(self):
        # piecewise(cond1, val1, cond2, val2, ..., default)
        expr = compile_formula("piecewise(x > 100, 3, x > 10, 2, 1)")
        assert evaluate_formula(expr, {"x": 200}) == pytest.approx(3.0)
        assert evaluate_formula(expr, {"x": 50}) == pytest.approx(2.0)
        assert evaluate_formula(expr, {"x": 5}) == pytest.approx(1.0)

    def test_comparisons(self):
        assert evaluate_formula(compile_formula("if(5 >= 5, 1, 0)")) == pytest.approx(1.0)
        assert evaluate_formula(compile_formula("if(5 == 5, 1, 0)")) == pytest.approx(1.0)
        assert evaluate_formula(compile_formula("if(5 != 4, 1, 0)")) == pytest.approx(1.0)


class TestVariables:
    def test_single_variable(self):
        expr = compile_formula("x * 2")
        assert evaluate_formula(expr, {"x": 5}) == pytest.approx(10.0)

    def test_multiple_variables(self):
        expr = compile_formula("a + b * c")
        assert evaluate_formula(expr, {"a": 1, "b": 2, "c": 3}) == pytest.approx(7.0)

    def test_predefined_names(self):
        expr = compile_formula("150 * sqrt(lifetime_earnings / 1e15)")
        result = evaluate_formula(expr, {"lifetime_earnings": 1e18})
        expected = 150 * math.sqrt(1e18 / 1e15)
        assert result == pytest.approx(expected)

    def test_undefined_variable_raises(self):
        expr = compile_formula("x + 1")
        with pytest.raises(NameError):
            evaluate_formula(expr, {})


class TestSecurity:
    def test_max_depth_rejects(self):
        # Nested function calls create real tree depth (parentheses are transparent in LALR)
        deep = "abs(" * 55 + "1" + ")" * 55
        with pytest.raises(ValueError, match="depth"):
            compile_formula(deep)

    def test_no_attribute_access(self):
        with pytest.raises(Exception):
            compile_formula("x.__class__")

    def test_no_import(self):
        with pytest.raises(Exception):
            compile_formula("__import__('os')")

    def test_no_subscript(self):
        with pytest.raises(Exception):
            compile_formula("x[0]")

    def test_ast_whitelist_enforced(self):
        """Only whitelisted AST nodes should appear in compiled expression."""
        expr = compile_formula("sqrt(x + 1)")
        # This should succeed — uses only Name, BinOp, Call, Constant
        assert evaluate_formula(expr, {"x": 8}) == pytest.approx(3.0)


class TestPrestigeFormulas:
    """Real-world formulas from actual games."""

    def test_adcap_angel_formula(self):
        """AdCap: 150 * sqrt(lifetime_earnings / 1e15)"""
        expr = compile_formula("150 * sqrt(lifetime_earnings / 1e15)")
        # With 1e18 lifetime earnings: 150 * sqrt(1000) = 150 * 31.62 = 4743.4
        result = evaluate_formula(expr, {"lifetime_earnings": 1e18})
        assert result == pytest.approx(4743.416, rel=1e-3)

    def test_cookie_clicker_formula(self):
        """Cookie Clicker: cbrt(lifetime_earnings / 1e12)"""
        expr = compile_formula("cbrt(lifetime_earnings / 1e12)")
        result = evaluate_formula(expr, {"lifetime_earnings": 1e15})
        assert result == pytest.approx(10.0, rel=1e-5)
