"""Top-level game definition with validation."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, model_validator
from idleframework.model.nodes import NodeUnion
from idleframework.model.edges import Edge


class GameDefinition(BaseModel):
    schema_version: str
    name: str
    nodes: list[NodeUnion]
    edges: list[Edge]
    stacking_groups: dict[str, Literal["additive", "multiplicative", "percentage"]]
    time_unit: str = "seconds"
    tie_breaking: str = "lowest_cost"
    event_epsilon: float = 0.001
    free_purchase_threshold: float = 1e-5

    @model_validator(mode="after")
    def validate_unique_ids(self):
        ids = [n.id for n in self.nodes]
        dupes = [i for i in ids if ids.count(i) > 1]
        if dupes:
            raise ValueError(f"Duplicate node IDs: {set(dupes)}")
        return self

    def get_node(self, node_id: str):
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_edges_from(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.target == node_id]
