"""GameDefinition — the static structure of an idle game."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator

from idleframework.model.edges import Edge
from idleframework.model.nodes import (
    NodeUnion,
    PrestigeLayer,
    Register,
    SacrificeNode,
    SynergyNode,
    TickspeedNode,
    Upgrade,
)


class GameDefinition(BaseModel):
    """Complete static definition of an idle game."""

    schema_version: str
    name: str
    description: str | None = None
    nodes: list[NodeUnion]
    edges: list[Edge]
    stacking_groups: dict[str, Literal["additive", "multiplicative", "percentage"]]
    time_unit: str = "seconds"
    tie_breaking: str = "lowest_cost"
    event_epsilon: float = 0.001
    free_purchase_threshold: float = 1e-5

    @model_validator(mode="after")
    def _validate_game(self) -> GameDefinition:
        self._validate_unique_node_ids()
        self._validate_unique_edge_ids()
        self._validate_edge_references()
        self._validate_upgrade_targets()
        self._validate_stacking_groups()
        self._validate_formulas()
        self._validate_tickspeed_singleton()
        self._validate_state_modifier_properties()
        return self

    def _validate_unique_node_ids(self) -> None:
        seen: set[str] = set()
        for node in self.nodes:
            if node.id in seen:
                raise ValueError(f"Duplicate node ID: {node.id!r}")
            seen.add(node.id)

    def _validate_unique_edge_ids(self) -> None:
        seen: set[str] = set()
        for edge in self.edges:
            if edge.id in seen:
                raise ValueError(f"Duplicate edge ID: {edge.id!r}")
            seen.add(edge.id)

    def _validate_edge_references(self) -> None:
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(
                    f"Edge {edge.id!r}: source {edge.source!r} does not reference an existing node"
                )
            if edge.target not in node_ids:
                raise ValueError(
                    f"Edge {edge.id!r}: target {edge.target!r} does not reference an existing node"
                )
            if edge.edge_type == "state_modifier" and not edge.formula:
                raise ValueError(f"Edge {edge.id!r}: state_modifier edge must have a formula")

    def _validate_upgrade_targets(self) -> None:
        node_ids = {n.id for n in self.nodes}
        for node in self.nodes:
            if isinstance(node, Upgrade) and node.target != "_all" and node.target not in node_ids:
                raise ValueError(
                    f"Target {node.target!r} on upgrade {node.id!r} "
                    f"does not reference a valid node ID"
                )

    def _validate_stacking_groups(self) -> None:
        for node in self.nodes:
            if isinstance(node, Upgrade) and node.stacking_group not in self.stacking_groups:
                raise ValueError(
                    f"Upgrade {node.id!r} references stacking_group "
                    f"{node.stacking_group!r} which is not defined in "
                    f"stacking_groups"
                )

    def _validate_formulas(self) -> None:
        from idleframework.dsl.compiler import compile_formula

        # Validate formula_expr on nodes
        for node in self.nodes:
            if isinstance(node, (PrestigeLayer, SacrificeNode, Register)):
                try:
                    compile_formula(node.formula_expr)
                except Exception as e:
                    raise ValueError(f"Formula validation failed on node {node.id!r}: {e}") from e
            if isinstance(node, SynergyNode):
                try:
                    compile_formula(node.formula_expr)
                except Exception as e:
                    raise ValueError(f"Formula validation failed on node {node.id!r}: {e}") from e

        # Validate formula on state_modifier edges
        for edge in self.edges:
            if edge.edge_type == "state_modifier" and edge.formula:
                try:
                    compile_formula(edge.formula)
                except Exception as e:
                    raise ValueError(f"Formula validation failed on edge {edge.id!r}: {e}") from e

    def _validate_tickspeed_singleton(self) -> None:
        ts_count = sum(1 for n in self.nodes if isinstance(n, TickspeedNode))
        if ts_count > 1:
            raise ValueError(f"At most one tickspeed node allowed, found {ts_count}")

    def _validate_state_modifier_properties(self) -> None:
        import typing

        def _is_numeric_type(annotation) -> bool:
            """Check if a type annotation is or contains float/int."""
            if annotation is float or annotation is int:
                return True
            origin = typing.get_origin(annotation)
            if origin is typing.Union:
                # float | None, Optional[float], etc.
                return any(
                    _is_numeric_type(a) for a in typing.get_args(annotation) if a is not type(None)
                )
            # Handle types.UnionType (Python 3.10+ X | Y syntax)
            if hasattr(annotation, "__args__"):
                origin_check = getattr(annotation, "__origin__", None)
                if origin_check is None and hasattr(annotation, "__args__"):
                    # types.UnionType (e.g., float | None)
                    return any(
                        _is_numeric_type(a) for a in annotation.__args__ if a is not type(None)
                    )
            return False

        node_map = {n.id: n for n in self.nodes}
        for edge in self.edges:
            if edge.edge_type == "state_modifier" and edge.target_property is not None:
                target_node = node_map.get(edge.target)
                if target_node is None:
                    continue  # caught by _validate_edge_references
                valid_fields = {
                    name
                    for name, info in type(target_node).model_fields.items()
                    if _is_numeric_type(info.annotation)
                }
                if edge.target_property not in valid_fields:
                    raise ValueError(
                        f"Edge {edge.id!r}: target_property {edge.target_property!r} "
                        f"is not a valid numeric field on {type(target_node).__name__}"
                    )

    def get_node(self, node_id: str) -> NodeUnion:
        """Get a node by ID. Raises KeyError if not found."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(f"Node {node_id!r} not found")

    def get_edges_from(self, node_id: str) -> list[Edge]:
        """Get all edges originating from the given node."""
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        """Get all edges targeting the given node."""
        return [e for e in self.edges if e.target == node_id]
