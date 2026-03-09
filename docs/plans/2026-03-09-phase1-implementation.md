# IdleFramework Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the complete Phase 1 Python library + CLI + Plotly reports + pytest suite as specified in the design document (Revision 4).

**Architecture:** Library-first — all components are modules within `idleframework` package. TDD throughout: every feature starts with a failing test. Components built in dependency order so each task has a working foundation. The design is malleable: Pydantic models can be extended, new node types added via PRs, and every math formula is independently testable against known analytical results and real game data.

**Tech Stack:** Python 3.12+, Pydantic v2, Lark, NetworkX, SciPy, Plotly, typer, pytest, Hypothesis

**Design Doc:** `docs/plans/2026-03-07-idleframework-design.md` (Revision 4)

---

## Directory Structure

```
idleframework/
├── pyproject.toml
├── src/
│   └── idleframework/
│       ├── __init__.py
│       ├── bigfloat.py              # Task 1
│       ├── dsl/
│       │   ├── __init__.py
│       │   ├── grammar.lark         # Task 3
│       │   ├── parser.py            # Task 3
│       │   └── compiler.py          # Task 3
│       ├── model/
│       │   ├── __init__.py
│       │   ├── nodes.py             # Task 4
│       │   ├── edges.py             # Task 4
│       │   ├── game.py              # Task 4
│       │   └── stacking.py          # Task 5
│       ├── graph/
│       │   ├── __init__.py
│       │   └── validation.py        # Task 6
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── solvers.py           # Task 8
│       │   ├── segments.py          # Task 9
│       │   └── events.py            # Task 9
│       ├── optimizer/
│       │   ├── __init__.py
│       │   ├── greedy.py            # Task 10
│       │   ├── beam.py              # Task 11
│       │   ├── mcts.py              # Task 12
│       │   └── bnb.py               # Task 12
│       ├── analysis/
│       │   ├── __init__.py
│       │   └── detectors.py         # Task 13
│       ├── reports/
│       │   ├── __init__.py
│       │   └── html.py              # Task 14
│       ├── export.py                # Task 15
│       └── cli.py                   # Task 15
├── tests/
│   ├── conftest.py
│   ├── test_bigfloat.py             # Task 1
│   ├── test_bigfloat_props.py       # Task 2
│   ├── test_dsl.py                  # Task 3
│   ├── test_model.py                # Task 4
│   ├── test_stacking.py             # Task 5
│   ├── test_graph.py                # Task 6
│   ├── test_simulator.py            # Task 7
│   ├── test_solvers.py              # Task 8
│   ├── test_segments.py             # Task 9
│   ├── test_greedy.py               # Task 10
│   ├── test_beam.py                 # Task 11
│   ├── test_mcts_bnb.py             # Task 12
│   ├── test_analysis.py             # Task 13
│   ├── test_reports.py              # Task 14
│   ├── test_cli.py                  # Task 15
│   ├── fixtures/
│   │   ├── minicap.json             # Task 7
│   │   ├── mediumcap.json           # Task 13
│   │   └── largecap.py              # Task 13 (procedural generator)
│   └── regressions/                 # Convention: bug-fix test cases
│       └── .gitkeep
└── docs/
    └── plans/
        └── ...
```

---

## Task 1: Project Setup + BigFloat Core

**Files:**
- Create: `pyproject.toml`
- Create: `src/idleframework/__init__.py`
- Create: `src/idleframework/bigfloat.py`
- Create: `tests/conftest.py`
- Create: `tests/test_bigfloat.py`

**Step 1: Initialize project**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "idleframework"
version = "0.1.0"
description = "Math-first framework for analyzing idle/incremental game balance"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "lark>=1.1",
    "networkx>=3.0",
    "scipy>=1.11",
    "plotly>=5.0",
    "typer>=0.9",
]

[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "hypothesis>=6.0",
    "mpmath>=1.3",
    "sympy>=1.12",
    "pytest-benchmark>=4.0",
]
dev = ["idleframework[test]", "ruff"]

[project.scripts]
idleframework = "idleframework.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/idleframework"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

```python
# src/idleframework/__init__.py
"""IdleFramework — math-first idle game balance analysis."""
__version__ = "0.1.0"
```

```python
# tests/conftest.py
"""Shared test fixtures and configuration."""
```

Run: `cd /home/zaia/Development/IdleFramework && git init && pip install -e ".[dev]"`

**Step 2: Write failing BigFloat tests**

```python
# tests/test_bigfloat.py
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
```

Run: `pytest tests/test_bigfloat.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'idleframework.bigfloat'`

**Step 3: Implement BigFloat**

