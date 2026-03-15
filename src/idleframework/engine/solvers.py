"""Closed-form solvers for common idle/incremental game calculations.

These functions compute exact (or near-exact) answers for standard idle game
math problems without simulation. They use BigFloat for overflow-safe
game-scale arithmetic and scipy.optimize.brentq for higher-degree polynomial
root-finding.

Key formulas implemented:
- Geometric series for bulk purchase costs
- Logarithmic inverse for max-affordable calculations
- Generator chain production (t^n/n! for homogeneous rates)
- Polynomial time-to-afford via Brent's method
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from idleframework.bigfloat import BigFloat

try:
    from idleframework.engine._numba_accel import bulk_purchase_cost_fast as _fast_bulk
    _HAS_FAST = True
except Exception:
    _HAS_FAST = False

if TYPE_CHECKING:
    pass

# Tolerance for detecting rate == 1.0 (geometric series singularity)
_RATE_ONE_TOLERANCE = 1e-10


def time_to_afford(cost: BigFloat, production_rate: BigFloat) -> BigFloat:
    """Compute time needed to afford a cost at a constant production rate.

    Formula: time = cost / production_rate

    Args:
        cost: The target cost to reach.
        production_rate: Constant resource generation per second.

    Returns:
        Time in seconds as a BigFloat.

    Raises:
        ValueError: If production_rate is zero.
    """
    if production_rate._is_zero():
        raise ValueError("production_rate must be non-zero")
    return cost / production_rate


def bulk_purchase_cost(
    base: BigFloat, rate: BigFloat, owned: int, quantity: int
) -> BigFloat:
    """Compute the total cost of buying multiple items with geometric scaling.

    Each successive item costs `rate` times more than the previous one.
    The k-th item (0-indexed from first purchase) costs: base * rate^(owned + k).

    For rate != 1: total = base * rate^owned * (rate^quantity - 1) / (rate - 1)
    For rate == 1: total = base * quantity  (all items cost the same)

    Args:
        base: Base cost of the first item (when owned == 0).
        rate: Cost multiplier per item owned.
        owned: Number of items already owned (shifts the cost curve).
        quantity: Number of items to purchase.

    Returns:
        Total cost as a BigFloat. Returns BigFloat(0) if quantity is 0.
    """
    if quantity <= 0:
        return BigFloat(0)

    # Fast path: when both base and rate fit in float64 (exponent == 0),
    # delegate to the Numba-accelerated implementation.
    if _HAS_FAST and isinstance(base, BigFloat) and isinstance(rate, BigFloat):
        if base.exponent == 0 and rate.exponent == 0:
            result = _fast_bulk(base.mantissa, rate.mantissa, owned, quantity)
            return BigFloat(result)

    rate_f = float(rate)

    # Check for rate == 1.0 singularity
    if abs(rate_f - 1.0) < _RATE_ONE_TOLERANCE:
        # All items cost the same: base * quantity
        return base * BigFloat(quantity)

    # General geometric series:
    # sum_{k=0}^{n-1} base * rate^(owned+k) = base * rate^owned * (rate^n - 1) / (rate - 1)
    rate_to_owned = rate ** owned
    rate_to_n = rate ** quantity
    numerator = rate_to_n - BigFloat(1)
    denominator = rate - BigFloat(1)

    return base * rate_to_owned * (numerator / denominator)


def max_affordable(
    currency: BigFloat, base: BigFloat, rate: BigFloat, owned: int
) -> int:
    """Compute the maximum number of items affordable given current currency.

    This is the inverse of bulk_purchase_cost: find the largest n such that
    bulk_purchase_cost(base, rate, owned, n) <= currency.

    For rate != 1: n = floor(log_rate(currency * (rate-1) / (base * rate^owned) + 1))
    For rate == 1: n = floor(currency / base)

    Args:
        currency: Available currency as a BigFloat.
        base: Base cost of the first item.
        rate: Cost multiplier per item.
        owned: Number of items already owned.

    Returns:
        Maximum number of items purchasable (int, >= 0).
    """
    if currency <= BigFloat(0):
        return 0

    rate_f = float(rate)

    if abs(rate_f - 1.0) < _RATE_ONE_TOLERANCE:
        # rate == 1: each item costs base, so n = floor(currency / base)
        n = int(float(currency / base))
        return max(n, 0)

    # General case:
    # bulk_cost(n) = base * rate^owned * (rate^n - 1) / (rate - 1) <= currency
    # rate^n - 1 <= currency * (rate - 1) / (base * rate^owned)
    # rate^n <= currency * (rate - 1) / (base * rate^owned) + 1
    # n <= log_rate(currency * (rate - 1) / (base * rate^owned) + 1)
    rate_to_owned = rate ** owned
    denominator = base * rate_to_owned

    if denominator._is_zero():
        return 0

    inner = currency * (rate - BigFloat(1)) / denominator + BigFloat(1)

    if inner <= BigFloat(0):
        return 0

    # n = floor(log(inner) / log(rate))
    log_inner = inner.log10()
    log_rate = rate.log10()

    if log_rate <= 0:
        return 0

    n = int(math.floor(log_inner / log_rate))

    # Clamp to 0
    n = max(n, 0)

    # Due to floating-point imprecision, verify and adjust:
    # Make sure we can actually afford n items
    if n > 0:
        actual_cost = bulk_purchase_cost(base, rate, owned, n)
        if actual_cost > currency:
            n -= 1

    # Check if we can afford one more
    next_cost = bulk_purchase_cost(base, rate, owned, n + 1)
    if next_cost <= currency:
        n += 1

    return max(n, 0)


def generator_chain_production(
    time: float,
    chain_rates: list[float],
    initial_counts: list[int] | None = None,
) -> float:
    """Compute production from an n-tier generator chain.

    In idle games, generators form chains: tier N generates tier N-1 units.
    For a chain of n tiers all producing at rate r, the bottom tier
    accumulates r^n * t^n / n! units (Kongregate "Math of Idle Games").

    For heterogeneous rates [r_0, r_1, ..., r_{n-1}]:
        production = product(r_i) * t^n / n!

    With initial_counts, additional terms account for units present at t=0
    at each tier, which contribute polynomial terms of lower degree.

    Args:
        time: Elapsed time in seconds.
        chain_rates: Production rate for each tier, from bottom (index 0)
                     to top (index n-1). The top tier generates the tier below it.
        initial_counts: Optional initial unit counts at each tier.
                        If None, assumes all tiers start at 0 except the top
                        tier which has 1 unit.

    Returns:
        Total production at the bottom tier (index 0) as a float.
    """
    n = len(chain_rates)

    if n == 0:
        return 0.0

    if time <= 0.0:
        return 0.0

    if initial_counts is None:
        # Default: 1 unit at the top tier, 0 elsewhere
        # Production at bottom = product(rates) * t^n / n!
        # This is the standard generator chain formula
        rate_product = math.prod(chain_rates)
        return rate_product * (time ** n) / math.factorial(n)

    # With initial counts: each tier i with c_i units at t=0 contributes
    # to the bottom tier's accumulated production by propagating down
    # through all tiers below and integrating at each level.
    #
    # Contribution of c_i at tier i:
    #   c_i * product(rates[0:i+1]) * t^(i+1) / (i+1)!
    #
    # Derivation (2-tier example, rates=[r0, r1], c_1=1):
    #   dN_0/dt = r1 * c_1  =>  N_0(t) = r1 * c_1 * t
    #   Production = integral(r0 * N_0(s), 0, t) = r0 * r1 * c_1 * t^2 / 2

    total = 0.0

    for i in range(n):
        if initial_counts[i] == 0:
            continue
        rate_product = math.prod(chain_rates[: i + 1])
        contribution = (
            initial_counts[i] * rate_product * (time ** (i + 1)) / math.factorial(i + 1)
        )
        total += contribution

    return total


def time_to_afford_polynomial(
    cost: float, production_coefficients: list[float]
) -> float:
    """Compute time to accumulate `cost` when production is polynomial in time.

    Production rate at time t: P(t) = sum(c_i * t^i) for i = 0..degree
    Total accumulated at time t: integral_0^t P(s) ds = sum(c_i * t^(i+1) / (i+1))
    Solve for t such that the integral equals `cost`.

    Methods by degree:
    - Degree 0 (constant rate): t = cost / c_0
    - Degree 1 (linear rate):   quadratic formula on c_0*t + c_1*t^2/2 = cost
    - Degree 2+:                Brent's method (scipy.optimize.brentq)

    Args:
        cost: Target accumulated production.
        production_coefficients: Coefficients [c_0, c_1, c_2, ...] where
            P(t) = c_0 + c_1*t + c_2*t^2 + ...

    Returns:
        Time as a float.

    Raises:
        ValueError: If no positive root exists.
    """
    if cost <= 0.0:
        return 0.0

    if not production_coefficients:
        raise ValueError("production_coefficients must be non-empty")

    degree = len(production_coefficients) - 1

    # Strip trailing zeros to get true degree
    while degree > 0 and production_coefficients[degree] == 0.0:
        degree -= 1

    if degree == 0:
        # Constant production: integral = c_0 * t = cost
        c0 = production_coefficients[0]
        if c0 <= 0:
            raise ValueError("Constant production rate must be positive")
        return cost / c0

    if degree == 1:
        # Linear production: integral = c_0*t + c_1*t^2/2 = cost
        # c_1/2 * t^2 + c_0 * t - cost = 0
        c0 = production_coefficients[0]
        c1 = production_coefficients[1]
        a = c1 / 2.0
        b = c0
        c = -cost
        discriminant = b * b - 4.0 * a * c
        if discriminant < 0:
            raise ValueError("No positive solution exists")
        t = (-b + math.sqrt(discriminant)) / (2.0 * a)
        return t

    # Degree 2+: use Brent's method
    from scipy.optimize import brentq

    def accumulated(t: float) -> float:
        """Accumulated production at time t minus cost."""
        total = 0.0
        for i, c in enumerate(production_coefficients[: degree + 1]):
            total += c * t ** (i + 1) / (i + 1)
        return total - cost

    # Estimate upper bracket from the highest-degree term
    # c_n * t^(n+1) / (n+1) ~ cost  =>  t ~ ((n+1)*cost/c_n)^(1/(n+1))
    c_n = production_coefficients[degree]
    upper = ((degree + 1) * cost / c_n) ** (1.0 / (degree + 1))
    # Ensure the bracket actually contains the root
    upper = max(upper, 1.0) * 2.0
    for _ in range(100):
        if accumulated(upper) >= 0:
            break
        upper *= 2.0
    else:
        raise ValueError(
            "Could not bracket root for polynomial solver: "
            "production may be zero or negative"
        )

    t_solution = brentq(accumulated, 0.0, upper, xtol=1e-12)
    return float(t_solution)


def production_at_time(
    rate: BigFloat, count: int, time: BigFloat, cycle_time: float = 1.0
) -> BigFloat:
    """Compute total production of generators over a time period.

    Formula: result = rate * count * time / cycle_time

    Args:
        rate: Base production per cycle per generator.
        count: Number of generators.
        time: Total elapsed time.
        cycle_time: Seconds per production cycle (default 1.0).

    Returns:
        Total production as a BigFloat.
    """
    return rate * BigFloat(count) * time / BigFloat(cycle_time)


def efficiency_score(delta_production: BigFloat, cost: BigFloat) -> float:
    """Compute the efficiency (bang-for-buck) of a purchase.

    This is the fundamental greedy metric for idle game optimizers:
    how much additional production per unit of cost.

    Formula: delta_production / cost

    Args:
        delta_production: Additional production gained from the purchase.
        cost: Cost of the purchase.

    Returns:
        Efficiency as a plain float (for easy comparison/sorting).
    """
    if cost._is_zero():
        return float("inf") if not delta_production._is_zero() else 0.0
    return float(delta_production / cost)


# -- Aliases for optimizer compatibility ------------------------------------

def bulk_cost(
    base: float, rate: float, owned: int, count: int
) -> float:
    """Plain-float wrapper around bulk_purchase_cost for optimizer use."""
    result = bulk_purchase_cost(BigFloat(base), BigFloat(rate), owned, count)
    return float(result)
