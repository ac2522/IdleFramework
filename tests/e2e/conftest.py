"""Phase B E2E test fixtures and helpers."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.game import GameDefinition
from idleframework.model.nodes import Resource

E2E_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "e2e"

PHASE_B_FIXTURES = [
    "cookie_clicker",
    "factory_idle",
    "prestige_tower",
    "speed_runner",
    "full_kitchen",
]

# Fixtures that have drains, buffs, or prestige — production rate may not be monotonic
NON_MONOTONIC_FIXTURES = {"factory_idle", "prestige_tower", "full_kitchen"}

# Fixtures that are single-resource (safe for simple greedy optimizer)
SINGLE_RESOURCE_FIXTURES = {"cookie_clicker", "prestige_tower"}


def load_e2e_game(name: str) -> GameDefinition:
    """Load and validate an E2E fixture by name."""
    path = E2E_FIXTURE_DIR / f"{name}.json"
    data = json.loads(path.read_text())
    return GameDefinition.model_validate(data)


def find_primary_resource(game: GameDefinition) -> str:
    """Find the first Resource node ID in the game."""
    for node in game.nodes:
        if isinstance(node, Resource):
            return node.id
    raise ValueError("Game has no Resource nodes")


def find_first_generator(game: GameDefinition) -> str:
    """Find the first Generator node ID in the game."""
    from idleframework.model.nodes import Generator

    for node in game.nodes:
        if isinstance(node, Generator):
            return node.id
    raise ValueError("Game has no Generator nodes")


@pytest.fixture(params=PHASE_B_FIXTURES)
def pb_fixture_name(request):
    """Parametrize over all 5 E2E fixture names."""
    return request.param


@pytest.fixture
def pb_game(pb_fixture_name) -> GameDefinition:
    """Load E2E game definition."""
    return load_e2e_game(pb_fixture_name)


@pytest.fixture
def pb_engine(pb_game) -> PiecewiseEngine:
    """Create a fresh PiecewiseEngine from E2E game."""
    return PiecewiseEngine(pb_game, validate=True)


# Per-fixture named fixtures for targeted tests
@pytest.fixture
def cookie_game() -> GameDefinition:
    return load_e2e_game("cookie_clicker")


@pytest.fixture
def cookie_engine(cookie_game) -> PiecewiseEngine:
    return PiecewiseEngine(cookie_game, validate=True)


@pytest.fixture
def factory_game() -> GameDefinition:
    return load_e2e_game("factory_idle")


@pytest.fixture
def factory_engine(factory_game) -> PiecewiseEngine:
    return PiecewiseEngine(factory_game, validate=True)


@pytest.fixture
def prestige_game() -> GameDefinition:
    return load_e2e_game("prestige_tower")


@pytest.fixture
def prestige_engine(prestige_game) -> PiecewiseEngine:
    return PiecewiseEngine(prestige_game, validate=True)


@pytest.fixture
def speed_game() -> GameDefinition:
    return load_e2e_game("speed_runner")


@pytest.fixture
def speed_engine(speed_game) -> PiecewiseEngine:
    return PiecewiseEngine(speed_game, validate=True)


@pytest.fixture
def kitchen_game() -> GameDefinition:
    return load_e2e_game("full_kitchen")


@pytest.fixture
def kitchen_engine(kitchen_game) -> PiecewiseEngine:
    return PiecewiseEngine(kitchen_game, validate=True)


def fresh_engine(game: GameDefinition) -> PiecewiseEngine:
    """Create a fresh engine — use when you need isolation from optimizer mutation."""
    return PiecewiseEngine(copy.deepcopy(game), validate=True)
