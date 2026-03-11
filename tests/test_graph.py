"""Tests for Graph Validation: cycles, compatibility, tag filtering, topological sort."""

from __future__ import annotations

import pytest

from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.nodes import Generator, NestedGenerator, Resource, Upgrade

# ---------- helpers ----------


def _make_game(
    nodes: list,
    edges: list | None = None,
    stacking_groups: dict | None = None,
) -> GameDefinition:
    """Build a minimal GameDefinition for testing."""
    return GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=nodes,
        edges=edges or [],
        stacking_groups=stacking_groups or {},
    )


def _simple_game() -> GameDefinition:
    """A simple game: resource <- generator, with an upgrade."""
    return _make_game(
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(
                id="gen1",
                name="Generator 1",
                base_production=1.0,
                cost_base=10.0,
                cost_growth_rate=1.07,
            ),
            Upgrade(
                id="upg1",
                name="Upgrade 1",
                upgrade_type="multiplicative",
                magnitude=2.0,
                cost=50.0,
                target="gen1",
                stacking_group="global_mult",
            ),
        ],
        edges=[
            Edge(
                id="e1",
                source="gen1",
                target="gold",
                edge_type="production_target",
            ),
            Edge(
                id="e2",
                source="upg1",
                target="gen1",
                edge_type="upgrade_target",
            ),
        ],
        stacking_groups={"global_mult": "multiplicative"},
    )


# ---------- TestGraphBuilding ----------


class TestGraphBuilding:
    """build_graph produces a NetworkX DiGraph with correct node/edge count."""

    def test_correct_node_count(self):
        from idleframework.graph.validation import build_graph

        game = _simple_game()
        g = build_graph(game)
        assert len(g.nodes) == 3

    def test_correct_edge_count(self):
        from idleframework.graph.validation import build_graph

        game = _simple_game()
        g = build_graph(game)
        assert len(g.edges) == 2

    def test_node_data_attribute(self):
        from idleframework.graph.validation import build_graph

        game = _simple_game()
        g = build_graph(game)
        assert g.nodes["gold"]["data"].id == "gold"
        assert g.nodes["gen1"]["data"].type == "generator"

    def test_edge_data_attribute(self):
        from idleframework.graph.validation import build_graph

        game = _simple_game()
        g = build_graph(game)
        assert g.edges["gen1", "gold"]["data"].edge_type == "production_target"


# ---------- TestDependencyCycles ----------


class TestDependencyCycles:
    """find_dependency_cycles only flags unlock_dependency cycles."""

    def test_no_cycles_in_simple_graph(self):
        from idleframework.graph.validation import find_dependency_cycles

        game = _simple_game()
        assert find_dependency_cycles(game) == []

    def test_resource_flow_cycle_is_valid(self):
        """A resource_flow cycle is a feedback loop, NOT an error."""
        from idleframework.graph.validation import find_dependency_cycles

        game = _make_game(
            nodes=[
                Resource(id="a", name="A"),
                Resource(id="b", name="B"),
            ],
            edges=[
                Edge(id="e1", source="a", target="b", edge_type="resource_flow"),
                Edge(id="e2", source="b", target="a", edge_type="resource_flow"),
            ],
        )
        assert find_dependency_cycles(game) == []

    def test_unlock_dependency_cycle_detected(self):
        from idleframework.graph.validation import find_dependency_cycles

        game = _make_game(
            nodes=[
                Resource(id="a", name="A"),
                Resource(id="b", name="B"),
                Resource(id="c", name="C"),
            ],
            edges=[
                Edge(id="e1", source="a", target="b", edge_type="unlock_dependency"),
                Edge(id="e2", source="b", target="c", edge_type="unlock_dependency"),
                Edge(id="e3", source="c", target="a", edge_type="unlock_dependency"),
            ],
        )
        cycles = find_dependency_cycles(game)
        assert len(cycles) >= 1
        # The cycle should contain all three nodes
        assert set(cycles[0]) == {"a", "b", "c"}


# ---------- TestEdgeCompatibility ----------


