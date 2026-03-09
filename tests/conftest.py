"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from idleframework.model.game import GameDefinition


@pytest.fixture
def minicap_path():
    """Path to the MiniCap fixture JSON file."""
    return Path(__file__).parent / "fixtures" / "minicap.json"


@pytest.fixture
def minicap(minicap_path):
    """Load and validate the MiniCap game definition."""
    with open(minicap_path) as f:
        data = json.load(f)
    return GameDefinition.model_validate(data)