```python
# src/idleframework/bigfloat.py
"""BigFloat: (mantissa, exponent) number type for idle game scale.

Design: mantissa in [1, 10), exponent is Python int (unlimited range).
Reference: break_infinity.js. 5-digit relative error tolerance.
"""
from __future__ import annotations

import math
from functools import total_ordering


_NAMED_SUFFIXES = [
    "", "Thousand", "Million", "Billion", "Trillion", "Quadrillion",
    "Quintillion", "Sextillion", "Septillion", "Octillion", "Nonillion",
    "Decillion", "Undecillion", "Duodecillion", "Tredecillion",
]
_SHORT_SUFFIXES = [
    "", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No",
    "Dc", "UDc", "DDc", "TDc",
]


@total_ordering
class BigFloat:
    """Arbitrary-scale floating point: (mantissa, exponent) where value = mantissa * 10^exponent."""

    __slots__ = ("mantissa", "exponent")

    def __init__(self, value: float | int = 0):
        if value == 0:
            self.mantissa = 0.0
            self.exponent = 0
            return
        if isinstance(value, BigFloat):
            self.mantissa = value.mantissa
            self.exponent = value.exponent
            return
        neg = value < 0
        abs_val = abs(float(value))
        if abs_val == 0:
            self.mantissa = 0.0
            self.exponent = 0
            return
        exp = math.floor(math.log10(abs_val))
        mant = abs_val / (10.0 ** exp)
        # Correct for floating point drift
        if mant >= 10.0:
            mant /= 10.0
            exp += 1
        elif mant < 1.0:
            mant *= 10.0
            exp -= 1
        self.mantissa = -mant if neg else mant
        self.exponent = exp

    @classmethod
    def from_components(cls, mantissa: float, exponent: int) -> BigFloat:
        """Create from pre-computed mantissa and exponent. Normalizes."""
        obj = cls.__new__(cls)
        if mantissa == 0:
            obj.mantissa = 0.0
            obj.exponent = 0
            return obj
        neg = mantissa < 0
        abs_m = abs(mantissa)
        if abs_m >= 10.0 or abs_m < 1.0:
            adj = math.floor(math.log10(abs_m))
            abs_m /= 10.0 ** adj
            exponent += adj
            if abs_m >= 10.0:
                abs_m /= 10.0
                exponent += 1
            elif abs_m < 1.0:
                abs_m *= 10.0
                exponent -= 1
        obj.mantissa = -abs_m if neg else abs_m
        obj.exponent = exponent
        return obj

    @property
    def is_zero(self) -> bool:
        return self.mantissa == 0.0

    def __float__(self) -> float:
        if self.is_zero:
            return 0.0
        if self.exponent > 308:
            return math.inf if self.mantissa > 0 else -math.inf
        if self.exponent < -324:
            return 0.0
        return self.mantissa * (10.0 ** self.exponent)

    def __add__(self, other: BigFloat) -> BigFloat:
        other = _coerce(other)
        if self.is_zero:
            return other
        if other.is_zero:
            return self
        # Align exponents
        diff = self.exponent - other.exponent
        if diff > 15:
            return self
        if diff < -15:
            return other
        if diff >= 0:
            m = self.mantissa + other.mantissa * (10.0 ** (-diff))
            return BigFloat.from_components(m, self.exponent)
        else:
            m = other.mantissa + self.mantissa * (10.0 ** diff)
            return BigFloat.from_components(m, other.exponent)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other: BigFloat) -> BigFloat:
        other = _coerce(other)
        return self.__add__(BigFloat.from_components(-other.mantissa, other.exponent))

    def __rsub__(self, other):
        other = _coerce(other)
        return other.__sub__(self)

    def __mul__(self, other: BigFloat) -> BigFloat:
        other = _coerce(other)
        if self.is_zero or other.is_zero:
            return BigFloat(0)
        return BigFloat.from_components(
            self.mantissa * other.mantissa,
            self.exponent + other.exponent,
        )

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other: BigFloat) -> BigFloat:
        other = _coerce(other)
        if other.is_zero:
            raise ZeroDivisionError("BigFloat division by zero")
        if self.is_zero:
            return BigFloat(0)
        return BigFloat.from_components(
            self.mantissa / other.mantissa,
            self.exponent - other.exponent,
        )

    def __rtruediv__(self, other):
        other = _coerce(other)
        return other.__truediv__(self)

    def __pow__(self, power: int | float) -> BigFloat:
        if self.is_zero:
            if power > 0:
                return BigFloat(0)
            raise ZeroDivisionError("0 ** non-positive")
        if isinstance(power, (int, float)):
            # log10(self) * power = (log10(mantissa) + exponent) * power
            neg = self.mantissa < 0
            abs_m = abs(self.mantissa)
            log_val = (math.log10(abs_m) + self.exponent) * power
            new_exp = math.floor(log_val)
            new_mant = 10.0 ** (log_val - new_exp)
            if neg and isinstance(power, int) and power % 2 == 1:
                new_mant = -new_mant
            return BigFloat.from_components(new_mant, int(new_exp))
        return NotImplemented

    def log10(self) -> float:
        """Return log10 of this value as a plain float."""
        if self.is_zero or self.mantissa < 0:
            raise ValueError(f"log10 undefined for {self}")
        return math.log10(self.mantissa) + self.exponent

    def __eq__(self, other) -> bool:
        try:
            other = _coerce(other)
        except TypeError:
            return NotImplemented
        if self.is_zero and other.is_zero:
            return True
        return self.exponent == other.exponent and abs(self.mantissa - other.mantissa) < 1e-10

    def __lt__(self, other) -> bool:
        other = _coerce(other)
        if self.mantissa >= 0 and other.mantissa < 0:
            return False
        if self.mantissa < 0 and other.mantissa >= 0:
            return True
        if self.mantissa >= 0:
            if self.exponent != other.exponent:
                return self.exponent < other.exponent
            return self.mantissa < other.mantissa
        else:
            if self.exponent != other.exponent:
                return self.exponent > other.exponent
            return self.mantissa < other.mantissa

    def __neg__(self) -> BigFloat:
        return BigFloat.from_components(-self.mantissa, self.exponent)

    def __abs__(self) -> BigFloat:
        return BigFloat.from_components(abs(self.mantissa), self.exponent)

    def __str__(self) -> str:
        if self.is_zero:
            return "0"
        return f"{self.mantissa:.2f}e{self.exponent}"

    def __repr__(self) -> str:
        return f"BigFloat({self.mantissa:.6f}e{self.exponent})"

    def __hash__(self) -> int:
        return hash((round(self.mantissa, 10), self.exponent))


def _coerce(value) -> BigFloat:
    if isinstance(value, BigFloat):
        return value
    if isinstance(value, (int, float)):
        return BigFloat(value)
    raise TypeError(f"Cannot coerce {type(value)} to BigFloat")


def format_bigfloat(value: BigFloat, style: str = "scientific") -> str:
    """Format BigFloat for display.

    Styles: scientific, engineering, named.
    """
    if value.is_zero:
        return "0"
    if style == "scientific":
        return f"{value.mantissa:.2f}e{value.exponent}"

    if style == "named" or style == "engineering":
        suffixes = _NAMED_SUFFIXES if style == "named" else _SHORT_SUFFIXES
        tier = value.exponent // 3
        if 0 <= tier < len(suffixes):
            display_mant = value.mantissa * (10.0 ** (value.exponent % 3))
            suffix = suffixes[tier]
            if suffix:
                return f"{display_mant:.2f} {suffix}"
            return f"{display_mant:.2f}"
        return f"{value.mantissa:.2f}e{value.exponent}"

    return str(value)
```

Run: `pytest tests/test_bigfloat.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: BigFloat core with arithmetic, pow/log, formatting, full test suite"
```

---

## Task 2: BigFloat Property-Based Tests (Hypothesis)

**Files:**
- Create: `tests/test_bigfloat_props.py`

**Step 1: Write property-based tests**

```python
# tests/test_bigfloat_props.py
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
```

Run: `pytest tests/test_bigfloat_props.py -v`
Expected: All PASS (Hypothesis explores edge cases)

**Step 2: Commit**

```bash
git add tests/test_bigfloat_props.py
git commit -m "test: BigFloat property-based tests with Hypothesis"
```

---

## Task 3: Formula DSL (Lark Parser + Bytecode Compiler)

**Files:**
- Create: `src/idleframework/dsl/__init__.py`
- Create: `src/idleframework/dsl/grammar.lark`
- Create: `src/idleframework/dsl/parser.py`
- Create: `src/idleframework/dsl/compiler.py`
- Create: `tests/test_dsl.py`

**Step 1: Write failing tests**

```python
# tests/test_dsl.py
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
        deep = "(" * 60 + "1" + ")" * 60
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
```

Run: `pytest tests/test_dsl.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 2: Implement Lark grammar**

```lark
// src/idleframework/dsl/grammar.lark
// Formula DSL grammar — LALR(1) compatible
// Operators: + - * / ** %
// Functions: sqrt, cbrt, log, log10, ln, abs, min, max, floor, ceil, clamp, round, sum, prod
// Conditionals: if(cond, then, else), piecewise(cond, val, ..., default)
// Comparisons: < <= > >= == !=

start: expr

?expr: or_expr

?or_expr: and_expr

?and_expr: comparison

?comparison: arith_expr (COMP_OP arith_expr)?
COMP_OP: ">=" | "<=" | "!=" | "==" | ">" | "<"

?arith_expr: term
    | arith_expr "+" term  -> add
    | arith_expr "-" term  -> sub

?term: factor
    | term "*" factor      -> mul
    | term "/" factor       -> div
    | term "%" factor      -> mod

?factor: unary
    | unary "**" factor    -> pow

?unary: atom
    | "-" unary            -> neg

?atom: NUMBER              -> number
    | NAME                 -> variable
    | "(" expr ")"
    | func_call

