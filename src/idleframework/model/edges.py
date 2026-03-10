"""Edge model for game graphs."""

from __future__ import annotations

from typing import Literal, Optional

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
    rate: Optional[float] = None
    formula: Optional[str] = None
    condition: Optional[str] = None
