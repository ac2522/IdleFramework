"""Game model Pydantic v2 validation tests.

Tests node/edge construction, discriminated union serialization,
JSON Schema export, and validation error messages.
"""
import json
import pytest
from pydantic import ValidationError
from idleframework.model.nodes import (
    Resource, Generator, Upgrade, PrestigeLayer, Achievement,
    UnlockGate, ChoiceGroup, EndCondition, NodeUnion,
)
from idleframework.model.edges import Edge, EdgeUnion
from idleframework.model.game import GameDefinition


class TestNodeConstruction:
    def test_resource(self):
        r = Resource(id="gold", name="Gold", initial_value=0)
        assert r.type == "resource"
        assert r.name == "Gold"

    def test_generator(self):
        g = Generator(
            id="lemonade",
            name="Lemonade Stand",
            base_production=1.0,
            cost_base=4.0,
            cost_growth_rate=1.07,
            cycle_time=1.0,
        )
        assert g.type == "generator"
        assert g.cost_growth_rate == 1.07

    def test_upgrade_multiplicative(self):
        u = Upgrade(
            id="x3_lemon",
            name="x3 Lemonade",
            upgrade_type="multiplicative",
            magnitude=3.0,
            cost=1000.0,
            target="lemonade",
            stacking_group="cash_upgrades",
        )
        assert u.type == "upgrade"
        assert u.stacking_group == "cash_upgrades"

    def test_achievement_multi_threshold(self):
        a = Achievement(
            id="own_25_all",
            name="Own 25 of Everything",
            condition_type="multi_threshold",
            targets=[
                {"node_id": "lemonade", "property": "count", "threshold": 25},
                {"node_id": "newspaper", "property": "count", "threshold": 25},
            ],
            logic="and",
            bonus={"type": "multiplicative", "magnitude": 3.0},
            permanent=True,
        )
        assert a.condition_type == "multi_threshold"

    def test_end_condition(self):
        ec = EndCondition(
            id="win",
            condition_type="single_threshold",
            targets=[{"node_id": "gold", "property": "current_value", "threshold": 1e15}],
            logic="and",
        )
        assert ec.type == "end_condition"

    def test_tags(self):
        u = Upgrade(
            id="paid_boost",
            name="Paid Boost",
            upgrade_type="multiplicative",
            magnitude=10.0,
            cost=0,
            target="lemonade",
            stacking_group="paid",
            tags=["paid"],
        )
        assert "paid" in u.tags


class TestEdgeConstruction:
    def test_production_target(self):
        e = Edge(
            id="e1",
            source="lemonade",
            target="gold",
            edge_type="production_target",
        )
        assert e.edge_type == "production_target"

    def test_state_modifier_with_formula(self):
        e = Edge(
            id="e2",
            source="angel_register",
            target="lemonade",
            edge_type="state_modifier",
            formula="a * 0.02",
        )
        assert e.formula == "a * 0.02"


class TestGameDefinition:
    def test_minimal_game(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Test Game",
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {
                    "id": "miner", "type": "generator", "name": "Miner",
                    "base_production": 1.0, "cost_base": 10.0,
                    "cost_growth_rate": 1.15, "cycle_time": 1.0,
                },
            ],
            edges=[
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
            stacking_groups={"default": "multiplicative"},
        )
        assert len(game.nodes) == 2
        assert len(game.edges) == 1

    def test_invalid_node_type_rejects(self):
        with pytest.raises(ValidationError):
            GameDefinition(
                schema_version="1.0",
                name="Bad",
                nodes=[{"id": "x", "type": "nonexistent"}],
                edges=[],
                stacking_groups={},
            )

    def test_duplicate_node_ids_reject(self):
        with pytest.raises(ValidationError, match="[Dd]uplicate"):
            GameDefinition(
                schema_version="1.0",
                name="Bad",
                nodes=[
                    {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                    {"id": "gold", "type": "resource", "name": "Gold2", "initial_value": 0},
                ],
                edges=[],
                stacking_groups={},
            )

    def test_json_roundtrip(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Roundtrip",
            nodes=[
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
            ],
            edges=[],
            stacking_groups={},
        )
        json_str = game.model_dump_json()
        loaded = GameDefinition.model_validate_json(json_str)
        assert loaded.name == "Roundtrip"

    def test_json_schema_export(self):
        schema = GameDefinition.model_json_schema()
        assert "properties" in schema
        assert "nodes" in schema["properties"]


class TestGameLevelProperties:
    def test_stacking_groups(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Stacking Test",
            nodes=[],
            edges=[],
            stacking_groups={
                "angel_bonus": "additive",
                "cash_upgrades": "multiplicative",
                "milestone_bonuses": "multiplicative",
            },
        )
        assert game.stacking_groups["angel_bonus"] == "additive"

    def test_event_epsilon_default(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Defaults",
            nodes=[],
            edges=[],
            stacking_groups={},
        )
        assert game.event_epsilon == 0.001

    def test_free_purchase_threshold_default(self):
        game = GameDefinition(
            schema_version="1.0",
            name="Defaults",
            nodes=[],
            edges=[],
            stacking_groups={},
        )
        assert game.free_purchase_threshold == 1e-5
