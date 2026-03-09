"""Closed-form solvers for idle game economics.

All formulas operate on plain floats for speed. BigFloat is used at the
caller level when values exceed float64 range.

Key formulas:
- bulk_cost: base * rate^owned * (rate^n - 1) / (rate - 1)
- max_affordable: floor(log_rate(currency * (rate-1) / (base * rate^owned) + 1))
- time_to_afford: cost / production_rate (constant case)
- generator_chain: product(counts) * product(rates) * t^depth / depth!
"""
from __future__ import annotations

import math


def bulk_cost(base: float, rate: float, owned: int, count: int) -> float:
    """Cost to buy `count` units of a generator.

    Formula: base * rate^owned * (rate^count - 1) / (rate - 1)
    When rate == 1: base * count
    """
    if count <= 0:
        return 0.0
    if abs(rate - 1.0) < 1e-12:
        return base * count
    return base * (rate ** owned) * ((rate ** count) - 1) / (rate - 1)


def max_affordable(currency: float, base: float, rate: float, owned: int) -> int:
    """Maximum units affordable with given currency.

    Inverse of bulk_cost. Returns floor of the analytical solution.
    """
    if currency <= 0:
        return 0
    if base <= 0:
        return 0

    if abs(rate - 1.0) < 1e-12:
        return int(currency / base)

    # n = floor(log_rate(currency * (rate - 1) / (base * rate^owned) + 1))
    rate_to_owned = rate ** owned
    inner = currency * (rate - 1) / (base * rate_to_owned) + 1
    if inner <= 0:
        return 0
    n = int(math.floor(math.log(inner) / math.log(rate)))

    # Verify and adjust (floating point can be off by 1)
    if n < 0:
        return 0
    while n > 0 and bulk_cost(base, rate, owned, n) > currency + 1e-10:
        n -= 1
    while bulk_cost(base, rate, owned, n + 1) <= currency + 1e-10:
        n += 1

    return n


def time_to_afford(
    cost: float,
    production_rate: float,
    current_balance: float = 0.0,
) -> float:
    """Time until balance reaches cost at constant production rate.

    Returns 0.0 if already affordable.
    Raises ValueError if production_rate is 0 and cost > balance.
    """
    remaining = cost - current_balance
    if remaining <= 0:
        return 0.0
    if production_rate <= 0:
        raise ValueError(
            f"Cannot afford cost={cost} with production_rate={production_rate} "
            f"and balance={current_balance}"
        )
    return remaining / production_rate


def generator_chain_output(
    chain_rates: list[float],
    counts: list[float],
    time: float,
) -> float:
    """Output of a generator chain over time.

    For a chain of depth n with rates r_i and counts c_i:
    output = product(c_i) * product(r_i) * t^depth / depth!

    This is the closed-form solution for nested generators where
    each level produces the level below it.
    """
    depth = len(chain_rates)
    if depth == 0 or time <= 0:
        return 0.0

    rate_product = math.prod(chain_rates)
    count_product = math.prod(counts)

    return count_product * rate_product * (time ** depth) / math.factorial(depth)


def production_accumulation(rate: float, duration: float) -> float:
    """Total production accumulated at constant rate over duration.

    Simply rate * duration (integral of constant).
    """
    return rate * duration