class TestEdgeCompatibility:
    """check_edge_compatibility validates semantic constraints on edges."""

    def test_valid_production_target_from_generator(self):
        from idleframework.graph.validation import check_edge_compatibility

        game = _simple_game()
        errors = check_edge_compatibility(game)
        assert errors == []

    def test_edge_references_missing_node(self):
        """Dangling edge references are now caught at construction time."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="nonexistent"):
            _make_game(
                nodes=[Resource(id="gold", name="Gold")],
                edges=[
                    Edge(
                        id="e1",
                        source="nonexistent",
                        target="gold",
                        edge_type="resource_flow",
                    ),
                ],
            )

    def test_production_target_from_non_generator(self):
        from idleframework.graph.validation import check_edge_compatibility

        game = _make_game(
            nodes=[
                Resource(id="gold", name="Gold"),
                Resource(id="silver", name="Silver"),
            ],
            edges=[
                Edge(
                    id="e1",
                    source="gold",
                    target="silver",
                    edge_type="production_target",
                ),
            ],
        )
        errors = check_edge_compatibility(game)
        assert len(errors) == 1
        assert "production_target" in errors[0]

    def test_state_modifier_without_formula(self):
        """state_modifier without formula is now caught at construction time."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="formula"):
            _make_game(
                nodes=[
                    Resource(id="a", name="A"),
                    Resource(id="b", name="B"),
                ],
                edges=[
                    Edge(
                        id="e1",
                        source="a",
                        target="b",
                        edge_type="state_modifier",
                        formula=None,
                    ),
                ],
            )

    def test_upgrade_target_from_non_upgrade(self):
        from idleframework.graph.validation import check_edge_compatibility

        game = _make_game(
            nodes=[
                Resource(id="gold", name="Gold"),
                Generator(
                    id="gen1",
                    name="Gen 1",
                    base_production=1.0,
                    cost_base=10.0,
                    cost_growth_rate=1.07,
                ),
            ],
            edges=[
                Edge(
                    id="e1",
                    source="gold",
                    target="gen1",
                    edge_type="upgrade_target",
                ),
            ],
        )
        errors = check_edge_compatibility(game)
        assert len(errors) == 1
        assert "upgrade_target" in errors[0]

    def test_valid_production_target_from_nested_generator(self):
        """nested_generator is also valid as production_target source."""
        from idleframework.graph.validation import check_edge_compatibility

        game = _make_game(
            nodes=[
                Resource(id="gold", name="Gold"),
                Generator(
                    id="gen1",
                    name="Gen 1",
                    base_production=1.0,
                    cost_base=10.0,
                    cost_growth_rate=1.07,
                ),
                NestedGenerator(
                    id="ng1",
                    name="Nested Gen 1",
                    target_generator="gen1",
                    production_rate=1.0,
                    cost_base=100.0,
                    cost_growth_rate=1.15,
                ),
            ],
            edges=[
                Edge(
                    id="e1",
                    source="ng1",
                    target="gold",
                    edge_type="production_target",
                ),
            ],
        )
        errors = check_edge_compatibility(game)
        assert errors == []


# ---------- TestTagSubgraph ----------


class TestTagSubgraph:
    """check_tag_subgraph filters nodes by tags and reports breakage."""

    def test_filter_removes_tagged_nodes(self):
        from idleframework.graph.validation import check_tag_subgraph

        game = _make_game(
            nodes=[
                Resource(id="gold", name="Gold"),  # no tags -> always included
                Resource(id="premium_gem", name="Gem", tags=["premium"]),
            ],
            edges=[],
        )
        result = check_tag_subgraph(game, active_tags=["free"])
        assert "premium_gem" in result.removed_nodes
        assert "gold" not in result.removed_nodes

    def test_tagged_node_kept_when_tag_active(self):
        from idleframework.graph.validation import check_tag_subgraph

        game = _make_game(
            nodes=[
                Resource(id="gold", name="Gold"),
                Resource(id="premium_gem", name="Gem", tags=["premium"]),
            ],
            edges=[],
        )
        result = check_tag_subgraph(game, active_tags=["premium"])
        assert result.removed_nodes == []

    def test_broken_dependency_reported(self):
        """An unlock_dependency from a removed node to a kept node is broken."""
        from idleframework.graph.validation import check_tag_subgraph

        game = _make_game(
            nodes=[
                Resource(id="free_node", name="Free"),
                Resource(id="paid_gate", name="Paid Gate", tags=["premium"]),
            ],
            edges=[
                Edge(
                    id="e1",
                    source="paid_gate",
                    target="free_node",
                    edge_type="unlock_dependency",
                ),
            ],
        )
        result = check_tag_subgraph(game, active_tags=["free"])
        assert "paid_gate" in result.removed_nodes
        assert len(result.broken_dependencies) == 1
        dep = result.broken_dependencies[0]
        assert dep["source"] == "paid_gate"
        assert dep["target"] == "free_node"


# ---------- TestEvaluationOrder ----------


class TestEvaluationOrder:
    """get_evaluation_order returns topological sort of state/register edges."""

    def test_simple_chain(self):
        from idleframework.graph.validation import get_evaluation_order

        game = _make_game(
            nodes=[
                Resource(id="a", name="A"),
                Resource(id="b", name="B"),
                Resource(id="c", name="C"),
            ],
            edges=[
                Edge(
                    id="e1",
                    source="a",
                    target="b",
                    edge_type="state_modifier",
                    formula="x * 2",
                ),
                Edge(
                    id="e2",
                    source="b",
                    target="c",
                    edge_type="state_modifier",
                    formula="x + 1",
                ),
            ],
        )
        order = get_evaluation_order(game)
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_no_state_edges_returns_empty(self):
        from idleframework.graph.validation import get_evaluation_order

        game = _simple_game()
        # _simple_game has production_target and upgrade_target, no state_modifier
        order = get_evaluation_order(game)
        assert order == []


# ---------- TestValidateGraph ----------


class TestValidateGraph:
    """validate_graph aggregates all checks."""

    def test_clean_graph_no_errors(self):
        from idleframework.graph.validation import validate_graph

        game = _simple_game()
        errors = validate_graph(game)
        assert errors == []

    def test_multiple_errors_aggregated(self):
        """validate_graph catches semantic issues on a constructed game."""
        from idleframework.graph.validation import validate_graph

        game = _make_game(
            nodes=[
                Resource(id="gold", name="Gold"),
                Resource(id="silver", name="Silver"),
            ],
            edges=[
                # production_target from non-generator (semantic issue)
                Edge(
                    id="e1",
                    source="gold",
                    target="silver",
                    edge_type="production_target",
                ),
                # upgrade_target from non-upgrade (semantic issue)
                Edge(
                    id="e2",
                    source="silver",
                    target="gold",
                    edge_type="upgrade_target",
                ),
            ],
        )
        errors = validate_graph(game)
        assert len(errors) >= 2
