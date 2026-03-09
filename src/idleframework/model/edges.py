"""Edge type definitions."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Edge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: Literal[
        "resource_flow", "consumption", "production_target",
        "state_modifier", "activator", "trigger",
        "unlock_dependency", "upgrade_target",
    ]
    rate: float | None = None
    formula: str | None = None
    condition: str | None = None


EdgeUnion = Edge  # Single edge model with edge_type discriminator