func_call: NAME "(" args ")"
args: expr ("," expr)*

NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
NUMBER: /[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?/

%ignore /\s+/
```

**Step 3: Implement parser and compiler**

```python
# src/idleframework/dsl/__init__.py
"""Formula DSL — Lark LALR(1) parser + Python bytecode compiler."""
```

```python
# src/idleframework/dsl/parser.py
"""Parse formula strings into Lark parse trees."""
from __future__ import annotations

from pathlib import Path
from lark import Lark

_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"
_parser = Lark(
    _GRAMMAR_PATH.read_text(),
    parser="lalr",
    maybe_placeholders=False,
)


def parse_formula(text: str) -> object:
    """Parse a formula string into a Lark parse tree."""
    return _parser.parse(text)
```

```python
# src/idleframework/dsl/compiler.py
"""Compile Lark parse trees to Python bytecode via ast.Expression.

Security: AST node whitelist enforced before compile(). Only these nodes
are permitted: BinOp, UnaryOp, Call, Name, Constant, Compare, IfExp.
No Attribute, Subscript, or other nodes that enable sandbox escape.
"""
from __future__ import annotations

import ast
import math
from typing import Any

from lark import Token, Tree

from idleframework.dsl.parser import parse_formula as _parse

MAX_DEPTH = 50

# Whitelisted AST node types
_ALLOWED_NODES = frozenset({
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name,
    ast.Constant, ast.Compare, ast.IfExp, ast.Load,
    # Operator nodes
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub,
    ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq,
})

# Safe builtins for evaluation
_SAFE_BUILTINS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "log": math.log,
    "log10": math.log10,
    "ln": math.log,
    "abs": abs,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
    "clamp": lambda val, lo, hi: max(lo, min(val, hi)),
    "round": round,
    "sum": sum,
    "prod": math.prod,
    "True": True,
    "False": False,
}


class CompiledFormula:
    """A compiled formula ready for repeated evaluation."""

    __slots__ = ("_code", "_source")

    def __init__(self, code: Any, source: str):
        self._code = code
        self._source = source

    @property
    def source(self) -> str:
        return self._source


def compile_formula(text: str) -> CompiledFormula:
    """Parse and compile a formula string to Python bytecode."""
    tree = _parse(text)
    ast_node = _tree_to_ast(tree, depth=0)
    expr = ast.Expression(body=ast_node)
    ast.fix_missing_locations(expr)
    _validate_whitelist(expr)
    code = compile(expr, f"<formula: {text[:50]}>", "eval")
    return CompiledFormula(code, text)


def evaluate_formula(formula: CompiledFormula, variables: dict[str, float] | None = None) -> float:
    """Evaluate a compiled formula with given variable bindings."""
    ns = dict(_SAFE_BUILTINS)
    if variables:
        ns.update(variables)
    return eval(formula._code, {"__builtins__": {}}, ns)


def _validate_whitelist(node: ast.AST) -> None:
    """Verify all AST nodes are in the whitelist. Raises ValueError if not."""
    for child in ast.walk(node):
        if type(child) not in _ALLOWED_NODES:
            raise ValueError(
                f"Disallowed AST node: {type(child).__name__}. "
                f"Only {sorted(n.__name__ for n in _ALLOWED_NODES)} are permitted."
            )


def _tree_to_ast(tree: Tree | Token, depth: int) -> ast.expr:
    """Convert Lark parse tree to Python AST."""
    if depth > MAX_DEPTH:
        raise ValueError(f"Formula exceeds maximum depth of {MAX_DEPTH}")

    if isinstance(tree, Token):
        if tree.type == "NUMBER":
            return ast.Constant(value=float(tree))
        if tree.type == "NAME":
            return ast.Name(id=str(tree), ctx=ast.Load())
        raise ValueError(f"Unexpected token: {tree}")

    d = depth + 1

    if tree.data == "start":
        return _tree_to_ast(tree.children[0], d)

    if tree.data == "number":
        return ast.Constant(value=float(tree.children[0]))

    if tree.data == "variable":
        name = str(tree.children[0])
        if name.startswith("__"):
            raise ValueError(f"Dunder names forbidden: {name}")
        return ast.Name(id=name, ctx=ast.Load())

    if tree.data == "neg":
        return ast.UnaryOp(op=ast.USub(), operand=_tree_to_ast(tree.children[0], d))

    # Binary operators
    _binops = {
        "add": ast.Add, "sub": ast.Sub, "mul": ast.Mult,
        "div": ast.Div, "mod": ast.Mod, "pow": ast.Pow,
    }
    if tree.data in _binops:
        return ast.BinOp(
            left=_tree_to_ast(tree.children[0], d),
            op=_binops[tree.data](),
            right=_tree_to_ast(tree.children[1], d),
        )

    # Comparison
    if tree.data == "comparison":
        left = _tree_to_ast(tree.children[0], d)
        op_str = str(tree.children[1])
        right = _tree_to_ast(tree.children[2], d)
        ops = {
            ">": ast.Gt, ">=": ast.GtE, "<": ast.Lt, "<=": ast.LtE,
            "==": ast.Eq, "!=": ast.NotEq,
        }
        return ast.Compare(left=left, ops=[ops[op_str]()], comparators=[right])

    # Function calls
    if tree.data == "func_call":
        func_name = str(tree.children[0])
        if func_name.startswith("__"):
            raise ValueError(f"Dunder function names forbidden: {func_name}")
        args_tree = tree.children[1]
        args = [_tree_to_ast(c, d) for c in args_tree.children]

        # Special handling for if() and piecewise()
        if func_name == "if" and len(args) == 3:
            return ast.IfExp(test=args[0], body=args[1], orelse=args[2])

        if func_name == "piecewise" and len(args) >= 3:
            # Build nested IfExp: piecewise(c1,v1,c2,v2,...,default)
            *pairs, default = args
            if len(pairs) % 2 != 0:
                raise ValueError("piecewise requires pairs of (condition, value) + default")
            result = default
            for i in range(len(pairs) - 2, -1, -2):
                result = ast.IfExp(test=pairs[i], body=pairs[i + 1], orelse=result)
            return result

        return ast.Call(
            func=ast.Name(id=func_name, ctx=ast.Load()),
            args=args,
            keywords=[],
        )

    # Fallthrough: try to process children
    if len(tree.children) == 1:
        return _tree_to_ast(tree.children[0], d)

    raise ValueError(f"Unhandled tree node: {tree.data}")
```

Run: `pytest tests/test_dsl.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/idleframework/dsl/ tests/test_dsl.py
git commit -m "feat: Formula DSL with Lark parser, bytecode compiler, AST whitelist security"
```

---

## Task 4: Game Model (Pydantic v2)

**Files:**
- Create: `src/idleframework/model/__init__.py`
- Create: `src/idleframework/model/nodes.py`
- Create: `src/idleframework/model/edges.py`
- Create: `src/idleframework/model/game.py`
- Create: `tests/test_model.py`

**Step 1: Write failing tests**

```python
# tests/test_model.py
"""Game model Pydantic v2 validation tests.

Tests node/edge construction, discriminated union serialization,
JSON Schema export, and validation error messages.
"""
import json
import pytest
from pydantic import ValidationError
from idleframework.model.nodes import (
    Resource, Generator, Upgrade, PrestigeLayer, Achievement,
    UnlockGate, ChoiceGroup, EndCondition, NodeUnion,
)
from idleframework.model.edges import Edge, EdgeUnion
from idleframework.model.game import GameDefinition


