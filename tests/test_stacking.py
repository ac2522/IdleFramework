"""Tests for stacking group computation and bridge function."""

import pytest

from idleframework.model.stacking import (
    collect_stacking_bonuses,
    compute_final_multiplier,
)
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState


# ---------- compute_final_multiplier ----------


def test_single_multiplicative_group():
    groups = {
        "cash_mults": {"rule": "multiplicative", "bonuses": [3.0, 2.0, 5.0]},
    }
    assert compute_final_multiplier(groups) == 30.0


def test_single_additive_group():
    groups = {
        "ad_bonus": {"rule": "additive", "bonuses": [0.02, 0.02, 0.02]},
    }
    assert compute_final_multiplier(groups) == pytest.approx(1.06)


def test_single_percentage_group():
    groups = {
        "pct_group": {"rule": "percentage", "bonuses": [10, 20, 5]},
    }
    assert compute_final_multiplier(groups) == pytest.approx(1.35)


def test_adcap_multi_group():
    """4 groups matching AdCap model: cash_mults * angel_mults * ad_bonus * event."""
    groups = {
        "cash_mults": {"rule": "multiplicative", "bonuses": [3.0, 3.0]},
        "angel_mults": {"rule": "multiplicative", "bonuses": [2.0, 5.0]},
        "ad_bonus": {"rule": "additive", "bonuses": [0.5, 0.5]},
        "event": {"rule": "percentage", "bonuses": [50]},
    }
    # cash: 3*3 = 9
    # angel: 2*5 = 10
    # ad: 1 + 0.5 + 0.5 = 2.0
    # event: 1 + 50/100 = 1.5
    # final: 9 * 10 * 2.0 * 1.5 = 270.0
    assert compute_final_multiplier(groups) == pytest.approx(270.0)


def test_empty_group():
    groups = {
        "empty": {"rule": "multiplicative", "bonuses": []},
    }
    assert compute_final_multiplier(groups) == 1.0


def test_no_groups():
    assert compute_final_multiplier({}) == 1.0


def test_additive_gold_mults():
    """Additive means 1 + sum, NOT product. [12, 12] → 25.0, NOT 144."""
    groups = {
        "gold_mults": {"rule": "additive", "bonuses": [12, 12]},
    }
    assert compute_final_multiplier(groups) == pytest.approx(25.0)


# ---------- collect_stacking_bonuses ----------


def _make_game(upgrades, stacking_groups, generators=None):
    """Helper to build a minimal GameDefinition with upgrades."""
    nodes = []
    # Need at least one resource for a valid game
    nodes.append({"type": "resource", "id": "cash", "name": "Cash"})
    # Add generators
    if generators:
        nodes.extend(generators)
    else:
        nodes.append(
            {
                "type": "generator",
                "id": "gen1",
                "name": "Gen 1",
                "base_production": 1.0,
                "cost_base": 10.0,
                "cost_growth_rate": 1.07,
            }
        )
    nodes.extend(upgrades)
    return GameDefinition(
        schema_version="1.0",
        name="Test Game",
        nodes=nodes,
        edges=[],
        stacking_groups=stacking_groups,
    )


def test_collect_from_game_state():
    upgrades = [
        {
            "type": "upgrade",
            "id": "u1",
            "name": "Upgrade 1",
            "upgrade_type": "multiplicative",
            "magnitude": 3.0,
            "cost": 100,
            "target": "gen1",
            "stacking_group": "cash_mults",
        },
        {
            "type": "upgrade",
            "id": "u2",
            "name": "Upgrade 2",
            "upgrade_type": "multiplicative",
            "magnitude": 2.0,
            "cost": 500,
            "target": "gen1",
            "stacking_group": "cash_mults",
        },
        {
            "type": "upgrade",
            "id": "u3",
            "name": "Upgrade 3",
            "upgrade_type": "additive",
            "magnitude": 0.5,
            "cost": 200,
            "target": "gen1",
            "stacking_group": "ad_bonus",
        },
    ]
    stacking_groups = {"cash_mults": "multiplicative", "ad_bonus": "additive"}
    game = _make_game(upgrades, stacking_groups)
    state = GameState.from_game(game)

    # Purchase u1 and u3, but NOT u2
    state.get("u1").purchased = True
    state.get("u3").purchased = True

    result = collect_stacking_bonuses(game, state)
    assert result == {
        "cash_mults": {"rule": "multiplicative", "bonuses": [3.0]},
        "ad_bonus": {"rule": "additive", "bonuses": [0.5]},
    }
    assert compute_final_multiplier(result) == pytest.approx(3.0 * 1.5)


