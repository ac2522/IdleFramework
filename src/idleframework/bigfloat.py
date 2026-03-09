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
