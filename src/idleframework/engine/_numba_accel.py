"""Numba-accelerated inner loops for engine hot paths (stub).

These functions provide Numba-accelerated alternatives to engine hot paths.
Currently a stub — not imported by segments.py or solvers.py. Integration
is deferred until profiling identifies bottlenecks worth accelerating.

When Numba is available, functions are JIT-compiled. Otherwise, the pure-Python
fallback is used transparently.
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
