"""Event types, formula tier classification, and chattering detection.

Events represent discrete state changes that separate analytical segments:
purchases, prestiges, unlocks, etc. Between events, the system of equations
is fixed and solvable analytically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    """Types of events that create segment boundaries."""

    PURCHASE = auto()
    PRESTIGE = auto()
    UNLOCK = auto()
    ACHIEVEMENT = auto()
    FREE_PURCHASE = auto()


class ChatteringError(Exception):
    """Raised when Zeno-like chattering is detected.

    This happens when too many purchases occur within a single epsilon window,
    indicating the engine should batch-evaluate all affordable candidates.
    """

    pass


@dataclass
class PurchaseEvent:
    """A purchase event in the simulation timeline."""

    time: float
    node_id: str
    count: int
    cost: float

    def __lt__(self, other: PurchaseEvent) -> bool:
        return self.time < other.time


# Maximum purchases allowed in a single epsilon window before chattering kicks in
MAX_PURCHASES_PER_EPSILON = 100

# Patterns for formula tier classification
_TIER1_VARS = {"count", "level", "owned"}
_TIER2_VARS = {"current_value"}
_TIER3_VARS = {"production_rate", "total_production", "rate"}

# Regex to find variable-like identifiers in a formula string
_IDENTIFIER_RE = re.compile(r"\b([a-z_][a-z_0-9]*)\b")

# Built-in function names and constants that are NOT variables
_BUILTINS = {
    "sqrt",
    "log",
    "log10",
    "exp",
    "abs",
    "min",
    "max",
    "floor",
    "ceil",
    "pow",
    "sin",
    "cos",
    "tan",
    "pi",
    "e",
    "if",
    "sum",
    "prod",
    "true",
    "false",
}


def classify_formula_tier(formula_expr: str) -> int:
    """Classify a formula expression into a tier.

    Tier 1: Only discrete values (count, level, owned) or constants.
            Pure piecewise analytical — fast path.
    Tier 2: Uses current_value with slowly-varying formulas.
            Evaluate once at segment start, constant within segment.
    Tier 3: Tight feedback loops (e.g., current_value * production_rate).
            Flagged as approximation_level: "numerical_fallback".

    Args:
        formula_expr: The formula string to classify.

    Returns:
        1, 2, or 3 indicating the tier.
    """
    identifiers = set(_IDENTIFIER_RE.findall(formula_expr))
    # Remove builtins and numeric-looking tokens
    variables = identifiers - _BUILTINS

    has_tier2 = bool(variables & _TIER2_VARS)
    has_tier3 = bool(variables & _TIER3_VARS)

    if has_tier3 and has_tier2:
        # Tight feedback: current_value coupled with production info
        return 3
    if has_tier3:
        return 3
    if has_tier2:
        return 2

    # Only tier-1 vars or pure constants
    return 1
