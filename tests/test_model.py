"""Tests for Game Model: nodes, edges, GameDefinition, GameState."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from idleframework.model.nodes import (
    AutobuyerNode,
    BuffNode,
    DrainNode,
    SynergyNode,
    TickspeedNode,
)

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
                    id="gen1",
                    name="G",
                    base_production=1.0,
                    cost_base=10.0,
                    cost_growth_rate=1.07,
                ),
                Upgrade(
                    id="upg1",
                    name="U",
                    upgrade_type="multiplicative",
                    magnitude=2.0,
                    cost=50.0,
                    target="gen1",
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
                    id="upg1",
                    name="U",
                    upgrade_type="multiplicative",
                    magnitude=2.0,
                    cost=50.0,
                    target="_all",
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
                        id="upg1",
                        name="U",
                        upgrade_type="multiplicative",
                        magnitude=2.0,
                        cost=50.0,
                        target="nonexistent",
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
                        id="e1",
                        source="nonexistent_source",
                        target="gold",
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
                        id="gen1",
                        name="G",
                        base_production=1.0,
                        cost_base=10.0,
                        cost_growth_rate=1.07,
                    ),
                ],
                edges=[
                    Edge(
                        id="e1",
                        source="gen1",
                        target="nonexistent_target",
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
                        id="gen1",
                        name="G",
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
                    id="gen1",
                    name="G",
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
                    edge_type="state_modifier",
                    formula="base * 2",
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
                        id="gen1",
                        name="G",
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
                        edge_type="state_modifier",
                        formula="!@#invalid",
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
                    id="gen1",
                    name="Miner",
                    base_production=1.0,
                    cost_base=10.0,
                    cost_growth_rate=1.07,
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


# --- Task 1: TickspeedNode ---
def test_tickspeed_node_creation():
    node = TickspeedNode(id="ts1", base_tickspeed=1.5)
    assert node.type == "tickspeed"
    assert node.base_tickspeed == 1.5
    assert node.name == "Tickspeed"


def test_tickspeed_node_default():
    node = TickspeedNode(id="ts1")
    assert node.base_tickspeed == 1.0


# --- Task 2: AutobuyerNode ---
def test_autobuyer_node_creation():
    node = AutobuyerNode(id="ab1", target="gen1", interval=2.0, priority=5)
    assert node.type == "autobuyer"
    assert node.target == "gen1"
    assert node.interval == 2.0
    assert node.priority == 5
    assert node.bulk_amount == "1"
    assert node.enabled is True
    assert node.condition is None


def test_autobuyer_node_with_condition():
    node = AutobuyerNode(id="ab1", target="gen1", condition="balance > cost * 2", bulk_amount="max")
    assert node.condition == "balance > cost * 2"
    assert node.bulk_amount == "max"


# --- Task 3: DrainNode ---
def test_drain_node_creation():
    node = DrainNode(id="drain1", rate=5.0)
    assert node.type == "drain"
    assert node.rate == 5.0
    assert node.condition is None


def test_drain_node_with_condition():
    node = DrainNode(id="drain1", rate=3.0, condition="active == 1")
    assert node.condition == "active == 1"


# --- Task 4: BuffNode ---
def test_buff_node_timed():
    node = BuffNode(id="b1", buff_type="timed", duration=10.0, multiplier=3.0, cooldown=50.0)
    assert node.type == "buff"
    assert node.buff_type == "timed"
    assert node.duration == 10.0
    assert node.cooldown == 50.0


def test_buff_node_proc():
    node = BuffNode(id="b1", buff_type="proc", proc_chance=0.05, multiplier=2.0)
    assert node.proc_chance == 0.05
    assert node.target is None


def test_buff_node_zero_cooldown():
    node = BuffNode(id="b1", buff_type="timed", duration=10.0, multiplier=5.0, cooldown=0.0)
    assert node.cooldown == 0.0


# --- Task 5: SynergyNode ---
def test_synergy_node_creation():
    node = SynergyNode(
        id="syn1",
        sources=["gen_cursor", "gen_grandma"],
        formula_expr="owned_gen_cursor * 0.001",
        target="gen_grandma",
    )
    assert node.type == "synergy"
    assert len(node.sources) == 2
    assert node.formula_expr == "owned_gen_cursor * 0.001"


# --- Task 6: Edge target_property and modifier_mode ---
def test_edge_state_modifier_with_target_property():
    from idleframework.model.edges import Edge

    edge = Edge(
        id="e1",
        source="upg1",
        target="gen1",
        edge_type="state_modifier",
        formula="owned * 0.05",
        target_property="crit_chance",
        modifier_mode="add",
    )
    assert edge.target_property == "crit_chance"
    assert edge.modifier_mode == "add"


def test_edge_backward_compat_no_target_property():
    from idleframework.model.edges import Edge

    edge = Edge(
        id="e1",
        source="upg1",
        target="gen1",
        edge_type="state_modifier",
        formula="2.0",
    )
    assert edge.target_property is None
    assert edge.modifier_mode is None


# --- Task 7: PrestigeLayer multi-layer fields ---
def test_prestige_layer_multi_layer_fields():
    from idleframework.model.nodes import PrestigeLayer

    node = PrestigeLayer(
        id="p1",
        formula_expr="floor(sqrt(lifetime))",
        layer_index=1,
        reset_scope=["gen1", "res1"],
        currency_id="prestige_currency",
        parent_layer="p2",
    )
    assert node.currency_id == "prestige_currency"
    assert node.parent_layer == "p2"


def test_prestige_layer_backward_compat():
    from idleframework.model.nodes import PrestigeLayer

    node = PrestigeLayer(
        id="p1",
        formula_expr="floor(sqrt(lifetime))",
        layer_index=0,
        reset_scope=["gen1"],
    )
    assert node.currency_id is None
    assert node.parent_layer is None


# --- Task 8: Resource capacity ---
def test_resource_capacity():
    from idleframework.model.nodes import Resource

    node = Resource(id="r1", name="Gold", capacity=1000.0)
    assert node.capacity == 1000.0
    assert node.overflow_behavior == "clamp"


def test_resource_no_capacity():
    from idleframework.model.nodes import Resource

    node = Resource(id="r1", name="Gold")
    assert node.capacity is None


# --- Task 9: Converter recipe_type, conversion_limit, ConverterIO formula ---
def test_converter_io_with_formula():
    from idleframework.model.nodes import ConverterIO

    cio = ConverterIO(resource="gold", amount=10.0, formula="conversion_count * 0.9")
    assert cio.formula == "conversion_count * 0.9"


def test_converter_io_no_formula():
    from idleframework.model.nodes import ConverterIO

    cio = ConverterIO(resource="gold", amount=10.0)
    assert cio.formula is None


def test_converter_scaling_recipe():
    from idleframework.model.nodes import Converter, ConverterIO

    node = Converter(
        id="c1",
        inputs=[ConverterIO(resource="wood", amount=5.0)],
        outputs=[ConverterIO(resource="plank", amount=2.0, formula="2 * conversion_count ** 0.5")],
        rate=1.0,
        recipe_type="scaling",
        conversion_limit=100,
    )
    assert node.recipe_type == "scaling"
    assert node.conversion_limit == 100


# --- Task 10: NodeState last_fired, GameState layer_run_times ---
def test_node_state_last_fired():
    from idleframework.model.state import NodeState

    ns = NodeState(last_fired=5.0)
    assert ns.last_fired == 5.0


def test_node_state_last_fired_default():
    from idleframework.model.state import NodeState

    ns = NodeState()
    assert ns.last_fired == 0.0


def test_game_state_layer_run_times():
    from idleframework.model.state import GameState

    gs = GameState(node_states={}, layer_run_times={"p1": 100.0})
    assert gs.layer_run_times["p1"] == 100.0


def test_game_state_layer_run_times_default():
    from idleframework.model.state import GameState

    gs = GameState(node_states={})
    assert gs.layer_run_times == {}


# --- Task 12: GameDefinition validation for new node types ---


def test_game_validates_tickspeed_singleton():
    """Only one TickspeedNode allowed per game."""
    from pydantic import ValidationError

    from idleframework.model.game import GameDefinition
    from idleframework.model.nodes import Resource

    nodes = [
        Resource(id="r1", name="Gold"),
        TickspeedNode(id="ts1"),
        TickspeedNode(id="ts2"),
    ]
    with pytest.raises(ValidationError, match="tickspeed"):
        GameDefinition(
            schema_version="1.0",
            name="test",
            nodes=nodes,
            edges=[],
            stacking_groups={},
        )


def test_game_validates_state_modifier_target_property():
    """target_property must be a valid numeric field on target node."""
    from pydantic import ValidationError

    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.nodes import Generator, Resource

    nodes = [
        Resource(id="r1", name="Gold"),
        Generator(id="g1", name="Gen", base_production=1, cost_base=1, cost_growth_rate=1.15),
    ]
    edges = [
        Edge(
            id="e1",
            source="r1",
            target="g1",
            edge_type="state_modifier",
            formula="2",
            target_property="nonexistent_field",
            modifier_mode="multiply",
        )
    ]
    with pytest.raises(ValidationError, match="target_property"):
        GameDefinition(
            schema_version="1.0",
            name="test",
            nodes=nodes,
            edges=edges,
            stacking_groups={},
        )


def test_game_validates_synergy_formula():
    """SynergyNode formula_expr must compile."""
    from pydantic import ValidationError

    from idleframework.model.game import GameDefinition
    from idleframework.model.nodes import Generator, Resource

    nodes = [
        Resource(id="r1", name="Gold"),
        Generator(id="g1", name="Gen", base_production=1, cost_base=1, cost_growth_rate=1.15),
        SynergyNode(id="syn1", sources=["g1"], formula_expr="invalid!!!", target="g1"),
    ]
    with pytest.raises(ValidationError, match="[Ff]ormula"):
        GameDefinition(
            schema_version="1.0",
            name="test",
            nodes=nodes,
            edges=[],
            stacking_groups={},
        )


def test_state_modifier_validates_numeric_target_property():
    """State modifier with valid numeric target_property should pass validation."""
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.nodes import Generator, Resource

    # base_production is a float field - should be valid
    GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(
                id="gen1", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15
            ),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(
                id="sm1",
                source="gold",
                target="gen1",
                edge_type="state_modifier",
                formula="2.0",
                target_property="base_production",
                modifier_mode="multiply",
            ),
        ],
        stacking_groups={},
    )
    # Should not raise


def test_state_modifier_rejects_non_numeric_target_property():
    """State modifier with non-numeric target_property should fail validation."""
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.nodes import Generator, Resource

    with pytest.raises(ValidationError, match="target_property"):
        GameDefinition(
            schema_version="1.0",
            name="test",
            nodes=[
                Resource(id="gold", name="Gold"),
                Generator(
                    id="gen1",
                    name="Miner",
                    base_production=1.0,
                    cost_base=10,
                    cost_growth_rate=1.15,
                ),
            ],
            edges=[
                Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
                Edge(
                    id="sm1",
                    source="gold",
                    target="gen1",
                    edge_type="state_modifier",
                    formula="2.0",
                    target_property="name",
                    modifier_mode="multiply",
                ),
            ],
            stacking_groups={},
        )


def test_state_modifier_accepts_optional_float():
    """State modifier targeting Optional[float] field like capacity should pass."""
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.nodes import Generator, Resource

    # capacity is float | None — should be accepted
    GameDefinition(
        schema_version="1.0",
        name="test",
        nodes=[
            Resource(id="gold", name="Gold", capacity=1000.0),
            Generator(
                id="gen1", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15
            ),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(
                id="sm1",
                source="gold",
                target="gold",
                edge_type="state_modifier",
                formula="2000.0",
                target_property="capacity",
                modifier_mode="set",
            ),
        ],
        stacking_groups={},
    )
    # Should not raise


def test_state_modifier_rejects_literal_field():
    """State modifier targeting a Literal field (like type) should fail."""
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.nodes import Generator, Resource

    with pytest.raises(ValidationError, match="target_property"):
        GameDefinition(
            schema_version="1.0",
            name="test",
            nodes=[
                Resource(id="gold", name="Gold"),
                Generator(
                    id="gen1",
                    name="Miner",
                    base_production=1.0,
                    cost_base=10,
                    cost_growth_rate=1.15,
                ),
            ],
            edges=[
                Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
                Edge(
                    id="sm1",
                    source="gold",
                    target="gen1",
                    edge_type="state_modifier",
                    formula="2.0",
                    target_property="type",
                    modifier_mode="set",
                ),
            ],
            stacking_groups={},
        )
