"""Numba-accelerated hot-path functions.

These operate on float64 primitives (not BigFloat).
Falls back to pure Python if Numba is not installed.
"""
from __future__ import annotations

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*args, **kwargs):
        """No-op decorator when Numba is unavailable."""
        def wrapper(fn):
            return fn
        if args and callable(args[0]):
            return args[0]
        return wrapper


@njit(cache=True)
def bulk_purchase_cost_fast(
    base: float, rate: float, owned: int, count: int,
) -> float:
    """Compute bulk purchase cost: base * rate^owned * (rate^count - 1) / (rate - 1).

    For rate == 1: base * count.
    """
    if count <= 0:
        return 0.0
    if abs(rate - 1.0) < 1e-12:
        return base * count
    return base * (rate ** owned) * (rate ** count - 1.0) / (rate - 1.0)


MAX_FLOAT64 = 1e308

def can_use_numba(value: float) -> bool:
    """Check if a value is within float64 range for Numba."""
    return HAS_NUMBA and abs(value) < MAX_FLOAT64
