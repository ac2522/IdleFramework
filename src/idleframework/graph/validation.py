"""Graph validation — cycles, compatibility, tag filtering, topological sort."""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.nodes import Generator, NestedGenerator, Upgrade


@dataclass
class TagFilterResult:
    """Result of filtering a game graph by active tags."""

    removed_nodes: list[str] = field(default_factory=list)
    broken_dependencies: list[dict[str, str]] = field(default_factory=list)


def build_graph(game: GameDefinition) -> nx.DiGraph:
    """Create a NetworkX DiGraph from a game definition.

    Nodes have a ``data`` attribute with the Pydantic node model.
    Edges have a ``data`` attribute with the Edge model.
    """
    g = nx.DiGraph()
    for node in game.nodes:
        g.add_node(node.id, data=node)
    for edge in game.edges:
        g.add_edge(edge.source, edge.target, data=edge)
    return g


def find_dependency_cycles(game: GameDefinition) -> list[list[str]]:
    """Find cycles in unlock_dependency edges only.

    Resource flow cycles are valid feedback loops and are ignored.
    Returns a list of cycles, where each cycle is a list of node IDs.
    """
    dep_graph = nx.DiGraph()
    for node in game.nodes:
        dep_graph.add_node(node.id)
    for edge in game.edges:
        if edge.edge_type == "unlock_dependency":
            dep_graph.add_edge(edge.source, edge.target)

    return list(nx.simple_cycles(dep_graph))


def check_edge_compatibility(game: GameDefinition) -> list[str]:
    """Check edges for referential integrity and semantic constraints.

    Returns a list of error strings (empty means valid).
    """
    errors: list[str] = []
    node_map = {n.id: n for n in game.nodes}

    for edge in game.edges:
        # Check that source and target exist
        if edge.source not in node_map:
            errors.append(
                f"Edge {edge.id!r}: source {edge.source!r} does not reference an existing node"
            )
        if edge.target not in node_map:
            errors.append(
                f"Edge {edge.id!r}: target {edge.target!r} does not reference an existing node"
            )

        # Skip semantic checks if nodes are missing
        if edge.source not in node_map or edge.target not in node_map:
            continue

        source_node = node_map[edge.source]

        # production_target source must be generator or nested_generator
        if edge.edge_type == "production_target":
            if not isinstance(source_node, (Generator, NestedGenerator)):
                errors.append(
                    f"Edge {edge.id!r}: production_target source {edge.source!r} "
                    f"is not a generator or nested_generator (type={source_node.type!r})"
                )

        # upgrade_target source must be an upgrade
        if edge.edge_type == "upgrade_target":
            if not isinstance(source_node, Upgrade):
                errors.append(
                    f"Edge {edge.id!r}: upgrade_target source {edge.source!r} "
                    f"is not an upgrade (type={source_node.type!r})"
                )

        # state_modifier must have a formula
        if edge.edge_type == "state_modifier":
            if not edge.formula:
                errors.append(
                    f"Edge {edge.id!r}: state_modifier edge must have a formula"
                )

    return errors


def check_tag_subgraph(
    game: GameDefinition, active_tags: list[str]
) -> TagFilterResult:
    """Filter nodes by tags and report broken dependencies.

    Nodes with no tags pass through (available to all).
    Nodes with tags are kept only if at least one tag is in active_tags.
    Reports broken unlock_dependency edges from removed to kept nodes.
    """
    active_set = set(active_tags)
    removed: list[str] = []
    kept: set[str] = set()

    for node in game.nodes:
        if not node.tags:
            # No tags -> always included
            kept.add(node.id)
        elif active_set & set(node.tags):
            # At least one tag matches
            kept.add(node.id)
        else:
            removed.append(node.id)

    removed_set = set(removed)
    broken: list[dict[str, str]] = []

    for edge in game.edges:
        if edge.edge_type == "unlock_dependency":
            if edge.source in removed_set and edge.target in kept:
                broken.append({"source": edge.source, "target": edge.target})

    return TagFilterResult(removed_nodes=removed, broken_dependencies=broken)


def get_evaluation_order(game: GameDefinition) -> list[str]:
    """Topological sort of state_modifier and register edges.

    Returns node IDs in evaluation order for the piecewise engine.
    Returns empty list if no state_modifier edges exist.
    """
    state_graph = nx.DiGraph()
    has_edges = False

    for edge in game.edges:
        if edge.edge_type == "state_modifier":
            state_graph.add_edge(edge.source, edge.target)
            has_edges = True

    if not has_edges:
        return []

    return list(nx.topological_sort(state_graph))


def validate_graph(game: GameDefinition) -> list[str]:
    """Aggregate validation: edge compatibility + dependency cycles.

    Returns combined list of errors (empty means valid).
    """
    errors: list[str] = []

    errors.extend(check_edge_compatibility(game))

    cycles = find_dependency_cycles(game)
    for cycle in cycles:
        errors.append(
            f"Unlock dependency cycle detected: {' -> '.join(cycle)}"
        )

    return errors
