"""BigFloat: (mantissa, exponent) number type for idle game math.

Represents numbers as mantissa * 10^exponent where mantissa is in [1, 10)
for positive values and (-10, -1] for negative values.
Zero is the special case: mantissa=0.0, exponent=0.

Inspired by break_infinity.js. Designed for overflow-free arithmetic on
astronomically large numbers common in idle/incremental games.
"""

from __future__ import annotations

import math
from functools import total_ordering
from typing import Union

# Maximum exponent difference before smaller operand is negligible in addition
_EXP_GAP_THRESHOLD = 15

# Named number suffixes for formatting
_NAMED_SUFFIXES = [
    (3, "Thousand"),
    (6, "Million"),
    (9, "Billion"),
    (12, "Trillion"),
    (15, "Quadrillion"),
    (18, "Quintillion"),
    (21, "Sextillion"),
    (24, "Septillion"),
    (27, "Octillion"),
    (30, "Nonillion"),
    (33, "Decillion"),
]

# Short engineering suffixes
_ENGINEERING_SUFFIXES = [
    (3, "K"),
    (6, "M"),
    (9, "B"),
    (12, "T"),
    (15, "Qa"),
    (18, "Qi"),
    (21, "Sx"),
    (24, "Sp"),
    (27, "Oc"),
    (30, "No"),
    (33, "Dc"),
]


def _normalize(mantissa: float, exponent: int) -> tuple[float, int]:
    """Normalize mantissa to [1, 10) for positive, (-10, -1] for negative.

    Returns (mantissa, exponent) tuple.
    """
    if mantissa == 0.0:
        return 0.0, 0

    if math.isnan(mantissa):
        raise ValueError("Cannot create BigFloat from NaN")
    if math.isinf(mantissa):
        return mantissa, exponent

    negative = mantissa < 0
    abs_m = abs(mantissa)

    # Use log10 to find the shift needed
    log_m = math.log10(abs_m)
    shift = math.floor(log_m)

    new_mantissa = abs_m / (10.0 ** shift)
    new_exponent = exponent + shift

    # Fix floating-point edge cases where new_mantissa might be
    # outside [1, 10) due to log10 rounding
    while new_mantissa >= 10.0:
        new_mantissa /= 10.0
        new_exponent += 1
    while 0 < new_mantissa < 1.0:
        new_mantissa *= 10.0
        new_exponent -= 1

    if negative:
        new_mantissa = -new_mantissa

    return new_mantissa, int(new_exponent)


Numeric = Union[int, float, "BigFloat"]


