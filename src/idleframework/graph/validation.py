"""Graph validation: build NetworkX graph, detect cycles, check compatibility, tag filtering."""
from __future__ import annotations

from dataclasses import dataclass, field
import networkx as nx

from idleframework.model.game import GameDefinition


# Edge types that represent hard dependencies (cycles = errors)
_DEPENDENCY_EDGE_TYPES = frozenset({"unlock_dependency"})


def build_graph(game: GameDefinition) -> nx.DiGraph:
    """Build a NetworkX directed graph from a game definition."""
    G = nx.DiGraph()
    for node in game.nodes:
        G.add_node(node.id, data=node)
    for edge in game.edges:
        G.add_edge(edge.source, edge.target, data=edge)
    return G


def find_dependency_cycles(game: GameDefinition) -> list[list[str]]:
    """Find cycles in dependency edges (unlock_dependency). Resource cycles are valid."""
    dep_graph = nx.DiGraph()
    for node in game.nodes:
        dep_graph.add_node(node.id)
    for edge in game.edges:
        if edge.edge_type in _DEPENDENCY_EDGE_TYPES:
            dep_graph.add_edge(edge.source, edge.target)
    return list(nx.simple_cycles(dep_graph))


def check_edge_compatibility(game: GameDefinition) -> list[str]:
    """Check that edge sources and targets reference existing nodes."""
    node_ids = {n.id for n in game.nodes}
    errors = []
    for edge in game.edges:
        if edge.source not in node_ids:
            errors.append(f"Edge '{edge.id}': source '{edge.source}' not found")
        if edge.target not in node_ids:
            errors.append(f"Edge '{edge.id}': target '{edge.target}' not found")
    return errors


def validate_graph(game: GameDefinition) -> list[str]:
    """Run all graph validations. Returns list of error messages."""
    errors = []
    errors.extend(check_edge_compatibility(game))
    cycles = find_dependency_cycles(game)
    for cycle in cycles:
        errors.append(f"Dependency cycle detected: {' -> '.join(cycle)}")
    return errors


@dataclass
class TagFilterResult:
    """Result of filtering a game graph by active tags."""
    removed_nodes: list = field(default_factory=list)
    broken_dependencies: list[str] = field(default_factory=list)


def check_tag_subgraph(game: GameDefinition, active_tags: list[str]) -> TagFilterResult:
    """Filter game graph by active tags. Report removed nodes and broken dependencies."""
    result = TagFilterResult()
    active_set = set(active_tags)

    # Nodes that survive: no tags (available to all) or at least one tag in active set
    kept_ids = set()
    for node in game.nodes:
        if not node.tags or any(t in active_set for t in node.tags):
            kept_ids.add(node.id)
        else:
            result.removed_nodes.append(node)

    # Check for broken dependencies
    removed_ids = {n.id for n in result.removed_nodes}
    for edge in game.edges:
        if edge.edge_type in _DEPENDENCY_EDGE_TYPES:
            if edge.source in removed_ids and edge.target in kept_ids:
                result.broken_dependencies.append(
                    f"Node '{edge.target}' depends on removed node '{edge.source}' "
                    f"(edge '{edge.id}', type '{edge.edge_type}')"
                )

    return result
