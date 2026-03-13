"""Numba-accelerated inner loops for engine hot paths.

These functions are used when Numba is available, with pure-Python
fallback when it's not installed.
"""
try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*args, **kwargs):
        def decorator(f):
            return f
        if args and callable(args[0]):
            return args[0]
        return decorator


@njit(cache=True)
def bulk_purchase_cost_fast(base: float, growth: float, owned: int, count: int) -> float:
    """Compute cost of buying count units starting from owned."""
    if abs(growth - 1.0) < 1e-12:
        return base * count
    total = 0.0
    for i in range(count):
        total += base * growth ** (owned + i)
    return total


MAX_FLOAT64 = 1e308

def can_use_numba(value: float) -> bool:
    """Check if a value is within float64 range for Numba."""
    return HAS_NUMBA and abs(value) < MAX_FLOAT64