class TestNodeConstruction:
    def test_resource(self):
        r = Resource(id="gold", name="Gold", initial_value=0)
        assert r.type == "resource"
        assert r.name == "Gold"

    def test_generator(self):
        g = Generator(
            id="lemonade",
            name="Lemonade Stand",
            base_production=1.0,
            cost_base=4.0,
            cost_growth_rate=1.07,
            cycle_time=1.0,
        )
        assert g.type == "generator"
        assert g.cost_growth_rate == 1.07

    def test_upgrade_multiplicative(self):
        u = Upgrade(
            id="x3_lemon",
            name="x3 Lemonade",
            upgrade_type="multiplicative",
            magnitude=3.0,
            cost=1000.0,
            target="lemonade",
            stacking_group="cash_upgrades",
        )
        assert u.type == "upgrade"
        assert u.stacking_group == "cash_upgrades"

    def test_achievement_multi_threshold(self):
        a = Achievement(
            id="own_25_all",
            name="Own 25 of Everything",
            condition_type="multi_threshold",
            targets=[
                {"node_id": "lemonade", "property": "count", "threshold": 25},
                {"node_id": "newspaper", "property": "count", "threshold": 25},
            ],
            logic="and",
            bonus={"type": "multiplicative", "magnitude": 3.0},
            permanent=True,
        )
        assert a.condition_type == "multi_threshold"

    def test_end_condition(self):
        ec = EndCondition(
            id="win",
            condition_type="single_threshold",
            targets=[{"node_id": "gold", "property": "current_value", "threshold": 1e15}],
            logic="and",
        )
        assert ec.type == "end_condition"

    def test_tags(self):
        u = Upgrade(
            id="paid_boost",
            name="Paid Boost",
            upgrade_type="multiplicative",
            magnitude=10.0,
            cost=0,
            target="lemonade",
            stacking_group="paid",
            tags=["paid"],
        )
        assert "paid" in u.tags


class TestEdgeConstruction:
    def test_production_target(self):
        e = Edge(
            id="e1",
            source="lemonade",
            target="gold",
            edge_type="production_target",
        )
        assert e.edge_type == "production_target"

    def test_state_modifier_with_formula(self):
        e = Edge(
            id="e2",
            source="angel_register",
            target="lemonade",
            edge_type="state_modifier",
            formula="a * 0.02",
        )
        assert e.formula == "a * 0.02"


