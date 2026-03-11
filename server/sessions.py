"""In-memory engine session manager."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import bulk_cost
from idleframework.model.game import GameDefinition
from server.config import settings


@dataclass
class EngineSession:
    session_id: str
    game_id: str
    game: GameDefinition
    engine: PiecewiseEngine
    created_at: float
    last_accessed: float


class SessionManager:
    """In-memory session store with TTL and LRU eviction."""

    def __init__(
        self,
        max_sessions: int = settings.max_sessions,
        ttl_seconds: int = settings.session_ttl,
    ):
        self._sessions: dict[str, EngineSession] = {}
        self._max = max_sessions
        self._ttl = ttl_seconds

    def create(self, game_id: str, game: GameDefinition, initial_balance: float = 50.0) -> EngineSession:
        self._evict_expired()
        if len(self._sessions) >= self._max:
            self._evict_lru()

        session_id = str(uuid.uuid4())
        engine = PiecewiseEngine(game)

        # Set initial balance on primary resource
        primary = engine._get_primary_resource_id()
        if primary:
            engine.set_balance(primary, initial_balance)
            # Buy first generator if affordable
            for gen_id in engine._generators:
                cost = bulk_cost(
                    engine._generators[gen_id].cost_base,
                    engine._generators[gen_id].cost_growth_rate,
                    0, 1,
                )
                if cost <= initial_balance:
                    engine.purchase(gen_id, 1)
                    break

        now = time.monotonic()
        session = EngineSession(
            session_id=session_id,
            game_id=game_id,
            game=game,
            engine=engine,
            created_at=now,
            last_accessed=now,
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> EngineSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if time.monotonic() - session.last_accessed > self._ttl:
            del self._sessions[session_id]
            return None
        session.last_accessed = time.monotonic()
        return session

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def _evict_expired(self):
        now = time.monotonic()
        expired = [k for k, v in self._sessions.items() if now - v.last_accessed > self._ttl]
        for k in expired:
            del self._sessions[k]

    def _evict_lru(self):
        if not self._sessions:
            return
        oldest = min(self._sessions.values(), key=lambda s: s.last_accessed)
        del self._sessions[oldest.session_id]


session_manager = SessionManager()
