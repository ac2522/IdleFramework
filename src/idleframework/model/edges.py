"""Edge model for game graphs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Edge(BaseModel):
    """A directed edge in the game graph."""

    id: str
    source: str
    target: str
    edge_type: Literal[
        "resource_flow",
        "consumption",
        "production_target",
        "state_modifier",
        "activator",
        "trigger",
        "unlock_dependency",
        "upgrade_target",
    ]
    rate: float | None = None
    formula: str | None = None
    condition: str | None = None
    target_property: str | None = None
    modifier_mode: Literal["set", "add", "multiply"] | None = None
