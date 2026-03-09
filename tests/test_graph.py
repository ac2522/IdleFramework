"""Graph validation tests — NetworkX-based structural analysis."""
import pytest
from idleframework.model.game import GameDefinition
from idleframework.graph.validation import (
    build_graph,
    validate_graph,
    find_dependency_cycles,
    check_edge_compatibility,
    check_tag_subgraph,
)


def _make_game(nodes, edges, **kwargs):
    return GameDefinition(
        schema_version="1.0",
        name="Test",
        nodes=nodes,
        edges=edges,
        stacking_groups=kwargs.get("stacking_groups", {}),
    )


class TestGraphBuilding:
    def test_builds_networkx_digraph(self):
        import networkx as nx
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
        )
        G = build_graph(game)
        assert isinstance(G, nx.DiGraph)
        assert G.number_of_nodes() == 2
        assert G.number_of_edges() == 1


class TestDependencyCycles:
    def test_no_cycles_in_simple_graph(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
        )
        cycles = find_dependency_cycles(game)
        assert len(cycles) == 0

    def test_resource_cycle_is_valid(self):
        """Resource flow cycles are valid feedback loops, not errors."""
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
                {"id": "e2", "source": "gold", "target": "miner", "edge_type": "consumption"},
            ],
        )
        cycles = find_dependency_cycles(game)
        # Resource cycles are valid — only unlock_dependency cycles are errors
        assert len(cycles) == 0

    def test_dependency_cycle_detected(self):
        """unlock_dependency cycles are errors."""
        game = _make_game(
            nodes=[
                {"id": "a", "type": "unlock_gate", "name": "A"},
                {"id": "b", "type": "unlock_gate", "name": "B"},
            ],
            edges=[
                {"id": "e1", "source": "a", "target": "b", "edge_type": "unlock_dependency"},
                {"id": "e2", "source": "b", "target": "a", "edge_type": "unlock_dependency"},
            ],
        )
        cycles = find_dependency_cycles(game)
        assert len(cycles) > 0


class TestEdgeCompatibility:
    def test_production_target_from_generator(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
        )
        errors = check_edge_compatibility(game)
        assert len(errors) == 0

    def test_invalid_edge_source_detected(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
            ],
            edges=[
                {"id": "e1", "source": "nonexistent", "target": "gold", "edge_type": "production_target"},
            ],
        )
        errors = check_edge_compatibility(game)
        assert len(errors) > 0


class TestTagSubgraph:
    def test_filter_removes_tagged_nodes(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15,
                 "cycle_time": 1.0, "tags": ["free"]},
                {"id": "boost", "type": "upgrade", "name": "Boost",
                 "upgrade_type": "multiplicative", "magnitude": 10.0, "cost": 0,
                 "target": "miner", "stacking_group": "paid", "tags": ["paid"]},
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
                {"id": "e2", "source": "boost", "target": "miner", "edge_type": "upgrade_target"},
            ],
        )
        result = check_tag_subgraph(game, active_tags=["free"])
        assert "boost" in [n.id for n in result.removed_nodes]

    def test_broken_dependency_reported(self):
        game = _make_game(
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "paid_gate", "type": "unlock_gate", "name": "Gate", "tags": ["paid"]},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.15,
                 "cycle_time": 1.0, "tags": ["free"]},
            ],
            edges=[
                {"id": "e1", "source": "paid_gate", "target": "miner", "edge_type": "unlock_dependency"},
                {"id": "e2", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
        )
        result = check_tag_subgraph(game, active_tags=["free"])
        assert len(result.broken_dependencies) > 0
