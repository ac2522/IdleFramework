"""Event types for the piecewise engine."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PurchaseEvent:
    """Represents a scheduled purchase at a future time."""
    time: float
    node_id: str
    count: int = 1
    cost: float = 0.0

    def __lt__(self, other: PurchaseEvent) -> bool:
        return self.time < other.time
