"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from idleframework.model.game import GameDefinition

FIXTURE_DIR = Path(__file__).parent / "fixtures"
E2E_FIXTURE_DIR = FIXTURE_DIR / "e2e"

E2E_FIXTURE_NAMES = [
    "cookie_clicker",
    "factory_idle",
    "prestige_tower",
    "speed_runner",
    "full_kitchen",
]


def _load_game(fixture_dir: Path, name: str) -> GameDefinition:
    """Load and validate a game definition from a JSON fixture file."""
    path = fixture_dir / f"{name}.json"
    data = json.loads(path.read_text())
    return GameDefinition.model_validate(data)


@pytest.fixture
def minicap_path():
    """Path to the MiniCap fixture JSON file."""
    return FIXTURE_DIR / "minicap.json"


@pytest.fixture
def minicap(minicap_path):
    """Load and validate the MiniCap game definition."""
    with open(minicap_path) as f:
        data = json.load(f)
    return GameDefinition.model_validate(data)


@pytest.fixture(params=E2E_FIXTURE_NAMES)
def e2e_fixture_name(request):
    """Parametrize over all 5 E2E fixture names."""
    return request.param


@pytest.fixture
def e2e_game(e2e_fixture_name) -> GameDefinition:
    """Load and validate an E2E fixture by name."""
    return _load_game(E2E_FIXTURE_DIR, e2e_fixture_name)