@total_ordering
class BigFloat:
    """Overflow-free floating-point number using (mantissa, exponent) representation.

    mantissa * 10^exponent, with mantissa normalized to [1, 10) for positive values.
    """

    __slots__ = ("mantissa", "exponent")

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("BigFloat is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("BigFloat is immutable")

    def __init__(self, value: Numeric = 0) -> None:
        if isinstance(value, BigFloat):
            object.__setattr__(self, "mantissa", value.mantissa)
            object.__setattr__(self, "exponent", value.exponent)
            return

        if isinstance(value, (int, float)):
            fval = float(value)
            if fval == 0.0:
                object.__setattr__(self, "mantissa", 0.0)
                object.__setattr__(self, "exponent", 0)
            else:
                m, e = _normalize(fval, 0)
                object.__setattr__(self, "mantissa", m)
                object.__setattr__(self, "exponent", e)
            return

        raise TypeError(f"Cannot create BigFloat from {type(value).__name__}")

    @classmethod
    def from_components(cls, mantissa: float, exponent: int) -> BigFloat:
        """Create a BigFloat from explicit mantissa and exponent, re-normalizing."""
        bf = object.__new__(cls)
        if mantissa == 0.0:
            object.__setattr__(bf, "mantissa", 0.0)
            object.__setattr__(bf, "exponent", 0)
        else:
            m, e = _normalize(mantissa, exponent)
            object.__setattr__(bf, "mantissa", m)
            object.__setattr__(bf, "exponent", e)
        return bf

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce(other: Numeric) -> BigFloat:
        if isinstance(other, BigFloat):
            return other
        return BigFloat(other)

    def _is_zero(self) -> bool:
        return self.mantissa == 0.0

    # ------------------------------------------------------------------
    # Arithmetic
    # ------------------------------------------------------------------

    def __add__(self, other: Numeric) -> BigFloat:
        other = self._coerce(other)

        if self._is_zero():
            return BigFloat(other)
        if other._is_zero():
            return BigFloat(self)

        # Align to the larger exponent
        if self.exponent >= other.exponent:
            big, small = self, other
        else:
            big, small = other, self

        exp_diff = big.exponent - small.exponent
        if exp_diff > _EXP_GAP_THRESHOLD:
            return BigFloat(big)

        # Shift small mantissa down
        adjusted_small = small.mantissa * (10.0 ** (-exp_diff))
        new_mantissa = big.mantissa + adjusted_small
        return BigFloat.from_components(new_mantissa, big.exponent)

    def __radd__(self, other: Numeric) -> BigFloat:
        return self.__add__(other)

    def __sub__(self, other: Numeric) -> BigFloat:
        other = self._coerce(other)
        return self.__add__(-other)

    def __rsub__(self, other: Numeric) -> BigFloat:
        other = self._coerce(other)
        return other.__sub__(self)

    def __mul__(self, other: Numeric) -> BigFloat:
        other = self._coerce(other)

        if self._is_zero() or other._is_zero():
            return BigFloat(0)

        new_mantissa = self.mantissa * other.mantissa
        new_exponent = self.exponent + other.exponent
        return BigFloat.from_components(new_mantissa, new_exponent)

    def __rmul__(self, other: Numeric) -> BigFloat:
        return self.__mul__(other)

    def __truediv__(self, other: Numeric) -> BigFloat:
        other = self._coerce(other)

        if other._is_zero():
            raise ZeroDivisionError("BigFloat division by zero")

        if self._is_zero():
            return BigFloat(0)

        new_mantissa = self.mantissa / other.mantissa
        new_exponent = self.exponent - other.exponent
        return BigFloat.from_components(new_mantissa, new_exponent)

    def __rtruediv__(self, other: Numeric) -> BigFloat:
        other = self._coerce(other)
        return other.__truediv__(self)

    def __pow__(self, power: Numeric) -> BigFloat:
        if isinstance(power, BigFloat):
            power = float(power)
        power = float(power)

        if power == 0.0:
            return BigFloat(1)
        if self._is_zero():
            if power > 0:
                return BigFloat(0)
            raise ZeroDivisionError("0 raised to negative power")
        if power == 1.0:
            return BigFloat(self)

        # Handle negative base
        negative_result = False
        abs_mantissa = self.mantissa
        if abs_mantissa < 0:
            # Negative base: only works for integer powers
            if power != int(power):
                raise ValueError("Negative BigFloat raised to non-integer power")
            abs_mantissa = -abs_mantissa
            negative_result = int(power) % 2 == 1

        # log10(m * 10^e) = log10(m) + e
        log10_val = math.log10(abs_mantissa) + self.exponent
        # (m * 10^e)^p = 10^(p * log10_val)
        new_log = power * log10_val

        # Split into new exponent (integer part) and mantissa (fractional part)
        new_exponent = math.floor(new_log)
        new_mantissa = 10.0 ** (new_log - new_exponent)

        if negative_result:
            new_mantissa = -new_mantissa

        return BigFloat.from_components(new_mantissa, int(new_exponent))

    def __neg__(self) -> BigFloat:
        if self._is_zero():
            return BigFloat(0)
        bf = object.__new__(BigFloat)
        object.__setattr__(bf, "mantissa", -self.mantissa)
        object.__setattr__(bf, "exponent", self.exponent)
        return bf

    def __abs__(self) -> BigFloat:
        if self.mantissa >= 0:
            return BigFloat(self)
        return -self

    def __mod__(self, other: Numeric) -> BigFloat:
        other = self._coerce(other)
        if other._is_zero():
            raise ZeroDivisionError("BigFloat modulo by zero")
        # Use float modulo to avoid precision issues from division + floor
        return BigFloat(float(self) % float(other))

    def __rmod__(self, other: Numeric) -> BigFloat:
        other = self._coerce(other)
        return other.__mod__(self)

    def floor(self) -> int:
        """Return the floor as an integer."""
        if self._is_zero():
            return 0
        if self.exponent < 0:
            # |value| < 1
            return -1 if self.mantissa < 0 else 0
        val = float(self)
        if not math.isfinite(val):
            raise OverflowError("BigFloat too large for integer floor")
        return math.floor(val)

    def ceil(self) -> int:
        """Return the ceiling as an integer."""
        if self._is_zero():
            return 0
        if self.exponent < 0:
            # |value| < 1
            return 0 if self.mantissa < 0 else 1
        val = float(self)
        if not math.isfinite(val):
            raise OverflowError("BigFloat too large for integer ceil")
        return math.ceil(val)

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------

    def log10(self) -> float:
        """Return log base 10 as a plain float.

        Key insight: log10(m * 10^e) = log10(m) + e
        """
        if self._is_zero():
            raise ValueError("log10(0) is undefined")
        if self.mantissa < 0:
            raise ValueError("log10 of negative number is undefined")
        return math.log10(self.mantissa) + self.exponent

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (BigFloat, int, float)):
            return NotImplemented
        other = self._coerce(other)  # type: ignore[arg-type]

        if self._is_zero() and other._is_zero():
            return True

        # Both must have same sign
        if (self.mantissa > 0) != (other.mantissa > 0):
            if self._is_zero() or other._is_zero():
                return False
            return False

        return self.exponent == other.exponent and round(self.mantissa, 10) == round(other.mantissa, 10)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, (BigFloat, int, float)):
            return NotImplemented
        other = self._coerce(other)  # type: ignore[arg-type]

        # Handle signs
        self_neg = self.mantissa < 0
        other_neg = other.mantissa < 0
        self_zero = self._is_zero()
        other_zero = other._is_zero()

        if self_zero and other_zero:
            return False
        if self_neg and not other_neg and not other_zero:
            return True
        if not self_neg and not self_zero and other_neg:
            return False
        if self_zero:
            return other.mantissa > 0
        if other_zero:
            return self.mantissa < 0

        # Same sign
        if not self_neg:
            # Both positive
            if self.exponent != other.exponent:
                return self.exponent < other.exponent
            return self.mantissa < other.mantissa
        else:
            # Both negative: larger exponent means more negative
            if self.exponent != other.exponent:
                return self.exponent > other.exponent
            return self.mantissa < other.mantissa  # more negative mantissa = smaller

    def __hash__(self) -> int:
        if self._is_zero():
            return hash((0.0, 0))
        # Round mantissa to avoid float comparison issues
        return hash((round(self.mantissa, 10), self.exponent))

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def __float__(self) -> float:
        if self._is_zero():
            return 0.0
        try:
            return self.mantissa * (10.0 ** self.exponent)
        except OverflowError:
            return math.inf if self.mantissa > 0 else -math.inf

    def __int__(self) -> int:
        return int(float(self))

    def __bool__(self) -> bool:
        return not self._is_zero()

    def __str__(self) -> str:
        if self._is_zero():
            return "0"
        if -3 <= self.exponent <= 6:
            # Display as normal number for reasonable ranges
            val = float(self)
            if val == int(val):
                return str(int(val))
            return f"{val:.6g}"
        return f"{self.mantissa:.3f}e{self.exponent}"

    def __repr__(self) -> str:
        return f"BigFloat({self.mantissa}, e{self.exponent})"


