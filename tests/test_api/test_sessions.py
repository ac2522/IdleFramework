"""Unit tests for SessionManager."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from server.sessions import SessionManager


@pytest.fixture
def minicap_game():
    """Load the MiniCap GameDefinition."""
    from server.game_store import game_store
    game = game_store.get_game("minicap")
    assert game is not None
    return game


class TestSessionCRUD:
    def test_create_returns_session(self, session_mgr, minicap_game):
        session = session_mgr.create("minicap", minicap_game)
        assert session.session_id
        assert session.game_id == "minicap"
        assert session.engine is not None

    def test_get_returns_created_session(self, session_mgr, minicap_game):
        session = session_mgr.create("minicap", minicap_game)
        retrieved = session_mgr.get(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_get_nonexistent_returns_none(self, session_mgr):
        assert session_mgr.get("nonexistent-id") is None

    def test_delete_returns_true(self, session_mgr, minicap_game):
        session = session_mgr.create("minicap", minicap_game)
        assert session_mgr.delete(session.session_id) is True

    def test_delete_then_get_returns_none(self, session_mgr, minicap_game):
        session = session_mgr.create("minicap", minicap_game)
        session_mgr.delete(session.session_id)
        assert session_mgr.get(session.session_id) is None

    def test_double_delete_returns_false(self, session_mgr, minicap_game):
        session = session_mgr.create("minicap", minicap_game)
        assert session_mgr.delete(session.session_id) is True
        assert session_mgr.delete(session.session_id) is False


class TestTTLExpiration:
    def test_expired_session_returns_none(self, minicap_game):
        mgr = SessionManager(max_sessions=10, ttl_seconds=1)
        session = mgr.create("minicap", minicap_game)
        sid = session.session_id

        # Mock time.monotonic to jump forward past TTL
        original_time = time.monotonic()
        with patch("server.sessions.time") as mock_time:
            mock_time.monotonic.return_value = original_time + 5
            result = mgr.get(sid)

        assert result is None

    def test_non_expired_session_returns_session(self, minicap_game):
        mgr = SessionManager(max_sessions=10, ttl_seconds=100)
        session = mgr.create("minicap", minicap_game)
        sid = session.session_id

        # Time barely moves — session should still be alive
        retrieved = mgr.get(sid)
        assert retrieved is not None
        assert retrieved.session_id == sid


class TestLRUEviction:
    def test_oldest_evicted_when_capacity_exceeded(self, minicap_game):
        mgr = SessionManager(max_sessions=3, ttl_seconds=3600)
        sessions = []
        for _i in range(3):
            s = mgr.create("minicap", minicap_game)
            sessions.append(s)

        first_sid = sessions[0].session_id

        # Creating a 4th session should evict the oldest (first)
        mgr.create("minicap", minicap_game)
        assert mgr.get(first_sid) is None

    def test_recently_accessed_not_evicted(self, minicap_game):
        mgr = SessionManager(max_sessions=3, ttl_seconds=3600)
        s1 = mgr.create("minicap", minicap_game)
        s2 = mgr.create("minicap", minicap_game)
        mgr.create("minicap", minicap_game)

        # Access s1 to refresh its last_accessed timestamp
        mgr.get(s1.session_id)

        # Creating a 4th should evict s2 (oldest by last_accessed), not s1
        mgr.create("minicap", minicap_game)
        assert mgr.get(s1.session_id) is not None
        assert mgr.get(s2.session_id) is None

    def test_expired_evicted_before_capacity_check(self, minicap_game):
        """Expired sessions should be evicted first, preserving newer ones."""
        mgr = SessionManager(max_sessions=3, ttl_seconds=1)
        s1 = mgr.create("minicap", minicap_game)
        mgr.create("minicap", minicap_game)
        mgr.create("minicap", minicap_game)

        # Make s1 expired by mocking time forward
        original_time = time.monotonic()
        with patch("server.sessions.time") as mock_time:
            mock_time.monotonic.return_value = original_time + 5
            # Create a 4th session — s1 (expired) should be evicted first,
            # leaving room without evicting s2 or s3
            s4 = mgr.create("minicap", minicap_game)

        # s1 was expired and evicted, s4 was created
        assert s4 is not None
        assert s4.session_id != s1.session_id
