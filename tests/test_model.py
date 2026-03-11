"""Tests for Game Model: nodes, edges, GameDefinition, GameState."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

# ---------- Node construction tests (all 17 types) ----------


class TestNodeConstruction:
    """Every node type can be constructed with minimal + full args."""

    def test_resource(self):
        from idleframework.model.nodes import Resource

        r = Resource(id="gold", name="Gold")
        assert r.type == "resource"
        assert r.initial_value == 0.0
        assert r.tags == []
        assert r.activation_mode == "automatic"
        assert r.pull_mode == "pull_any"
        assert r.cooldown_time is None

    def test_resource_with_initial_value(self):
        from idleframework.model.nodes import Resource

        r = Resource(id="gold", name="Gold", initial_value=100.0)
        assert r.initial_value == 100.0

    def test_generator(self):
        from idleframework.model.nodes import Generator

        g = Generator(
            id="lemonade_stand",
            name="Lemonade Stand",
            base_production=1.0,
            cost_base=4.0,
            cost_growth_rate=1.07,
        )
        assert g.type == "generator"
        assert g.cycle_time == 1.0

    def test_nested_generator(self):
        from idleframework.model.nodes import NestedGenerator

        ng = NestedGenerator(
            id="ng1",
            name="Newspaper Delivery",
            target_generator="lemonade_stand",
            production_rate=2.0,
            cost_base=100.0,
            cost_growth_rate=1.15,
        )
        assert ng.type == "nested_generator"

    def test_upgrade(self):
        from idleframework.model.nodes import Upgrade

        u = Upgrade(
            id="upg1",
            name="Speed Boost",
            upgrade_type="multiplicative",
            magnitude=2.0,
            cost=50.0,
            target="lemonade_stand",
            stacking_group="speed",
        )
        assert u.type == "upgrade"
        assert u.duration is None
        assert u.cooldown_time is None

    def test_prestige_layer(self):
        from idleframework.model.nodes import PrestigeLayer

        p = PrestigeLayer(
            id="prestige1",
            formula_expr="sqrt(lifetime_earnings / 1e12)",
            layer_index=0,
            reset_scope=["gold", "lemonade_stand"],
        )
        assert p.type == "prestige_layer"
        assert p.bonus_type == "multiplicative"
        assert p.persistence_scope == []
        assert p.milestone_rules == []

    def test_sacrifice_node(self):
        from idleframework.model.nodes import SacrificeNode

        s = SacrificeNode(
            id="sacrifice1",
            formula_expr="log(x + 1)",
            reset_scope=["gold"],
        )
        assert s.type == "sacrifice"
        assert s.bonus_type == "multiplicative"

    def test_achievement(self):
        from idleframework.model.nodes import Achievement, ConditionTarget

        a = Achievement(
            id="ach1",
            condition_type="single_threshold",
            targets=[ConditionTarget(node_id="gold", property="current_value", threshold=1000.0)],
        )
        assert a.type == "achievement"
        assert a.permanent is True
        assert a.logic == "and"

    def test_manager(self):
        from idleframework.model.nodes import Manager

        m = Manager(id="mgr1", target="lemonade_stand")
        assert m.type == "manager"
        assert m.automation_type == "collect"

    def test_converter(self):
        from idleframework.model.nodes import Converter, ConverterIO

        c = Converter(
            id="conv1",
            inputs=[ConverterIO(resource="wood", amount=5.0)],
            outputs=[ConverterIO(resource="plank", amount=2.0)],
        )
        assert c.type == "converter"
        assert c.rate == 1.0

    def test_probability_node(self):
        from idleframework.model.nodes import ProbabilityNode

        p = ProbabilityNode(id="prob1", expected_value=10.0)
        assert p.type == "probability"
        assert p.variance == 0.0
        assert p.crit_chance == 0.0
        assert p.crit_multiplier == 1.0

    def test_end_condition(self):
        from idleframework.model.nodes import ConditionTarget, EndCondition

        e = EndCondition(
            id="end1",
            targets=[ConditionTarget(node_id="gold", property="current_value", threshold=1e15)],
        )
        assert e.type == "end_condition"
        assert e.condition_type == "single_threshold"
        assert e.logic == "and"

    def test_unlock_gate(self):
        from idleframework.model.nodes import ConditionTarget, UnlockGate

        u = UnlockGate(
            id="gate1",
            targets=[ConditionTarget(node_id="gold", property="current_value", threshold=500.0)],
            prerequisites=["ach1"],
        )
        assert u.type == "unlock_gate"
        assert u.permanent is True

    def test_choice_group(self):
        from idleframework.model.nodes import ChoiceGroup

        c = ChoiceGroup(
            id="cg1",
            options=["opt_a", "opt_b", "opt_c"],
        )
        assert c.type == "choice_group"
        assert c.max_selections == 1
        assert c.respeccable is False
        assert c.respec_cost is None

    def test_register(self):
        from idleframework.model.nodes import Register

        r = Register(
            id="reg1",
            formula_expr="a + b * 2",
            input_labels=[{"a": "gold"}, {"b": "silver"}],
        )
        assert r.type == "register"

    def test_gate(self):
        from idleframework.model.nodes import Gate

        g = Gate(
            id="gate_det",
            mode="deterministic",
            weights=[1.0, 2.0],
        )
        assert g.type == "gate"

    def test_gate_probabilistic(self):
        from idleframework.model.nodes import Gate

        g = Gate(
            id="gate_prob",
            mode="probabilistic",
            probabilities=[0.3, 0.7],
        )
        assert g.type == "gate"

    def test_queue(self):
        from idleframework.model.nodes import Queue

        q = Queue(id="queue1", delay=5.0)
        assert q.type == "queue"
        assert q.capacity is None

    def test_queue_with_capacity(self):
        from idleframework.model.nodes import Queue

        q = Queue(id="queue2", delay=3.0, capacity=10)
        assert q.capacity == 10


# ---------- Edge tests ----------


class TestEdgeConstruction:
    def test_production_target_edge(self):
        from idleframework.model.edges import Edge

        e = Edge(
            id="e1",
            source="lemonade_stand",
            target="gold",
            edge_type="production_target",
        )
        assert e.edge_type == "production_target"
        assert e.rate is None
        assert e.formula is None
        assert e.condition is None

    def test_state_modifier_edge_with_formula(self):
        from idleframework.model.edges import Edge

        e = Edge(
            id="e2",
            source="upg1",
            target="lemonade_stand",
            edge_type="state_modifier",
            formula="base * 2",
        )
        assert e.formula == "base * 2"

    def test_resource_flow_edge_with_rate(self):
        from idleframework.model.edges import Edge

        e = Edge(
            id="e3",
            source="gen1",
            target="gold",
            edge_type="resource_flow",
            rate=1.5,
        )
        assert e.rate == 1.5

    def test_invalid_edge_type_rejected(self):
        from idleframework.model.edges import Edge

        with pytest.raises(ValidationError):
            Edge(id="bad", source="a", target="b", edge_type="not_a_type")

    def test_all_edge_types(self):
        from idleframework.model.edges import Edge

        valid_types = [
            "resource_flow",
            "consumption",
            "production_target",
            "state_modifier",
            "activator",
            "trigger",
            "unlock_dependency",
            "upgrade_target",
        ]
        for i, et in enumerate(valid_types):
            e = Edge(id=f"e_{i}", source="a", target="b", edge_type=et)
            assert e.edge_type == et


# ---------- GameDefinition tests ----------


class TestGameDefinition:
    def _minimal_game(self):
        """Helper: build a minimal valid game."""
        from idleframework.model.edges import Edge
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Generator, Resource

        return GameDefinition(
            schema_version="1.0",
            name="TestGame",
            nodes=[
                Resource(id="gold", name="Gold"),
                Generator(
                    id="gen1",
                    name="Miner",
                    base_production=1.0,
                    cost_base=10.0,
                    cost_growth_rate=1.07,
                ),
            ],
            edges=[
                Edge(
                    id="e1",
                    source="gen1",
                    target="gold",
                    edge_type="production_target",
                ),
            ],
            stacking_groups={},
        )

    def test_minimal_game(self):
        g = self._minimal_game()
        assert g.name == "TestGame"
        assert len(g.nodes) == 2
        assert len(g.edges) == 1

    def test_defaults(self):
        g = self._minimal_game()
        assert g.time_unit == "seconds"
        assert g.tie_breaking == "lowest_cost"
        assert g.event_epsilon == 0.001
        assert g.free_purchase_threshold == 1e-5
        assert g.description is None

    def test_description_field(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Resource

        g = GameDefinition(
            schema_version="1.0",
            name="Described",
            description="A test game",
            nodes=[Resource(id="r1", name="R")],
            edges=[],
            stacking_groups={},
        )
        assert g.description == "A test game"

    def test_invalid_node_type_rejected(self):
        from idleframework.model.game import GameDefinition

        with pytest.raises(ValidationError):
            GameDefinition(
                schema_version="1.0",
                name="Bad",
                nodes=[{"id": "x", "type": "not_real", "name": "X"}],
                edges=[],
                stacking_groups={},
            )

    def test_duplicate_node_ids_rejected(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Resource

        with pytest.raises(ValidationError, match="[Dd]uplicate.*node"):
            GameDefinition(
                schema_version="1.0",
                name="DupNodes",
                nodes=[
                    Resource(id="gold", name="Gold"),
                    Resource(id="gold", name="Gold2"),
                ],
                edges=[],
                stacking_groups={},
            )

    def test_duplicate_edge_ids_rejected(self):
        from idleframework.model.edges import Edge
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Generator, Resource

        with pytest.raises(ValidationError, match="[Dd]uplicate.*edge"):
            GameDefinition(
                schema_version="1.0",
                name="DupEdges",
                nodes=[
                    Resource(id="gold", name="Gold"),
                    Generator(
                        id="gen1",
                        name="Miner",
                        base_production=1.0,
                        cost_base=10.0,
                        cost_growth_rate=1.07,
                    ),
                ],
                edges=[
                    Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
                    Edge(id="e1", source="gen1", target="gold", edge_type="resource_flow"),
                ],
                stacking_groups={},
            )

    def test_stacking_groups(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Resource

        g = GameDefinition(
            schema_version="1.0",
            name="SG",
            nodes=[Resource(id="r1", name="R")],
            edges=[],
            stacking_groups={"speed": "multiplicative", "flat": "additive"},
        )
        assert g.stacking_groups["speed"] == "multiplicative"

    def test_json_roundtrip(self):
        g = self._minimal_game()
        json_str = g.model_dump_json()
        data = json.loads(json_str)
        from idleframework.model.game import GameDefinition

        g2 = GameDefinition.model_validate(data)
        assert g2.name == g.name
        assert len(g2.nodes) == len(g.nodes)
        assert len(g2.edges) == len(g.edges)

    def test_json_schema_export(self):
        from idleframework.model.game import GameDefinition

        schema = GameDefinition.model_json_schema()
        assert "properties" in schema
        assert "name" in schema["properties"]

    def test_get_node(self):
        g = self._minimal_game()
        node = g.get_node("gold")
        assert node.id == "gold"

    def test_get_node_missing_raises(self):
        g = self._minimal_game()
        with pytest.raises(KeyError):
            g.get_node("nonexistent")

    def test_get_edges_from(self):
        g = self._minimal_game()
        edges = g.get_edges_from("gen1")
        assert len(edges) == 1
        assert edges[0].target == "gold"

    def test_get_edges_to(self):
        g = self._minimal_game()
        edges = g.get_edges_to("gold")
        assert len(edges) == 1
        assert edges[0].source == "gen1"

    def test_get_edges_empty(self):
        g = self._minimal_game()
        assert g.get_edges_from("gold") == []
        assert g.get_edges_to("gen1") == []


# ---------- Upgrade.target validation ----------


class TestUpgradeTargetValidation:
    def test_valid_target_passes(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Generator, Resource, Upgrade

        GameDefinition(
            schema_version="1.0",
            name="UpgTest",
            nodes=[
                Resource(id="gold", name="Gold"),
                Generator(
                    id="gen1", name="G", base_production=1.0,
                    cost_base=10.0, cost_growth_rate=1.07,
                ),
                Upgrade(
                    id="upg1", name="U", upgrade_type="multiplicative",
                    magnitude=2.0, cost=50.0, target="gen1",
                    stacking_group="speed",
                ),
            ],
            edges=[],
            stacking_groups={"speed": "multiplicative"},
        )

    def test_all_target_passes(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Resource, Upgrade

        GameDefinition(
            schema_version="1.0",
            name="UpgAll",
            nodes=[
                Resource(id="gold", name="Gold"),
                Upgrade(
                    id="upg1", name="U", upgrade_type="multiplicative",
                    magnitude=2.0, cost=50.0, target="_all",
                    stacking_group="speed",
                ),
            ],
            edges=[],
            stacking_groups={"speed": "multiplicative"},
        )

    def test_invalid_target_rejected(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Resource, Upgrade

        with pytest.raises(ValidationError, match="[Tt]arget.*nonexistent"):
            GameDefinition(
                schema_version="1.0",
                name="UpgBad",
                nodes=[
                    Resource(id="gold", name="Gold"),
                    Upgrade(
                        id="upg1", name="U", upgrade_type="multiplicative",
                        magnitude=2.0, cost=50.0, target="nonexistent",
                        stacking_group="speed",
                    ),
                ],
                edges=[],
                stacking_groups={"speed": "multiplicative"},
            )


# ---------- Edge referential integrity ----------


class TestEdgeReferentialIntegrity:
    def test_dangling_edge_source_rejected(self):
        from idleframework.model.edges import Edge
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Resource

        with pytest.raises(ValidationError, match="nonexistent_source"):
            GameDefinition(
                schema_version="1.0",
                name="BadEdge",
                nodes=[Resource(id="gold", name="Gold")],
                edges=[
                    Edge(
                        id="e1", source="nonexistent_source", target="gold",
                        edge_type="production_target",
                    ),
                ],
                stacking_groups={},
            )

    def test_dangling_edge_target_rejected(self):
        from idleframework.model.edges import Edge
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Generator, Resource

        with pytest.raises(ValidationError, match="nonexistent_target"):
            GameDefinition(
                schema_version="1.0",
                name="BadEdge",
                nodes=[
                    Resource(id="gold", name="Gold"),
                    Generator(
                        id="gen1", name="G", base_production=1.0,
                        cost_base=10.0, cost_growth_rate=1.07,
                    ),
                ],
                edges=[
                    Edge(
                        id="e1", source="gen1", target="nonexistent_target",
                        edge_type="production_target",
                    ),
                ],
                stacking_groups={},
            )

    def test_state_modifier_without_formula_rejected(self):
        from idleframework.model.edges import Edge
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Generator, Resource

        with pytest.raises(ValidationError, match="formula"):
            GameDefinition(
                schema_version="1.0",
                name="BadEdge",
                nodes=[
                    Resource(id="gold", name="Gold"),
                    Generator(
                        id="gen1", name="G", base_production=1.0,
                        cost_base=10.0, cost_growth_rate=1.07,
                    ),
                ],
                edges=[
                    Edge(
                        id="e1", source="gen1", target="gold",
                        edge_type="state_modifier",
                    ),
                ],
                stacking_groups={},
            )


# ---------- Formula validation at load ----------


class TestFormulaValidation:
    def test_valid_formula_on_prestige_layer(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import PrestigeLayer, Resource

        GameDefinition(
            schema_version="1.0",
            name="FormulaOK",
            nodes=[
                Resource(id="gold", name="Gold"),
                PrestigeLayer(
                    id="p1",
                    formula_expr="sqrt(x + 1)",
                    layer_index=0,
                    reset_scope=["gold"],
                ),
            ],
            edges=[],
            stacking_groups={},
        )

    def test_invalid_formula_on_prestige_layer_rejected(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import PrestigeLayer, Resource

        with pytest.raises(ValidationError, match="[Ff]ormula"):
            GameDefinition(
                schema_version="1.0",
                name="FormulaBad",
                nodes=[
                    Resource(id="gold", name="Gold"),
                    PrestigeLayer(
                        id="p1",
                        formula_expr="this is not a formula!!!",
                        layer_index=0,
                        reset_scope=["gold"],
                    ),
                ],
                edges=[],
                stacking_groups={},
            )

    def test_valid_formula_on_sacrifice_node(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Resource, SacrificeNode

        GameDefinition(
            schema_version="1.0",
            name="SacOK",
            nodes=[
                Resource(id="gold", name="Gold"),
                SacrificeNode(
                    id="s1",
                    formula_expr="log(x + 1)",
                    reset_scope=["gold"],
                ),
            ],
            edges=[],
            stacking_groups={},
        )

    def test_valid_formula_on_register(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Register, Resource

        GameDefinition(
            schema_version="1.0",
            name="RegOK",
            nodes=[
                Resource(id="gold", name="Gold"),
                Register(
                    id="r1",
                    formula_expr="a + b * 2",
                    input_labels=[{"a": "gold"}],
                ),
            ],
            edges=[],
            stacking_groups={},
        )

    def test_invalid_formula_on_register_rejected(self):
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Register, Resource

        with pytest.raises(ValidationError, match="[Ff]ormula"):
            GameDefinition(
                schema_version="1.0",
                name="RegBad",
                nodes=[
                    Resource(id="gold", name="Gold"),
                    Register(
                        id="r1",
                        formula_expr="@#$%^&",
                        input_labels=[],
                    ),
                ],
                edges=[],
                stacking_groups={},
            )

    def test_valid_formula_on_state_modifier_edge(self):
        from idleframework.model.edges import Edge
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Generator, Resource

        GameDefinition(
            schema_version="1.0",
            name="EdgeFormulaOK",
            nodes=[
                Resource(id="gold", name="Gold"),
                Generator(
                    id="gen1", name="G", base_production=1.0,
                    cost_base=10.0, cost_growth_rate=1.07,
                ),
            ],
            edges=[
                Edge(
                    id="e1", source="gen1", target="gold",
                    edge_type="state_modifier", formula="base * 2",
                ),
            ],
            stacking_groups={},
        )

    def test_invalid_formula_on_state_modifier_edge_rejected(self):
        from idleframework.model.edges import Edge
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Generator, Resource

        with pytest.raises(ValidationError, match="[Ff]ormula"):
            GameDefinition(
                schema_version="1.0",
                name="EdgeFormulaBad",
                nodes=[
                    Resource(id="gold", name="Gold"),
                    Generator(
                        id="gen1", name="G", base_production=1.0,
                        cost_base=10.0, cost_growth_rate=1.07,
                    ),
                ],
                edges=[
                    Edge(
                        id="e1", source="gen1", target="gold",
                        edge_type="state_modifier", formula="!@#invalid",
                    ),
                ],
                stacking_groups={},
            )


# ---------- GameState tests ----------


class TestGameState:
    def _make_game(self):
        from idleframework.model.edges import Edge
        from idleframework.model.game import GameDefinition
        from idleframework.model.nodes import Generator, Resource

        return GameDefinition(
            schema_version="1.0",
            name="StateTest",
            nodes=[
                Resource(id="gold", name="Gold", initial_value=100.0),
                Generator(
                    id="gen1", name="Miner", base_production=1.0,
                    cost_base=10.0, cost_growth_rate=1.07,
                ),
            ],
            edges=[
                Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            ],
            stacking_groups={},
        )

    def test_from_game_creates_states(self):
        from idleframework.model.state import GameState

        game = self._make_game()
        state = GameState.from_game(game)
        assert "gold" in state.node_states
        assert "gen1" in state.node_states

    def test_initial_resource_value(self):
        from idleframework.model.state import GameState

        game = self._make_game()
        state = GameState.from_game(game)
        assert state.get_resource_value("gold") == 100.0

    def test_generator_initial_state(self):
        from idleframework.model.state import GameState

        game = self._make_game()
        state = GameState.from_game(game)
        ns = state.get("gen1")
        assert ns.owned == 0
        assert ns.current_value == 0.0

    def test_get_node_state(self):
        from idleframework.model.state import GameState

        game = self._make_game()
        state = GameState.from_game(game)
        ns = state.get("gold")
        assert ns.current_value == 100.0

    def test_elapsed_time_default(self):
        from idleframework.model.state import GameState

        game = self._make_game()
        state = GameState.from_game(game)
        assert state.elapsed_time == 0.0
        assert state.run_time == 0.0

    def test_lifetime_earnings_default(self):
        from idleframework.model.state import GameState

        game = self._make_game()
        state = GameState.from_game(game)
        assert state.lifetime_earnings == {}

    def test_get_missing_node_raises(self):
        from idleframework.model.state import GameState

        game = self._make_game()
        state = GameState.from_game(game)
        with pytest.raises(KeyError):
            state.get("nonexistent")
