"""RK4 Simulator — test-only module for numerical validation.

This is NOT part of the IdleFramework library. It exists solely as a test
harness to validate analytical solutions against numerical integration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def rk4_step(
    state: dict[str, float],
    production_rates: dict[str, float],
    dt: float,
) -> dict[str, float]:
    """Single RK4 step.

    For constant production rates, RK4 is exact (since the ODE is dy/dt = c,
    which has zero higher derivatives). This function is general enough to
    support time-varying rates via the event system.

    Parameters
    ----------
    state : dict mapping resource_id -> current value
    production_rates : dict mapping resource_id -> rate per second
    dt : time step size

    Returns
    -------
    New state dict (does not mutate the input).
    """
    # For constant rates, all k values are identical: k = rate * dt
    # But we implement full RK4 for correctness when rates change between steps.
    k1 = {rid: production_rates.get(rid, 0.0) * dt for rid in state}
    k2 = {rid: production_rates.get(rid, 0.0) * dt for rid in state}
    k3 = {rid: production_rates.get(rid, 0.0) * dt for rid in state}
    k4 = {rid: production_rates.get(rid, 0.0) * dt for rid in state}

    new_state = {}
    for rid in state:
        new_state[rid] = state[rid] + (
            k1[rid] + 2.0 * k2[rid] + 2.0 * k3[rid] + k4[rid]
        ) / 6.0

    return new_state


def simulate_constant_production(
    initial: dict[str, float],
    rates: dict[str, float],
    duration: float,
    dt: float = 0.01,
) -> dict[str, float]:
    """Run RK4 simulation with constant production rates for given duration.

    Parameters
    ----------
    initial : dict mapping resource_id -> initial value
    rates : dict mapping resource_id -> constant rate per second
    duration : total simulation time in seconds
    dt : time step size (smaller = more accurate)

    Returns
    -------
    Final state dict after simulation.
    """
    state = dict(initial)
    t = 0.0
    while t < duration - 1e-12:
        step = min(dt, duration - t)
        state = rk4_step(state, rates, step)
        t += step
    return state


EventChecker = Callable[[float, dict[str, float]], list[dict[str, Any]]]


def simulate_with_events(
    initial: dict[str, float],
    rates: dict[str, float],
    duration: float,
    dt: float = 0.01,
    event_checker: EventChecker | None = None,
) -> dict[str, float]:
    """Run RK4 with optional event checking at each step.

    The event_checker callback is invoked after each RK4 step with the
    current (time, state). It returns a list of event dicts that can
    modify rates or state. Supported event types:

    - {"type": "set_rate", "resource": str, "value": float}
      Updates the production rate for a resource.
    - {"type": "set_value", "resource": str, "value": float}
      Sets a resource to an exact value.

    Parameters
    ----------
    initial : dict mapping resource_id -> initial value
    rates : dict mapping resource_id -> initial rate per second
    duration : total simulation time in seconds
    dt : time step size
    event_checker : optional callback(time, state) -> list[event_dict]

    Returns
    -------
    Final state dict after simulation.
    """
    state = dict(initial)
    current_rates = dict(rates)
    t = 0.0

    while t < duration - 1e-12:
        step = min(dt, duration - t)
        state = rk4_step(state, current_rates, step)
        t += step

        if event_checker is not None:
            events = event_checker(t, state)
            for event in events:
                etype = event["type"]
                if etype == "set_rate":
                    current_rates[event["resource"]] = event["value"]
                elif etype == "set_value":
                    state[event["resource"]] = event["value"]

    return state