class TestGameDefinition:
    def test_minimal_game(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Test Game",
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {
                    "id": "miner", "type": "generator", "name": "Miner",
                    "base_production": 1.0, "cost_base": 10.0,
                    "cost_growth_rate": 1.15, "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
            stacking_groups={"default": "multiplicative"},
        )
        assert len(game.nodes) == 2
        assert len(game.edges) == 1

    def test_invalid_node_type_rejects(self):
        with pytest.raises(ValidationError):
            GameDefinition(
                schema_version="1.0",
                name="Bad",
                nodes=[{"id": "x", "type": "nonexistent"}],
                edges=[],
                stacking_groups={},
            )

    def test_duplicate_node_ids_reject(self):
        with pytest.raises(ValidationError, match="[Dd]uplicate"):
            GameDefinition(
                schema_version="1.0",
                name="Bad",
                nodes=[
                    {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                    {"id": "gold", "type": "resource", "name": "Gold2", "initial_value": 0},
                ],
                edges=[],
                stacking_groups={},
            )

    def test_json_roundtrip(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Roundtrip",
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
            ],
            edges=[],
            stacking_groups={},
        )
        json_str = game.model_dump_json()
        loaded = GameDefinition.model_validate_json(json_str)
        assert loaded.name == "Roundtrip"

    def test_json_schema_export(self):
        schema = GameDefinition.model_json_schema()
        assert "properties" in schema
        assert "nodes" in schema["properties"]


class TestGameLevelProperties:
    def test_stacking_groups(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Stacking Test",
            nodes=[],
            edges=[],
            stacking_groups={
                "angel_bonus": "additive",
                "cash_upgrades": "multiplicative",
                "milestone_bonuses": "multiplicative",
            },
        )
        assert game.stacking_groups["angel_bonus"] == "additive"

    def test_event_epsilon_default(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Defaults",
            nodes=[],
            edges=[],
            stacking_groups={},
        )
        assert game.event_epsilon == 0.001

    def test_free_purchase_threshold_default(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Defaults",
            nodes=[],
            edges=[],
            stacking_groups={},
        )
        assert game.free_purchase_threshold == 1e-5
```

Run: `pytest tests/test_model.py -v`
Expected: FAIL

**Step 2: Implement models**

```python
# src/idleframework/model/__init__.py
"""Game model — Pydantic v2 validated node/edge/game definitions."""
```

```python
# src/idleframework/model/nodes.py
"""Node type definitions — discriminated union on 'type' field."""
from __future__ import annotations

from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field


class NodeBase(BaseModel):
    """Shared properties for all node types."""
    id: str
    tags: list[str] = Field(default_factory=list)
    activation_mode: Literal["automatic", "interactive", "passive", "toggle"] = "automatic"
    cooldown_time: float | None = None


class Resource(NodeBase):
    type: Literal["resource"] = "resource"
    name: str
    initial_value: float = 0.0


class Generator(NodeBase):
    type: Literal["generator"] = "generator"
    name: str
    base_production: float
    cost_base: float
    cost_growth_rate: float
    cycle_time: float = 1.0


class NestedGenerator(NodeBase):
    type: Literal["nested_generator"] = "nested_generator"
    name: str
    target_generator: str
    production_rate: float
    cost_base: float
    cost_growth_rate: float


class Upgrade(NodeBase):
    type: Literal["upgrade"] = "upgrade"
    name: str
    upgrade_type: Literal["multiplicative", "additive", "percentage"]
    magnitude: float
    cost: float
    target: str
    stacking_group: str
    duration: float | None = None
    cooldown_time: float | None = None


class PrestigeLayer(NodeBase):
    type: Literal["prestige_layer"] = "prestige_layer"
    name: str = ""
    formula_expr: str
    layer_index: int
    reset_scope: list[str]
    persistence_scope: list[str] = Field(default_factory=list)
    bonus_type: str = "multiplicative"
    milestone_rules: list[dict[str, Any]] = Field(default_factory=list)


class SacrificeNode(NodeBase):
    type: Literal["sacrifice"] = "sacrifice"
    name: str = ""
    formula_expr: str
    reset_scope: list[str]
    bonus_type: str = "multiplicative"


class ConditionTarget(BaseModel):
    node_id: str
    property: str
    threshold: float


class Achievement(NodeBase):
    type: Literal["achievement"] = "achievement"
    name: str = ""
    condition_type: Literal["single_threshold", "multi_threshold", "collection", "compound"]
    targets: list[ConditionTarget]
    logic: str = "and"
    bonus: dict[str, Any] | None = None
    permanent: bool = True


class Manager(NodeBase):
    type: Literal["manager"] = "manager"
    name: str = ""
    target: str
    automation_type: str = "collect"


class ConverterIO(BaseModel):
    resource: str
    amount: float


class Converter(NodeBase):
    type: Literal["converter"] = "converter"
    name: str = ""
    inputs: list[ConverterIO]
    outputs: list[ConverterIO]
    rate: float = 1.0
    pull_mode: Literal["pull_any", "pull_all"] = "pull_any"


class ProbabilityNode(NodeBase):
    type: Literal["probability"] = "probability"
    name: str = ""
    expected_value: float
    variance: float = 0.0
    crit_chance: float = 0.0
    crit_multiplier: float = 1.0


class EndCondition(NodeBase):
    type: Literal["end_condition"] = "end_condition"
    name: str = ""
    condition_type: Literal["single_threshold", "multi_threshold", "collection", "compound"] = "single_threshold"
    targets: list[ConditionTarget] = Field(default_factory=list)
    logic: str = "and"


class UnlockGate(NodeBase):
    type: Literal["unlock_gate"] = "unlock_gate"
    name: str = ""
    condition_type: Literal["single_threshold", "multi_threshold", "collection", "compound"] = "single_threshold"
    targets: list[ConditionTarget] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    logic: str = "and"
    permanent: bool = True


class ChoiceGroup(NodeBase):
    type: Literal["choice_group"] = "choice_group"
    name: str = ""
    options: list[str]
    max_selections: int = 1
    respeccable: bool = False
    respec_cost: float | None = None


class Register(NodeBase):
    type: Literal["register"] = "register"
    name: str = ""
    formula_expr: str
    input_labels: list[dict[str, str]] = Field(default_factory=list)


class Gate(NodeBase):
    type: Literal["gate"] = "gate"
    name: str = ""
    mode: Literal["deterministic", "probabilistic"] = "deterministic"
    weights: list[float] = Field(default_factory=list)
    probabilities: list[float] = Field(default_factory=list)


class Queue(NodeBase):
    type: Literal["queue"] = "queue"
    name: str = ""
    delay: float
    capacity: float | None = None


NodeUnion = Annotated[
    Resource | Generator | NestedGenerator | Upgrade | PrestigeLayer |
    SacrificeNode | Achievement | Manager | Converter | ProbabilityNode |
    EndCondition | UnlockGate | ChoiceGroup | Register | Gate | Queue,
    Field(discriminator="type"),
]
```

```python
# src/idleframework/model/edges.py
"""Edge type definitions."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Edge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: Literal[
        "resource_flow", "consumption", "production_target",
        "state_modifier", "activator", "trigger",
        "unlock_dependency", "upgrade_target",
    ]
    rate: float | None = None
    formula: str | None = None
    condition: str | None = None


EdgeUnion = Edge  # Single edge model with edge_type discriminator
```

```python
# src/idleframework/model/game.py
"""Top-level game definition with validation."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, model_validator
from idleframework.model.nodes import NodeUnion
from idleframework.model.edges import Edge


class GameDefinition(BaseModel):
    schema_version: str
    name: str
    nodes: list[NodeUnion]
    edges: list[Edge]
    stacking_groups: dict[str, Literal["additive", "multiplicative", "percentage"]]
    time_unit: str = "seconds"
    tie_breaking: str = "lowest_cost"
    event_epsilon: float = 0.001
    free_purchase_threshold: float = 1e-5

    @model_validator(mode="after")
    def validate_unique_ids(self):
        ids = [n.id for n in self.nodes]
        dupes = [i for i in ids if ids.count(i) > 1]
        if dupes:
            raise ValueError(f"Duplicate node IDs: {set(dupes)}")
        return self

    def get_node(self, node_id: str):
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_edges_from(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.target == node_id]
```

Run: `pytest tests/test_model.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/idleframework/model/ tests/test_model.py
git commit -m "feat: Game model with Pydantic v2 — 17 node types, 8 edge types, JSON Schema export"
```

---

## Task 5: Stacking Groups

**Files:**
- Create: `src/idleframework/model/stacking.py`
- Create: `tests/test_stacking.py`

**Step 1: Write failing tests**

```python
# tests/test_stacking.py
"""Stacking group calculation tests.

Formula:
  additive group: group_mult = 1 + sum(bonuses)
  multiplicative group: group_mult = product(bonuses)
  percentage group: group_mult = 1 + sum(pcts/100)
  final = base * product(all_group_mults)

Reference: AdCap stacking model.
"""
import pytest
from idleframework.model.stacking import compute_final_multiplier


class TestStackingGroups:
    def test_single_multiplicative_group(self):
        groups = {
            "cash_upgrades": {"rule": "multiplicative", "bonuses": [3.0, 2.0, 5.0]},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(30.0)  # 3 * 2 * 5

    def test_single_additive_group(self):
        groups = {
            "angel_bonus": {"rule": "additive", "bonuses": [0.02, 0.02, 0.02]},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(1.06)  # 1 + 0.02 + 0.02 + 0.02

    def test_single_percentage_group(self):
        groups = {
            "gems": {"rule": "percentage", "bonuses": [10, 20, 5]},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(1.35)  # 1 + (10+20+5)/100

    def test_adcap_multi_group(self):
        """AdCap: final = base * (1 + angels*0.02) * product(cash) * product(angel_upg) * product(milestones)"""
        groups = {
            "angel_bonus": {"rule": "additive", "bonuses": [0.02] * 100},  # 100 angels * 2%
            "cash_upgrades": {"rule": "multiplicative", "bonuses": [3.0, 3.0]},
            "angel_upgrades": {"rule": "multiplicative", "bonuses": [7.77]},
            "milestones": {"rule": "multiplicative", "bonuses": [2.0, 3.0]},
        }
        result = compute_final_multiplier(groups)
        # (1 + 2.0) * 9.0 * 7.77 * 6.0 = 3 * 9 * 7.77 * 6 = 1258.74
        expected = (1 + 100 * 0.02) * (3.0 * 3.0) * 7.77 * (2.0 * 3.0)
        assert result == pytest.approx(expected, rel=1e-5)

    def test_empty_group(self):
        groups = {
            "empty_mult": {"rule": "multiplicative", "bonuses": []},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(1.0)  # Identity

    def test_no_groups(self):
        result = compute_final_multiplier({})
        assert result == pytest.approx(1.0)

    def test_additive_gold_mults(self):
        """AdCap gold multipliers: x12 + x12 = x24, NOT x144."""
        groups = {
            "gold_mults": {"rule": "additive", "bonuses": [12, 12]},
        }
        result = compute_final_multiplier(groups)
        assert result == pytest.approx(25.0)  # 1 + 12 + 12
```

Run: `pytest tests/test_stacking.py -v`
Expected: FAIL

**Step 2: Implement**

```python
# src/idleframework/model/stacking.py
"""Stacking group multiplier computation.

Formula:
  additive:       group_mult = 1 + sum(bonuses)
  multiplicative: group_mult = product(bonuses)
  percentage:     group_mult = 1 + sum(pcts) / 100
  Between groups: final = product(all group_mults)
"""
from __future__ import annotations

import math


def compute_final_multiplier(groups: dict[str, dict]) -> float:
    """Compute final multiplier from stacking groups.

    Args:
        groups: {"group_name": {"rule": "additive|multiplicative|percentage", "bonuses": [float, ...]}}

    Returns:
        Final multiplier (product of all group multipliers).
    """
    if not groups:
        return 1.0

    final = 1.0
    for group_name, group_data in groups.items():
        rule = group_data["rule"]
        bonuses = group_data["bonuses"]

        if rule == "additive":
            group_mult = 1.0 + sum(bonuses)
        elif rule == "multiplicative":
            group_mult = math.prod(bonuses) if bonuses else 1.0
        elif rule == "percentage":
            group_mult = 1.0 + sum(bonuses) / 100.0
        else:
            raise ValueError(f"Unknown stacking rule '{rule}' in group '{group_name}'")

        final *= group_mult

    return final
```

Run: `pytest tests/test_stacking.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/idleframework/model/stacking.py tests/test_stacking.py
git commit -m "feat: Stacking group computation — additive/multiplicative/percentage with between-group product"
```

---

## Task 6: Graph Validation (NetworkX)

**Files:**
- Create: `src/idleframework/graph/__init__.py`
- Create: `src/idleframework/graph/validation.py`
- Create: `tests/test_graph.py`

**Step 1: Write failing tests**

```python
# tests/test_graph.py
"""Graph validation tests — NetworkX-based structural analysis."""
import pytest
from idleframework.model.game import GameDefinition
from idleframework.graph.validation import (
    build_graph,
    validate_graph,
    find_dependency_cycles,
    check_edge_compatibility,
    check_tag_subgraph,
)


def _make_game(nodes, edges, **kwargs):
    return GameDefinition(
        schema_version="1.0",
        name="Test",
        nodes=nodes,
        edges=edges,
        stacking_groups=kwargs.get("stacking_groups", {}),
    )


class TestGraphBuilding:
    def test_builds_networkx_digraph(self):
        import networkx as nx
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
        )
        G = build_graph(game)
        assert isinstance(G, nx.DiGraph)
        assert G.number_of_nodes() == 2
        assert G.number_of_edges() == 1


class TestDependencyCycles:
    def test_no_cycles_in_simple_graph(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
        )
        cycles = find_dependency_cycles(game)
        assert len(cycles) == 0

    def test_resource_cycle_is_valid(self):
        """Resource flow cycles are valid feedback loops, not errors."""
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
                {"id": "e2", "source": "gold", "target": "miner", "edge_type": "consumption"},
            ],
        )
        cycles = find_dependency_cycles(game)
        # Resource cycles are valid — only unlock_dependency cycles are errors
        assert len(cycles) == 0

    def test_dependency_cycle_detected(self):
        """unlock_dependency cycles are errors."""
        game = _make_game(
            nodes=[
                {"id": "a", "type": "unlock_gate", "name": "A"},
                {"id": "b", "type": "unlock_gate", "name": "B"},
            ],
            edges=[
                {"id": "e1", "source": "a", "target": "b", "edge_type": "unlock_dependency"},
                {"id": "e2", "source": "b", "target": "a", "edge_type": "unlock_dependency"},
            ],
        )
        cycles = find_dependency_cycles(game)
        assert len(cycles) > 0


class TestEdgeCompatibility:
    def test_production_target_from_generator(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
        )
        errors = check_edge_compatibility(game)
        assert len(errors) == 0

    def test_invalid_edge_source_detected(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
            ],
            edges=[
                {"id": "e1", "source": "nonexistent", "target": "gold", "edge_type": "production_target"},
            ],
        )
        errors = check_edge_compatibility(game)
        assert len(errors) > 0


class TestTagSubgraph:
    def test_filter_removes_tagged_nodes(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15,
                 "cycle_time": 1.0, "tags": ["free"]},
                {"id": "boost", "type": "upgrade", "name": "Boost",
                 "upgrade_type": "multiplicative", "magnitude": 10.0, "cost": 0,
                 "target": "miner", "stacking_group": "paid", "tags": ["paid"]},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
                {"id": "e2", "source": "boost", "target": "miner", "edge_type": "upgrade_target"},
            ],
        )
        result = check_tag_subgraph(game, active_tags=["free"])
        assert "boost" in [n.id for n in result.removed_nodes]

    def test_broken_dependency_reported(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "paid_gate", "type": "unlock_gate", "name": "Gate", "tags": ["paid"]},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15,
                 "cycle_time": 1.0, "tags": ["free"]},
            ],
            edges=[
                {"id": "e1", "source": "paid_gate", "target": "miner", "edge_type": "unlock_dependency"},
                {"id": "e2", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
        )
        result = check_tag_subgraph(game, active_tags=["free"])
        assert len(result.broken_dependencies) > 0
```

Run: `pytest tests/test_graph.py -v`
Expected: FAIL

**Step 2: Implement**

```python
# src/idleframework/graph/__init__.py
"""Graph operations — NetworkX-based validation and analysis."""
```

```python
# src/idleframework/graph/validation.py
"""Graph validation: build NetworkX graph, detect cycles, check compatibility, tag filtering."""
from __future__ import annotations

from dataclasses import dataclass, field
import networkx as nx

from idleframework.model.game import GameDefinition


# Edge types that represent hard dependencies (cycles = errors)
_DEPENDENCY_EDGE_TYPES = frozenset({"unlock_dependency"})


def build_graph(game: GameDefinition) -> nx.DiGraph:
    """Build a NetworkX directed graph from a game definition."""
    G = nx.DiGraph()
    for node in game.nodes:
        G.add_node(node.id, data=node)
    for edge in game.edges:
        G.add_edge(edge.source, edge.target, data=edge)
    return G


def find_dependency_cycles(game: GameDefinition) -> list[list[str]]:
    """Find cycles in dependency edges (unlock_dependency). Resource cycles are valid."""
    dep_graph = nx.DiGraph()
    for node in game.nodes:
        dep_graph.add_node(node.id)
    for edge in game.edges:
        if edge.edge_type in _DEPENDENCY_EDGE_TYPES:
            dep_graph.add_edge(edge.source, edge.target)
    return list(nx.simple_cycles(dep_graph))


def check_edge_compatibility(game: GameDefinition) -> list[str]:
    """Check that edge sources and targets reference existing nodes."""
    node_ids = {n.id for n in game.nodes}
    errors = []
    for edge in game.edges:
        if edge.source not in node_ids:
            errors.append(f"Edge '{edge.id}': source '{edge.source}' not found")
        if edge.target not in node_ids:
            errors.append(f"Edge '{edge.id}': target '{edge.target}' not found")
    return errors


@dataclass
class TagFilterResult:
    """Result of filtering a game graph by active tags."""
    removed_nodes: list = field(default_factory=list)
    broken_dependencies: list[str] = field(default_factory=list)


def check_tag_subgraph(game: GameDefinition, active_tags: list[str]) -> TagFilterResult:
    """Filter game graph by active tags. Report removed nodes and broken dependencies."""
    result = TagFilterResult()
    active_set = set(active_tags)

    # Nodes that survive: no tags (available to all) or at least one tag in active set
    kept_ids = set()
    for node in game.nodes:
        if not node.tags or any(t in active_set for t in node.tags):
            kept_ids.add(node.id)
        else:
            result.removed_nodes.append(node)

    # Check for broken dependencies
    removed_ids = {n.id for n in result.removed_nodes}
    for edge in game.edges:
        if edge.edge_type in _DEPENDENCY_EDGE_TYPES:
            if edge.source in removed_ids and edge.target in kept_ids:
                result.broken_dependencies.append(
                    f"Node '{edge.target}' depends on removed node '{edge.source}' "
                    f"(edge '{edge.id}', type '{edge.edge_type}')"
                )

    return result
```

Run: `pytest tests/test_graph.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/idleframework/graph/ tests/test_graph.py
git commit -m "feat: Graph validation — NetworkX builder, dependency cycle detection, tag subgraph filtering"
```

---

## Task 7: Test Fixtures + RK4 Simulator

**Files:**
- Create: `tests/fixtures/minicap.json`
- Create: `tests/test_simulator.py`
- Create: `tests/conftest.py` (update)

**Step 1: Create MiniCap fixture**

```json
// tests/fixtures/minicap.json
{
    "schema_version": "1.0",
    "name": "MiniCap",
    "description": "Minimal AdCap-like game for unit testing. 3 generators, 10 upgrades, 1 prestige layer.",
    "stacking_groups": {
        "cash_upgrades": "multiplicative",
        "angel_bonus": "additive",
        "milestones": "multiplicative"
    },
    "nodes": [
        {"id": "cash", "type": "resource", "name": "Cash", "initial_value": 0},
        {"id": "angels", "type": "resource", "name": "Angels", "initial_value": 0},

        {"id": "lemonade", "type": "generator", "name": "Lemonade Stand",
         "base_production": 1.0, "cost_base": 4.0, "cost_growth_rate": 1.07, "cycle_time": 1.0},
        {"id": "newspaper", "type": "generator", "name": "Newspaper Delivery",
         "base_production": 60.0, "cost_base": 60.0, "cost_growth_rate": 1.15, "cycle_time": 3.0},
        {"id": "carwash", "type": "generator", "name": "Car Wash",
         "base_production": 720.0, "cost_base": 720.0, "cost_growth_rate": 1.14, "cycle_time": 6.0},

        {"id": "x3_lemon", "type": "upgrade", "name": "x3 Lemonade",
         "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 1000.0,
         "target": "lemonade", "stacking_group": "cash_upgrades"},
        {"id": "x3_news", "type": "upgrade", "name": "x3 Newspaper",
         "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 5000.0,
         "target": "newspaper", "stacking_group": "cash_upgrades"},
        {"id": "x3_wash", "type": "upgrade", "name": "x3 Car Wash",
         "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 25000.0,
         "target": "carwash", "stacking_group": "cash_upgrades"},
        {"id": "x3_all_1", "type": "upgrade", "name": "x3 All Profit",
         "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 100000.0,
         "target": "_all", "stacking_group": "cash_upgrades"},
        {"id": "x3_all_2", "type": "upgrade", "name": "x3 All Profit II",
         "upgrade_type": "multiplicative", "magnitude": 3.0, "cost": 500000.0,
         "target": "_all", "stacking_group": "cash_upgrades"},

        {"id": "angel_x2_lemon", "type": "upgrade", "name": "Angel x2 Lemonade",
         "upgrade_type": "multiplicative", "magnitude": 2.0, "cost": 10.0,
         "target": "lemonade", "stacking_group": "cash_upgrades", "tags": ["angel_upgrade"]},
        {"id": "angel_x2_news", "type": "upgrade", "name": "Angel x2 Newspaper",
         "upgrade_type": "multiplicative", "magnitude": 2.0, "cost": 25.0,
         "target": "newspaper", "stacking_group": "cash_upgrades", "tags": ["angel_upgrade"]},
        {"id": "angel_x2_wash", "type": "upgrade", "name": "Angel x2 Car Wash",
         "upgrade_type": "multiplicative", "magnitude": 2.0, "cost": 50.0,
         "target": "carwash", "stacking_group": "cash_upgrades", "tags": ["angel_upgrade"]},
        {"id": "angel_x7_all", "type": "upgrade", "name": "Angel x7.77 All",
         "upgrade_type": "multiplicative", "magnitude": 7.77, "cost": 1000.0,
         "target": "_all", "stacking_group": "cash_upgrades", "tags": ["angel_upgrade"]},
        {"id": "paid_x10", "type": "upgrade", "name": "x10 All (Paid)",
         "upgrade_type": "multiplicative", "magnitude": 10.0, "cost": 0.0,
         "target": "_all", "stacking_group": "cash_upgrades", "tags": ["paid"]},

        {"id": "prestige", "type": "prestige_layer",
         "name": "Angel Investors",
         "formula_expr": "150 * sqrt(lifetime_earnings / 1e15)",
         "layer_index": 0,
         "reset_scope": ["cash", "lemonade", "newspaper", "carwash",
                         "x3_lemon", "x3_news", "x3_wash", "x3_all_1", "x3_all_2"],
         "persistence_scope": ["angels", "angel_x2_lemon", "angel_x2_news",
                               "angel_x2_wash", "angel_x7_all", "paid_x10"],
         "bonus_type": "multiplicative"},

        {"id": "milestone_25_lemon", "type": "achievement",
         "name": "25 Lemonade Stands",
         "condition_type": "single_threshold",
         "targets": [{"node_id": "lemonade", "property": "count", "threshold": 25}],
         "logic": "and",
         "bonus": {"type": "multiplicative", "magnitude": 2.0, "target": "lemonade", "stacking_group": "milestones"},
         "permanent": true},

        {"id": "end", "type": "end_condition",
         "condition_type": "single_threshold",
         "targets": [{"node_id": "cash", "property": "current_value", "threshold": 1e15}],
         "logic": "and"}
    ],
    "edges": [
        {"id": "e_lemon_cash", "source": "lemonade", "target": "cash", "edge_type": "production_target"},
        {"id": "e_news_cash", "source": "newspaper", "target": "cash", "edge_type": "production_target"},
        {"id": "e_wash_cash", "source": "carwash", "target": "cash", "edge_type": "production_target"}
    ]
}
```

**Step 2: Write RK4 simulator tests**

```python
# tests/test_simulator.py
"""RK4 test simulator — exists ONLY for test validation.

This is NOT the production engine. It's a simple numerical simulator used
for convergence testing: run at multiple step sizes and verify results
converge toward the math engine's analytical answer.
"""
import json
import pytest
from pathlib import Path
from idleframework.bigfloat import BigFloat


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
```

Run: `pytest tests/test_simulator.py -v`
Expected: All PASS (simulator is pure Python, fixture validates via Pydantic)

**Step 3: Commit**

```bash
git add tests/fixtures/minicap.json tests/test_simulator.py
git commit -m "feat: MiniCap fixture + RK4 test simulator for convergence testing"
```

---

## Tasks 8-15: Remaining Components

I'll outline these as task headers with key details. Each follows the same TDD pattern.

---

### Task 8: Closed-Form Solvers

**Files:** `src/idleframework/engine/solvers.py`, `tests/test_solvers.py`

**Key tests:**
- `test_time_to_afford_constant_production` — `time = cost / rate`
- `test_bulk_cost_formula` — `base * rate^owned * (rate^n - 1) / (rate - 1)`
- `test_bulk_cost_rate_one` — singularity: falls back to `base * n`
- `test_max_affordable` — inverse of bulk cost
- `test_generator_chain_polynomial` — `t^n / n!` for homogeneous chains
- `test_time_to_afford_brent` — degree ≥ 5 polynomial uses `scipy.optimize.brentq`
- `test_production_accumulation` — integral of constant rate over time segment

**Implementation:** Each solver function takes BigFloat inputs and returns BigFloat. `time_to_afford()` branches: degree ≤ 1 → closed-form, degree 2-4 → numpy roots, degree ≥ 5 → Brent's method.

---

### Task 9: Piecewise Analytical Engine

**Files:** `src/idleframework/engine/segments.py`, `src/idleframework/engine/events.py`, `tests/test_segments.py`

**Key tests:**
- `test_single_segment_constant` — one generator, compute production over T seconds
- `test_purchase_creates_new_segment` — buy generator → new segment with updated production
- `test_free_purchase_threshold` — items where cost/balance < 1e-5 auto-purchased
- `test_chattering_detection` — max 100 purchases per epsilon
- `test_stale_event_recomputation` — candidates recomputed after every purchase
- `test_formula_tier_classification` — classify register formulas as Tier 1/2/3
- `test_convergence_vs_rk4` — piecewise engine matches RK4 simulator within tolerance

**Implementation:** `PiecewiseEngine` class. Takes a `GameDefinition`, maintains state (owned counts, resource values). `advance_to(target_time)` iterates segments.

---

### Task 10: Greedy Optimizer

**Files:** `src/idleframework/optimizer/greedy.py`, `tests/test_greedy.py`

**Key tests:**
- `test_greedy_buys_best_efficiency` — picks highest `delta_production / cost`
- `test_greedy_multiplicative_formula` — `production * (mult - 1) / cost`
- `test_greedy_additive_formula` — `(bonus * production) / cost`
- `test_greedy_on_minicap` — produces a purchase sequence, verifiable by hand
- `test_greedy_coupled_purchase` — angel upgrade net benefit accounting
- `test_greedy_under_200ms` — performance target for <100 nodes (pytest-benchmark)

**Implementation:** `GreedyOptimizer` wraps `PiecewiseEngine`. Each step: compute efficiency for all candidates within purchasing range (~20), pick best, advance time, purchase, repeat.

---

### Task 11: Beam Search Optimizer

**Files:** `src/idleframework/optimizer/beam.py`, `tests/test_beam.py`

**Key tests:**
- `test_beam_explores_alternatives` — beam width > 1 finds non-greedy paths
- `test_beam_deterministic` — same input → same output
- `test_beam_beats_greedy_on_multiplicative` — known case where mult upgrade is delayed by greedy
- `test_beam_width_parameter` — wider beam = better or equal result

**Implementation:** At each step, maintain top-K states sorted by total production at horizon. Expand each by all candidates.

---

### Task 12: MCTS + Branch-and-Bound

**Files:** `src/idleframework/optimizer/mcts.py`, `src/idleframework/optimizer/bnb.py`, `tests/test_mcts_bnb.py`

**Key tests (MCTS):**
- `test_mcts_epsilon_greedy_rollouts` — rollouts aren't all identical
- `test_mcts_seeded_determinism` — same seed → same result
- `test_mcts_anytime` — more iterations → better or equal result
- `test_mcts_beats_greedy` — on a known game where greedy is suboptimal

**Key tests (B&B):**
- `test_bnb_small_problem_optimal` — 3 candidates, depth 5 → provably optimal
- `test_bnb_respects_depth_limit` — depth 20 default
- `test_bnb_matches_exhaustive` — for tiny problem, matches brute force

---

### Task 13: Analysis Engine

**Files:** `src/idleframework/analysis/detectors.py`, `tests/test_analysis.py`, `tests/fixtures/mediumcap.json`, `tests/fixtures/largecap.py`

**Key tests:**
- `test_dead_upgrade_detection` — intentionally overpriced upgrade never purchased
- `test_progression_wall_detection` — growth rate drops below threshold
- `test_dominant_strategy_detection` — one route >2x better than alternatives
- `test_strategy_convergence` — two equally viable paths converge
- `test_free_vs_paid_comparison` — run optimizer both ways, report gap
- `test_broken_dependency_chain` — filtering paid tags breaks a gate
- `test_time_to_end_condition` — minimum time to reach EndCondition node
- `test_sensitivity_analysis` — perturb parameters, measure impact

**Fixtures:**
- `mediumcap.json`: 8 generators, 30 upgrades, 2 prestige layers
- `largecap.py`: Procedurally generates ~100 upgrades with known properties

---

### Task 14: Report Generator (Plotly)

**Files:** `src/idleframework/reports/html.py`, `tests/test_reports.py`

**Key tests:**
- `test_generates_html_file` — output is valid HTML with embedded Plotly
- `test_production_curves` — chart data matches analysis results
- `test_cdn_option` — `--cdn` flag uses CDN instead of inline JS
- `test_approximation_level_shown` — results labeled with approximation level

**Implementation:** Takes analysis results, generates Plotly figures, renders to self-contained HTML via `plotly.io.to_html()`.

---

### Task 15: CLI + Export

**Files:** `src/idleframework/cli.py`, `src/idleframework/export.py`, `tests/test_cli.py`

**Key tests:**
- `test_validate_command` — `idleframework validate minicap.json` exits 0
- `test_analyze_command` — produces analysis output
- `test_report_command` — creates HTML file
- `test_compare_command` — `--strategies "free,paid"` runs dual analysis
- `test_export_yaml` — JSON → YAML conversion
- `test_export_xml` — JSON → XML conversion
- `test_invalid_file_error_message` — clear error for bad input

**Implementation:** typer app with subcommands mirroring design doc CLI examples.

---

## Execution Order

| Task | Component | Dependencies | Estimated Commits |
|------|-----------|-------------|-------------------|
| 1 | Project Setup + BigFloat | None | 1 |
| 2 | BigFloat Hypothesis | Task 1 | 1 |
| 3 | Formula DSL | Task 1 | 1 |
| 4 | Game Model (Pydantic) | None | 1 |
| 5 | Stacking Groups | Task 4 | 1 |
| 6 | Graph Validation | Task 4 | 1 |
| 7 | Fixtures + RK4 Simulator | Task 4 | 1 |
| 8 | Closed-Form Solvers | Tasks 1, 3 | 1 |
| 9 | Piecewise Engine | Tasks 4, 5, 6, 8 | 2 |
| 10 | Greedy Optimizer | Task 9 | 1 |
| 11 | Beam Search | Task 10 | 1 |
| 12 | MCTS + B&B | Task 10 | 1 |
| 13 | Analysis Engine | Tasks 10, 7 | 2 |
| 14 | Report Generator | Task 13 | 1 |
| 15 | CLI + Export | Tasks 13, 14 | 1 |

**Parallelizable:** Tasks 1-2 and 4-6 can run in parallel (no dependencies between BigFloat and Game Model). Tasks 3 and 7 can overlap.

**Total:** ~17 commits, 15 tasks.

---

Plan complete and saved to `docs/plans/2026-03-09-phase1-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

Which approach?
