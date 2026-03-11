"""File-based game definition storage."""
from __future__ import annotations

import json
import re
from pathlib import Path

from idleframework.model.game import GameDefinition
from server.config import settings


def _slugify(name: str) -> str:
    """Convert game name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class GameStore:
    """Manages game definitions on disk."""

    def __init__(self):
        self._bundled_dir = Path(settings.games_dir)
        self._user_dir = Path(settings.user_games_dir)
        self._bundled_dir.mkdir(parents=True, exist_ok=True)
        self._user_dir.mkdir(parents=True, exist_ok=True)

    def list_games(self) -> list[dict]:
        """List all games with metadata."""
        games = []
        for path in sorted(self._bundled_dir.glob("*.json")):
            game = self._load_file(path)
            if game:
                games.append({
                    "id": path.stem,
                    "name": game.name,
                    "node_count": len(game.nodes),
                    "edge_count": len(game.edges),
                    "bundled": True,
                })
        for path in sorted(self._user_dir.glob("*.json")):
            game = self._load_file(path)
            if game:
                games.append({
                    "id": path.stem,
                    "name": game.name,
                    "node_count": len(game.nodes),
                    "edge_count": len(game.edges),
                    "bundled": False,
                })
        return games

    def get_game(self, game_id: str) -> GameDefinition | None:
        """Load a game by ID."""
        for d in [self._bundled_dir, self._user_dir]:
            path = d / f"{game_id}.json"
            if path.exists():
                return self._load_file(path)
        return None

    def is_bundled(self, game_id: str) -> bool:
        return (self._bundled_dir / f"{game_id}.json").exists()

    def save_game(self, game: GameDefinition) -> str:
        """Save a user game. Returns the game ID."""
        game_id = _slugify(game.name)
        path = self._user_dir / f"{game_id}.json"
        path.write_text(game.model_dump_json(indent=2))
        return game_id

    def delete_game(self, game_id: str) -> bool:
        """Delete a user game. Returns True if deleted."""
        path = self._user_dir / f"{game_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def _load_file(self, path: Path) -> GameDefinition | None:
        try:
            data = json.loads(path.read_text())
            return GameDefinition.model_validate(data)
        except Exception:
            return None


# Singleton
game_store = GameStore()