def test_collect_no_purchased():
    upgrades = [
        {
            "type": "upgrade",
            "id": "u1",
            "name": "Upgrade 1",
            "upgrade_type": "multiplicative",
            "magnitude": 3.0,
            "cost": 100,
            "target": "gen1",
            "stacking_group": "cash_mults",
        },
    ]
    stacking_groups = {"cash_mults": "multiplicative"}
    game = _make_game(upgrades, stacking_groups)
    state = GameState.from_game(game)

    result = collect_stacking_bonuses(game, state)
    # No purchased upgrades → no bonuses
    assert result == {}
    assert compute_final_multiplier(result) == 1.0


def test_collect_all_target():
    """An upgrade with target '_all' applies its bonus to the group."""
    upgrades = [
        {
            "type": "upgrade",
            "id": "u_all",
            "name": "Global Boost",
            "upgrade_type": "multiplicative",
            "magnitude": 2.0,
            "cost": 1000,
            "target": "_all",
            "stacking_group": "cash_mults",
        },
    ]
    stacking_groups = {"cash_mults": "multiplicative"}
    game = _make_game(upgrades, stacking_groups)
    state = GameState.from_game(game)
    state.get("u_all").purchased = True

    result = collect_stacking_bonuses(game, state)
    assert result == {
        "cash_mults": {"rule": "multiplicative", "bonuses": [2.0]},
    }
    assert compute_final_multiplier(result) == pytest.approx(2.0)


def test_collect_achievement_bonus():
    """Achievement milestones with a bonus dict should contribute to stacking."""
    nodes = [
        {"type": "resource", "id": "cash", "name": "Cash"},
        {
            "type": "generator", "id": "gen1", "name": "Gen 1",
            "base_production": 1.0, "cost_base": 10.0, "cost_growth_rate": 1.07,
        },
        {
            "type": "achievement", "id": "milestone_25",
            "name": "25 Generators",
            "condition_type": "single_threshold",
            "targets": [{"node_id": "gen1", "property": "owned", "threshold": 25}],
            "bonus": {
                "type": "multiplicative", "magnitude": 2.0,
                "target": "gen1", "stacking_group": "milestones",
            },
        },
    ]
    stacking_groups = {"milestones": "multiplicative"}
    game = GameDefinition(
        schema_version="1.0", name="Test", nodes=nodes, edges=[],
        stacking_groups=stacking_groups,
    )
    state = GameState.from_game(game)
    # Mark achievement as unlocked
    state.get("milestone_25").purchased = True

    result = collect_stacking_bonuses(game, state)
    assert "milestones" in result, "Achievement bonus should appear in stacking groups"
    assert result["milestones"]["bonuses"] == [2.0]
    assert compute_final_multiplier(result) == pytest.approx(2.0)


def test_collect_upgrade_owned_count():
    """Stackable upgrades should contribute bonus × owned count."""
    upgrades = [
        {
            "type": "upgrade", "id": "u1", "name": "Repeatable Boost",
            "upgrade_type": "multiplicative", "magnitude": 2.0,
            "cost": 100, "target": "gen1", "stacking_group": "cash_mults",
        },
    ]
    stacking_groups = {"cash_mults": "multiplicative"}
    game = _make_game(upgrades, stacking_groups)
    state = GameState.from_game(game)
    state.get("u1").purchased = True
    state.get("u1").owned = 3  # Bought 3 copies

    result = collect_stacking_bonuses(game, state)
    # Multiplicative: each copy contributes 2.0, so 3 copies = 2.0 * 2.0 * 2.0 = 8.0
    assert len(result["cash_mults"]["bonuses"]) == 3
    assert compute_final_multiplier(result) == pytest.approx(8.0)