# ---------------------------------------------------------------------------
# Formatting helper
# ---------------------------------------------------------------------------

def format_bigfloat(value: BigFloat, style: str = "scientific") -> str:
    """Format a BigFloat for display.

    Styles:
        scientific  - "1.23e15"
        named       - "1.23 Trillion"
        engineering - "1.23 Qa"
    """
    if value._is_zero():
        return "0"

    if style == "scientific":
        return f"{value.mantissa:.2f}e{value.exponent}"

    if style == "named":
        return _format_with_suffixes(value, _NAMED_SUFFIXES)

    if style == "engineering":
        return _format_with_suffixes(value, _ENGINEERING_SUFFIXES)

    raise ValueError(f"Unknown format style: {style!r}")


def _format_with_suffixes(value: BigFloat, suffixes: list[tuple[int, str]]) -> str:
    """Format using a suffix table."""
    exp = value.exponent

    if exp < 3:
        # Small enough to display as a plain number
        val = float(value)
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}"

    # Find the best matching suffix
    best_exp = None
    best_name = None
    for threshold, name in reversed(suffixes):
        if exp >= threshold:
            best_exp = threshold
            best_name = name
            break

    if best_name is None:
        return f"{value.mantissa:.2f}e{exp}"

    # Adjust mantissa to match the suffix
    shift = exp - best_exp
    display_mantissa = value.mantissa * (10.0 ** shift)
    return f"{display_mantissa:.2f} {best_name}"
