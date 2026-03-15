"""Shared fixtures for API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.sessions import SessionManager


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def session_mgr():
    """Provide a fresh SessionManager with short TTL for test isolation."""
    return SessionManager(max_sessions=5, ttl_seconds=2)


@pytest.fixture
def game_store_dir(tmp_path):
    """Provide a temporary GameStore directory pair (bundled + user).

    Returns (bundled_dir, user_dir) as Path objects.
    """
    bundled = tmp_path / "games"
    user = tmp_path / "games" / "user"
    bundled.mkdir(parents=True, exist_ok=True)
    user.mkdir(parents=True, exist_ok=True)
    return bundled, user
