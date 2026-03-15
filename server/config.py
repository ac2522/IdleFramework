"""Server configuration -- loaded from environment with IDLE_ prefix."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    model_config = {"env_prefix": "IDLE_"}

    host: str = "0.0.0.0"
    port: int = 8000
    games_dir: str = str(Path(__file__).parent / "games")
    user_games_dir: str = str(Path(__file__).parent / "games" / "user")
    cors_origins: list[str] = ["http://localhost:5173"]
    max_sessions: int = 100
    session_ttl: int = 3600


settings = ServerConfig()
