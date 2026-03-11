# Phase 2 + Phase 4 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI REST API wrapping the idleframework library (Phase 2) and a React + TypeScript + Tailwind frontend with a playable game demo and analysis dashboard (Phase 4).

**Architecture:** FastAPI serves the API at `/api/v1/` and the built frontend as static files at `/`. The API is a thin wrapper — all computation delegates to the existing `idleframework` library. In-memory sessions power the interactive game mode. No database, no external services.

**Tech Stack:** Python 3.12+, FastAPI, uvicorn, React 19, TypeScript 5, Vite 6, Tailwind CSS 4, React Router 7, Plotly.js, react-plotly.js

**Design Doc:** `docs/plans/2026-03-10-phases-2-3-4-design.md`

---

## Task 1: Server Scaffold + Dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `server/__init__.py`
- Create: `server/app.py`
- Create: `server/config.py`
- Create: `server/routes/__init__.py`
- Create: `Makefile`

**Step 1: Update pyproject.toml with server dependencies**

```toml
# Add to pyproject.toml [project.optional-dependencies]
server = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "python-multipart>=0.0.20",
]
dev = [
    "pytest>=8.0",
    "hypothesis>=6.0",
    "mpmath>=1.3",
    "sympy>=1.12",
    "pytest-benchmark>=4.0",
    "ruff>=0.4",
    "httpx>=0.28",
    "idleframework[server]",
]
```

**Step 2: Create server config**

```python
# server/config.py
"""Server configuration — loaded from environment with IDLE_ prefix."""
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
```

Note: `pydantic-settings` must also be added to the `server` dependencies in `pyproject.toml`.

**Step 3: Create FastAPI app**

```python
# server/__init__.py
"""IdleFramework API server."""
```

```python
# server/app.py
"""FastAPI application — serves API + static frontend."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure games directories exist
    Path(settings.games_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.user_games_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="IdleFramework API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include route modules
from server.routes import games, analysis, engine  # noqa: E402

app.include_router(games.router, prefix="/api/v1/games", tags=["games"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(engine.router, prefix="/api/v1/engine", tags=["engine"])

# Mount static frontend (production build) if it exists
_static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="frontend")
```

```python
# server/routes/__init__.py
"""API route modules."""
```

**Step 4: Create Makefile**

```makefile
# Makefile
.PHONY: dev server frontend build run install test

install:
	pip install -e ".[dev,server]"
	cd frontend && npm install

server:
	uvicorn server.app:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run in two terminals:"
	@echo "  make server"
	@echo "  make frontend"

build:
	cd frontend && npm run build

run: build
	uvicorn server.app:app --port 8000

test:
	pytest tests/ -v
```

**Step 5: Create empty route stubs so the app starts**

```python
# server/routes/games.py
"""Game definition CRUD endpoints."""
from fastapi import APIRouter

router = APIRouter()
```

```python
# server/routes/analysis.py
"""Analysis endpoints."""
from fastapi import APIRouter

router = APIRouter()
```

```python
# server/routes/engine.py
"""Interactive engine session endpoints."""
from fastapi import APIRouter

router = APIRouter()
```

**Step 6: Install and verify server starts**

Run: `pip install -e ".[dev,server]" && python -c "from server.app import app; print('OK')"`
Expected: `OK`

**Step 7: Commit**

```bash
git add pyproject.toml server/ Makefile
git commit -m "feat: FastAPI server scaffold with config, CORS, route stubs, Makefile"
```

---

## Task 2: API Schemas + Game Storage

**Files:**
- Create: `server/schemas.py`
- Create: `server/game_store.py`
- Create: `server/games/` (copy fixtures)
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_api/test_games_routes.py`

**Step 1: Write failing tests for game routes**

```python
# tests/test_api/__init__.py
"""API route tests."""
```

```python
# tests/test_api/test_games_routes.py
"""Tests for game definition CRUD endpoints."""
import json
import pytest
from fastapi.testclient import TestClient
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestListGames:
    def test_list_returns_bundled_games(self, client):
        resp = client.get("/api/v1/games/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["games"], list)
        ids = [g["id"] for g in data["games"]]
        assert "minicap" in ids

    def test_list_includes_name_and_node_count(self, client):
        resp = client.get("/api/v1/games/")
        game = next(g for g in resp.json()["games"] if g["id"] == "minicap")
        assert game["name"] == "MiniCap"
        assert game["node_count"] > 0


class TestGetGame:
    def test_get_existing_game(self, client):
        resp = client.get("/api/v1/games/minicap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "MiniCap"
        assert "nodes" in data

    def test_get_nonexistent_game_404(self, client):
        resp = client.get("/api/v1/games/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["error"] == "game_not_found"


class TestCreateGame:
    def test_create_game_from_json(self, client, tmp_path):
        game_json = {
            "schema_version": "1.0",
            "name": "Test Game",
            "nodes": [
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
            ],
            "edges": [],
            "stacking_groups": {},
        }
        resp = client.post("/api/v1/games/", json=game_json)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "test-game"
        assert data["name"] == "Test Game"

    def test_create_invalid_game_422(self, client):
        resp = client.post("/api/v1/games/", json={"bad": "data"})
        assert resp.status_code == 422


class TestDeleteGame:
    def test_delete_user_game(self, client):
        # Create first
        game_json = {
            "schema_version": "1.0",
            "name": "Deletable",
            "nodes": [],
            "edges": [],
            "stacking_groups": {},
        }
        client.post("/api/v1/games/", json=game_json)
        resp = client.delete("/api/v1/games/deletable")
        assert resp.status_code == 204

    def test_delete_bundled_game_403(self, client):
        resp = client.delete("/api/v1/games/minicap")
        assert resp.status_code == 403


class TestExportGame:
    def test_export_yaml(self, client):
        resp = client.get("/api/v1/games/minicap/export?format=yaml")
        assert resp.status_code == 200
        assert "MiniCap" in resp.text

    def test_export_xml(self, client):
        resp = client.get("/api/v1/games/minicap/export?format=xml")
        assert resp.status_code == 200
        assert "<GameDefinition" in resp.text

    def test_export_schema(self, client):
        resp = client.get("/api/v1/games/minicap/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "properties" in data
```

Run: `pytest tests/test_api/test_games_routes.py -v`
Expected: FAIL — routes not implemented

**Step 2: Create game store**

```python
# server/game_store.py
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
```

**Step 3: Create API schemas**

```python
# server/schemas.py
"""API request/response Pydantic models."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel


# -- Games --

class GameSummary(BaseModel):
    id: str
    name: str
    node_count: int
    edge_count: int
    bundled: bool


class GameListResponse(BaseModel):
    games: list[GameSummary]


class GameCreateResponse(BaseModel):
    id: str
    name: str


# -- Analysis --

class AnalysisRequest(BaseModel):
    game_id: str
    simulation_time: float = 300.0
    optimizer: Literal["greedy", "beam", "mcts", "bnb"] = "greedy"
    beam_width: int = 100
    mcts_iterations: int = 1000
    mcts_seed: int | None = None
    bnb_depth: int = 20
    tags: list[str] | None = None


class CompareRequest(BaseModel):
    game_id: str
    strategies: list[str] = ["free", "paid"]
    simulation_time: float = 300.0


class ReportRequest(BaseModel):
    game_id: str
    simulation_time: float = 300.0
    use_cdn: bool = True


# -- Engine Sessions --

class StartSessionRequest(BaseModel):
    game_id: str
    initial_balance: float = 50.0


class AdvanceRequest(BaseModel):
    seconds: float = 1.0


class PurchaseRequest(BaseModel):
    node_id: str
    count: int = 1


class AutoOptimizeRequest(BaseModel):
    target_time: float = 300.0
    optimizer: Literal["greedy", "beam", "mcts", "bnb"] = "greedy"
    max_steps: int = 500


class ResourceState(BaseModel):
    current_value: float
    production_rate: float


class GeneratorState(BaseModel):
    owned: int
    cost_next: float
    production_per_sec: float


class UpgradeState(BaseModel):
    purchased: bool
    cost: float
    affordable: bool


class PrestigeState(BaseModel):
    available_currency: float
    formula_preview: str


class AchievementState(BaseModel):
    id: str
    name: str
    unlocked: bool


class SessionState(BaseModel):
    session_id: str
    game_id: str
    elapsed_time: float
    resources: dict[str, ResourceState]
    generators: dict[str, GeneratorState]
    upgrades: dict[str, UpgradeState]
    prestige: PrestigeState | None = None
    achievements: list[AchievementState] = []


class PurchaseStepResponse(BaseModel):
    time: float
    node_id: str
    cost: float
    count: int


class TimelineEntry(BaseModel):
    time: float
    production_rate: float


class AutoOptimizeResponse(BaseModel):
    purchases: list[PurchaseStepResponse]
    timeline: list[TimelineEntry]
    final_production: float
    final_balance: float


# -- Errors --

class ErrorResponse(BaseModel):
    error: str
    detail: str
    status: int
```

**Step 4: Copy bundled fixtures to server/games/**

```bash
cp tests/fixtures/minicap.json server/games/minicap.json
cp tests/fixtures/mediumcap.json server/games/mediumcap.json
```

**Step 5: Implement game routes**

```python
# server/routes/games.py
"""Game definition CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse

from idleframework.model.game import GameDefinition
from idleframework.export import to_yaml, to_xml
from server.game_store import game_store
from server.schemas import GameListResponse, GameCreateResponse, GameSummary, ErrorResponse

router = APIRouter()


@router.get("/", response_model=GameListResponse)
def list_games():
    games = game_store.list_games()
    return GameListResponse(games=[GameSummary(**g) for g in games])


@router.get("/{game_id}")
def get_game(game_id: str):
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    return game.model_dump(mode="json")


@router.post("/", response_model=GameCreateResponse, status_code=201)
def create_game(game: GameDefinition):
    game_id = game_store.save_game(game)
    return GameCreateResponse(id=game_id, name=game.name)


@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: str):
    if game_store.is_bundled(game_id):
        raise HTTPException(status_code=403, detail=ErrorResponse(
            error="forbidden",
            detail=f"Cannot delete bundled game '{game_id}'",
            status=403,
        ).model_dump())
    if not game_store.delete_game(game_id):
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No user game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    return Response(status_code=204)


@router.get("/{game_id}/schema")
def get_schema(game_id: str):
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    return GameDefinition.model_json_schema()


@router.get("/{game_id}/export")
def export_game(game_id: str, format: str = "yaml"):
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    if format == "yaml":
        return PlainTextResponse(to_yaml(game), media_type="text/yaml")
    elif format == "xml":
        return PlainTextResponse(to_xml(game), media_type="application/xml")
    else:
        raise HTTPException(status_code=400, detail=ErrorResponse(
            error="invalid_format",
            detail=f"Unsupported format '{format}'. Use 'yaml' or 'xml'.",
            status=400,
        ).model_dump())
```

**Step 6: Run tests**

Run: `pytest tests/test_api/test_games_routes.py -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add server/ tests/test_api/
git commit -m "feat: game CRUD routes — list, get, create, delete, export, schema"
```

---

## Task 3: Analysis Routes

**Files:**
- Create: `tests/test_api/test_analysis_routes.py`
- Modify: `server/routes/analysis.py`

**Step 1: Write failing tests**

```python
# tests/test_api/test_analysis_routes.py
"""Tests for analysis endpoints."""
import pytest
from fastapi.testclient import TestClient
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestRunAnalysis:
    def test_run_greedy_analysis(self, client):
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "minicap",
            "simulation_time": 60.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["game_name"] == "MiniCap"
        assert "dead_upgrades" in data
        assert "progression_walls" in data
        assert "optimizer_result" in data

    def test_run_analysis_nonexistent_game(self, client):
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "nonexistent",
        })
        assert resp.status_code == 404

    def test_run_with_custom_time(self, client):
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "minicap",
            "simulation_time": 30.0,
        })
        assert resp.status_code == 200
        assert resp.json()["simulation_time"] == 30.0


class TestCompare:
    def test_compare_strategies(self, client):
        resp = client.post("/api/v1/analysis/compare", json={
            "game_id": "minicap",
            "strategies": ["free", "paid"],
            "simulation_time": 60.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "baseline" in data
        assert "variants" in data


class TestReport:
    def test_generate_html_report(self, client):
        resp = client.post("/api/v1/analysis/report", json={
            "game_id": "minicap",
            "simulation_time": 60.0,
        })
        assert resp.status_code == 200
        assert "<!DOCTYPE html>" in resp.text
        assert "MiniCap" in resp.text
```

Run: `pytest tests/test_api/test_analysis_routes.py -v`
Expected: FAIL

**Step 2: Implement analysis routes**

```python
# server/routes/analysis.py
"""Analysis endpoints — run, compare, report."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from idleframework.analysis.detectors import run_full_analysis
from idleframework.reports.html import generate_report
from server.game_store import game_store
from server.schemas import AnalysisRequest, CompareRequest, ReportRequest, ErrorResponse

router = APIRouter()


def _get_game_or_404(game_id: str):
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    return game


@router.post("/run")
def run_analysis(req: AnalysisRequest):
    game = _get_game_or_404(req.game_id)
    report = run_full_analysis(game, simulation_time=req.simulation_time)
    # Serialize dataclass to dict
    result = {
        "game_name": report.game_name,
        "simulation_time": report.simulation_time,
        "dead_upgrades": report.dead_upgrades,
        "progression_walls": report.progression_walls,
        "dominant_strategy": report.dominant_strategy,
        "sensitivity": report.sensitivity,
        "optimizer_result": None,
    }
    if report.optimizer_result:
        opt = report.optimizer_result
        result["optimizer_result"] = {
            "purchases": [
                {"time": p.time, "node_id": p.node_id, "count": p.count, "cost": p.cost}
                for p in opt.purchases
            ],
            "timeline": opt.timeline,
            "final_production": opt.final_production,
            "final_balance": opt.final_balance,
            "final_time": opt.final_time,
        }
    return result


@router.post("/compare")
def compare_strategies(req: CompareRequest):
    game = _get_game_or_404(req.game_id)
    baseline = run_full_analysis(game, simulation_time=req.simulation_time)
    baseline_prod = baseline.optimizer_result.final_production if baseline.optimizer_result else 0

    variants = {}
    for tag in req.strategies:
        # Filter out nodes tagged with this tag
        filtered_nodes = []
        excluded_ids = set()
        for node in game.nodes:
            if hasattr(node, "tags") and tag in node.tags and getattr(node, "type", "") == "upgrade":
                excluded_ids.add(node.id)
            else:
                filtered_nodes.append(node)

        from idleframework.model.game import GameDefinition
        variant_game = GameDefinition(
            schema_version=game.schema_version,
            name=f"{game.name}_no_{tag}",
            nodes=filtered_nodes,
            edges=[e for e in game.edges if e.source not in excluded_ids and e.target not in excluded_ids],
            stacking_groups=game.stacking_groups,
        )
        variant_report = run_full_analysis(variant_game, simulation_time=req.simulation_time)
        variant_prod = variant_report.optimizer_result.final_production if variant_report.optimizer_result else 0
        ratio = baseline_prod / variant_prod if variant_prod > 0 else float("inf")
        variants[tag] = {
            "final_production": variant_prod,
            "ratio_vs_baseline": ratio,
        }

    return {
        "baseline": {"final_production": baseline_prod},
        "variants": variants,
    }


@router.post("/report")
def generate_html_report(req: ReportRequest):
    game = _get_game_or_404(req.game_id)
    report = run_full_analysis(game, simulation_time=req.simulation_time)
    html = generate_report(report, use_cdn=req.use_cdn)
    return HTMLResponse(content=html)
```

**Step 3: Run tests**

Run: `pytest tests/test_api/test_analysis_routes.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add server/routes/analysis.py tests/test_api/test_analysis_routes.py
git commit -m "feat: analysis routes — run, compare, HTML report generation"
```

---

## Task 4: Engine Session Manager

**Files:**
- Create: `server/sessions.py`
- Create: `tests/test_api/test_engine_routes.py`
- Modify: `server/routes/engine.py`

**Step 1: Write failing tests**

```python
# tests/test_api/test_engine_routes.py
"""Tests for interactive engine session endpoints."""
import pytest
from fastapi.testclient import TestClient
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session_id(client):
    """Start a MiniCap session and return the session ID."""
    resp = client.post("/api/v1/engine/start", json={"game_id": "minicap"})
    assert resp.status_code == 200
    return resp.json()["session_id"]


class TestStartSession:
    def test_start_creates_session(self, client):
        resp = client.post("/api/v1/engine/start", json={"game_id": "minicap"})
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["game_id"] == "minicap"
        assert data["elapsed_time"] == 0.0
        assert "resources" in data
        assert "generators" in data

    def test_start_nonexistent_game_404(self, client):
        resp = client.post("/api/v1/engine/start", json={"game_id": "nope"})
        assert resp.status_code == 404


class TestGetState:
    def test_get_state(self, client, session_id):
        resp = client.get(f"/api/v1/engine/{session_id}/state")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

    def test_get_nonexistent_session_404(self, client):
        resp = client.get("/api/v1/engine/fake-id/state")
        assert resp.status_code == 404


class TestAdvance:
    def test_advance_increases_time(self, client, session_id):
        resp = client.post(f"/api/v1/engine/{session_id}/advance", json={"seconds": 5.0})
        assert resp.status_code == 200
        assert resp.json()["elapsed_time"] == pytest.approx(5.0, abs=0.1)

    def test_advance_increases_resources(self, client, session_id):
        # First advance to generate some cash
        client.post(f"/api/v1/engine/{session_id}/advance", json={"seconds": 10.0})
        resp = client.get(f"/api/v1/engine/{session_id}/state")
        data = resp.json()
        # Should have some cash after advancing (initial balance + production)
        cash = data["resources"].get("cash", {}).get("current_value", 0)
        assert cash > 0


class TestPurchase:
    def test_purchase_generator(self, client, session_id):
        # Advance to accumulate cash
        client.post(f"/api/v1/engine/{session_id}/advance", json={"seconds": 30.0})
        resp = client.post(f"/api/v1/engine/{session_id}/purchase", json={
            "node_id": "lemonade",
            "count": 1,
        })
        assert resp.status_code == 200
        # Verify owned count increased
        data = resp.json()
        assert data["generators"]["lemonade"]["owned"] >= 1

    def test_purchase_nonexistent_node_400(self, client, session_id):
        resp = client.post(f"/api/v1/engine/{session_id}/purchase", json={
            "node_id": "nonexistent",
        })
        assert resp.status_code == 400


class TestAutoOptimize:
    def test_auto_optimize_returns_purchases(self, client, session_id):
        resp = client.post(f"/api/v1/engine/{session_id}/auto-optimize", json={
            "target_time": 60.0,
            "max_steps": 50,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "purchases" in data
        assert "timeline" in data
        assert data["final_production"] > 0


class TestDeleteSession:
    def test_delete_session(self, client, session_id):
        resp = client.delete(f"/api/v1/engine/{session_id}")
        assert resp.status_code == 204
        # Verify gone
        resp = client.get(f"/api/v1/engine/{session_id}/state")
        assert resp.status_code == 404
```

Run: `pytest tests/test_api/test_engine_routes.py -v`
Expected: FAIL

**Step 2: Implement session manager**

```python
# server/sessions.py
"""In-memory engine session manager."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from idleframework.engine.segments import PiecewiseEngine
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
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
            from idleframework.engine.solvers import bulk_cost
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
```

**Step 3: Implement engine routes**

```python
# server/routes/engine.py
"""Interactive engine session endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from idleframework.engine.solvers import bulk_purchase_cost
from idleframework.bigfloat import BigFloat
from idleframework.model.nodes import Generator, Upgrade, PrestigeLayer, Achievement
from idleframework.optimizer.greedy import GreedyOptimizer
from server.game_store import game_store
from server.schemas import (
    StartSessionRequest, AdvanceRequest, PurchaseRequest, AutoOptimizeRequest,
    SessionState, ResourceState, GeneratorState, UpgradeState,
    PrestigeState, AchievementState,
    AutoOptimizeResponse, PurchaseStepResponse, TimelineEntry,
    ErrorResponse,
)
from server.sessions import session_manager

router = APIRouter()


def _get_session_or_404(session_id: str):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="session_not_found",
            detail=f"No session with ID '{session_id}' exists",
            status=404,
        ).model_dump())
    return session


def _build_state(session) -> SessionState:
    """Build SessionState response from an engine session."""
    engine = session.engine
    game = session.game
    rates = engine.compute_production_rates()
    primary = engine._get_primary_resource_id()
    balance = engine.get_balance(primary) if primary else 0.0

    resources = {}
    generators = {}
    upgrades = {}
    achievements = []

    for node in game.nodes:
        ns = engine.state.get(node.id)
        if isinstance(node, Generator):
            gen_mult = engine._compute_generator_multipliers().get(node.id, 1.0)
            prod = node.base_production * ns.owned / node.cycle_time * gen_mult if ns.owned > 0 else 0.0
            cost_bf = bulk_purchase_cost(
                BigFloat(node.cost_base), BigFloat(node.cost_growth_rate), ns.owned, 1,
            )
            generators[node.id] = GeneratorState(
                owned=ns.owned,
                cost_next=float(cost_bf),
                production_per_sec=prod,
            )
        elif isinstance(node, Upgrade):
            upgrades[node.id] = UpgradeState(
                purchased=ns.purchased,
                cost=node.cost,
                affordable=balance >= node.cost and not ns.purchased,
            )
        elif node.type == "resource":
            resources[node.id] = ResourceState(
                current_value=ns.current_value,
                production_rate=rates.get(node.id, 0.0),
            )
        elif isinstance(node, Achievement):
            achievements.append(AchievementState(
                id=node.id,
                name=node.name,
                unlocked=ns.purchased,
            ))

    prestige = None
    for node in game.nodes:
        if isinstance(node, PrestigeLayer):
            prestige = PrestigeState(
                available_currency=0.0,
                formula_preview=node.formula_expr,
            )
            break

    return SessionState(
        session_id=session.session_id,
        game_id=session.game_id,
        elapsed_time=engine.current_time,
        resources=resources,
        generators=generators,
        upgrades=upgrades,
        prestige=prestige,
        achievements=achievements,
    )


@router.post("/start", response_model=SessionState)
def start_session(req: StartSessionRequest):
    game = game_store.get_game(req.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{req.game_id}' exists",
            status=404,
        ).model_dump())
    session = session_manager.create(req.game_id, game, req.initial_balance)
    return _build_state(session)


@router.get("/{session_id}/state", response_model=SessionState)
def get_state(session_id: str):
    session = _get_session_or_404(session_id)
    return _build_state(session)


@router.post("/{session_id}/advance", response_model=SessionState)
def advance(session_id: str, req: AdvanceRequest):
    session = _get_session_or_404(session_id)
    engine = session.engine
    rates = engine.compute_production_rates()
    engine._accumulate(rates, req.seconds)
    engine._time += req.seconds
    engine.state.elapsed_time = engine._time
    return _build_state(session)


@router.post("/{session_id}/purchase", response_model=SessionState)
def purchase(session_id: str, req: PurchaseRequest):
    session = _get_session_or_404(session_id)
    engine = session.engine

    # Validate node exists and is purchasable
    try:
        node = session.game.get_node(req.node_id)
    except KeyError:
        raise HTTPException(status_code=400, detail=ErrorResponse(
            error="invalid_purchase",
            detail=f"Node '{req.node_id}' not found",
            status=400,
        ).model_dump())

    if not isinstance(node, (Generator, Upgrade)):
        raise HTTPException(status_code=400, detail=ErrorResponse(
            error="invalid_purchase",
            detail=f"Node '{req.node_id}' is not purchasable",
            status=400,
        ).model_dump())

    for _ in range(req.count):
        engine.purchase(req.node_id)

    return _build_state(session)


@router.post("/{session_id}/prestige", response_model=SessionState)
def prestige(session_id: str):
    session = _get_session_or_404(session_id)
    engine = session.engine
    engine.prestige()
    return _build_state(session)


@router.post("/{session_id}/auto-optimize", response_model=AutoOptimizeResponse)
def auto_optimize(session_id: str, req: AutoOptimizeRequest):
    session = _get_session_or_404(session_id)
    optimizer = GreedyOptimizer(session.game, session.engine.state)
    result = optimizer.optimize(target_time=req.target_time, max_steps=req.max_steps)

    purchases = [
        PurchaseStepResponse(time=p.time, node_id=p.node_id, count=p.count, cost=p.cost)
        for p in result.purchases
    ]
    timeline = [
        TimelineEntry(time=t["time"], production_rate=t["production_rate"])
        for t in result.timeline
    ]

    return AutoOptimizeResponse(
        purchases=purchases,
        timeline=timeline,
        final_production=result.final_production,
        final_balance=result.final_balance,
    )


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str):
    if not session_manager.delete(session_id):
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="session_not_found",
            detail=f"No session with ID '{session_id}' exists",
            status=404,
        ).model_dump())
    return Response(status_code=204)
```

**Step 4: Run tests**

Run: `pytest tests/test_api/test_engine_routes.py -v`
Expected: All PASS

Note: Some engine methods like `prestige()` and `_accumulate()` may need minor adjustments if the library doesn't expose them exactly as called here. The implementer should check `PiecewiseEngine`'s public API and adapt accordingly. The tests define the contract — make the code match the tests.

**Step 5: Run full test suite (library + API)**

Run: `pytest tests/ -v --timeout=300`
Expected: All existing 401 tests + new API tests PASS

**Step 6: Commit**

```bash
git add server/sessions.py server/routes/engine.py tests/test_api/test_engine_routes.py
git commit -m "feat: engine session routes — start, advance, purchase, prestige, auto-optimize"
```

---

## Task 5: Frontend Scaffold

**Files:**
- Create: `frontend/` (entire Vite + React + TS + Tailwind project)

**Step 1: Scaffold the frontend project**

```bash
cd /home/zaia/Development/IdleFramework
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install react-router-dom
npm install react-plotly.js plotly.js
```

**Step 2: Configure Tailwind**

Add the Tailwind Vite plugin to `frontend/vite.config.ts`:

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

Replace `frontend/src/index.css` with:

```css
@import "tailwindcss";
```

**Step 3: Create app shell with routing**

```typescript
// frontend/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
```

```typescript
// frontend/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import PlayPage from './pages/PlayPage'
import AnalyzePage from './pages/AnalyzePage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/play" element={<PlayPage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/" element={<Navigate to="/play" replace />} />
      </Route>
    </Routes>
  )
}
```

```typescript
// frontend/src/components/layout/Layout.tsx
import { Outlet } from 'react-router-dom'
import Nav from './Nav'

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Nav />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
```

```typescript
// frontend/src/components/layout/Nav.tsx
import { NavLink } from 'react-router-dom'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive
      ? 'bg-blue-600 text-white'
      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
  }`

export default function Nav() {
  return (
    <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-2">
        <span className="font-bold text-lg mr-4">IdleFramework</span>
        <NavLink to="/play" className={linkClass}>Play</NavLink>
        <NavLink to="/analyze" className={linkClass}>Analyze</NavLink>
        <a
          href="https://github.com/ac2522/IdleFramework"
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          GitHub
        </a>
      </div>
    </nav>
  )
}
```

```typescript
// frontend/src/pages/PlayPage.tsx
export default function PlayPage() {
  return <div className="text-center py-20 text-gray-400">Play Page — coming soon</div>
}
```

```typescript
// frontend/src/pages/AnalyzePage.tsx
export default function AnalyzePage() {
  return <div className="text-center py-20 text-gray-400">Analyze Page — coming soon</div>
}
```

**Step 4: Clean up Vite defaults**

Delete `frontend/src/App.css` and any other default Vite boilerplate files that were replaced.

**Step 5: Verify frontend builds and runs**

Run: `cd frontend && npm run build && npm run dev`
Expected: Dev server starts on port 5173, shows nav with Play/Analyze links

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffold — Vite + React + TypeScript + Tailwind + Router"
```

---

## Task 6: API Client + Types + Utilities

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/games.ts`
- Create: `frontend/src/api/analysis.ts`
- Create: `frontend/src/api/engine.ts`
- Create: `frontend/src/utils/formatting.ts`

**Step 1: Create TypeScript types**

```typescript
// frontend/src/api/types.ts
export interface ResourceState {
  current_value: number
  production_rate: number
}

export interface GeneratorState {
  owned: number
  cost_next: number
  production_per_sec: number
}

export interface UpgradeState {
  purchased: boolean
  cost: number
  affordable: boolean
}

export interface PrestigeState {
  available_currency: number
  formula_preview: string
}

export interface AchievementState {
  id: string
  name: string
  unlocked: boolean
}

export interface SessionState {
  session_id: string
  game_id: string
  elapsed_time: number
  resources: Record<string, ResourceState>
  generators: Record<string, GeneratorState>
  upgrades: Record<string, UpgradeState>
  prestige: PrestigeState | null
  achievements: AchievementState[]
}

export interface GameSummary {
  id: string
  name: string
  node_count: number
  edge_count: number
  bundled: boolean
}

export interface PurchaseStep {
  time: number
  node_id: string
  cost: number
  count: number
}

export interface TimelineEntry {
  time: number
  production_rate: number
}

export interface AutoOptimizeResponse {
  purchases: PurchaseStep[]
  timeline: TimelineEntry[]
  final_production: number
  final_balance: number
}

export interface AnalysisResult {
  game_name: string
  simulation_time: number
  dead_upgrades: Array<{ upgrade_id: string; reason: string; cost?: number }>
  progression_walls: Array<{ reason: string; severity?: string }>
  dominant_strategy: { dominant_gen: string | null; ratio: number; productions: Record<string, number> } | null
  optimizer_result: {
    purchases: PurchaseStep[]
    timeline: TimelineEntry[]
    final_production: number
    final_balance: number
    final_time: number
  } | null
}

export interface CompareResult {
  baseline: { final_production: number }
  variants: Record<string, { final_production: number; ratio_vs_baseline: number }>
}

export interface ApiError {
  error: string
  detail: string
  status: number
}
```

**Step 2: Create base API client**

```typescript
// frontend/src/api/client.ts
import type { ApiError } from './types'

export class ApiClientError extends Error {
  constructor(public readonly apiError: ApiError) {
    super(apiError.detail)
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let apiError: ApiError
    try {
      const body = await res.json()
      apiError = body.detail ?? body
    } catch {
      apiError = { error: 'unknown', detail: res.statusText, status: res.status }
    }
    throw new ApiClientError(apiError)
  }
  return res.json()
}
```

**Step 3: Create endpoint modules**

```typescript
// frontend/src/api/games.ts
import { apiFetch } from './client'
import type { GameSummary } from './types'

export async function listGames(): Promise<{ games: GameSummary[] }> {
  return apiFetch('/games/')
}

export async function getGame(gameId: string): Promise<Record<string, unknown>> {
  return apiFetch(`/games/${gameId}`)
}

export async function createGame(gameJson: Record<string, unknown>): Promise<{ id: string; name: string }> {
  return apiFetch('/games/', { method: 'POST', body: JSON.stringify(gameJson) })
}

export async function deleteGame(gameId: string): Promise<void> {
  await fetch(`/api/v1/games/${gameId}`, { method: 'DELETE' })
}
```

```typescript
// frontend/src/api/analysis.ts
import { apiFetch } from './client'
import type { AnalysisResult, CompareResult } from './types'

export async function runAnalysis(params: {
  game_id: string
  simulation_time?: number
  optimizer?: string
}): Promise<AnalysisResult> {
  return apiFetch('/analysis/run', { method: 'POST', body: JSON.stringify(params) })
}

export async function compareStrategies(params: {
  game_id: string
  strategies?: string[]
  simulation_time?: number
}): Promise<CompareResult> {
  return apiFetch('/analysis/compare', { method: 'POST', body: JSON.stringify(params) })
}

export async function generateReport(params: {
  game_id: string
  simulation_time?: number
}): Promise<string> {
  const res = await fetch('/api/v1/analysis/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return res.text()
}
```

```typescript
// frontend/src/api/engine.ts
import { apiFetch } from './client'
import type { SessionState, AutoOptimizeResponse } from './types'

export async function startSession(gameId: string, initialBalance = 50): Promise<SessionState> {
  return apiFetch('/engine/start', {
    method: 'POST',
    body: JSON.stringify({ game_id: gameId, initial_balance: initialBalance }),
  })
}

export async function getState(sessionId: string): Promise<SessionState> {
  return apiFetch(`/engine/${sessionId}/state`)
}

export async function advance(sessionId: string, seconds = 1): Promise<SessionState> {
  return apiFetch(`/engine/${sessionId}/advance`, {
    method: 'POST',
    body: JSON.stringify({ seconds }),
  })
}

export async function purchase(sessionId: string, nodeId: string, count = 1): Promise<SessionState> {
  return apiFetch(`/engine/${sessionId}/purchase`, {
    method: 'POST',
    body: JSON.stringify({ node_id: nodeId, count }),
  })
}

export async function prestige(sessionId: string): Promise<SessionState> {
  return apiFetch(`/engine/${sessionId}/prestige`, { method: 'POST' })
}

export async function autoOptimize(sessionId: string, params?: {
  target_time?: number
  max_steps?: number
}): Promise<AutoOptimizeResponse> {
  return apiFetch(`/engine/${sessionId}/auto-optimize`, {
    method: 'POST',
    body: JSON.stringify(params ?? {}),
  })
}
```

**Step 4: Create number formatting utility**

```typescript
// frontend/src/utils/formatting.ts
const SUFFIXES = ['', 'K', 'M', 'B', 'T', 'Qa', 'Qi', 'Sx', 'Sp', 'Oc', 'No', 'Dc']

export function formatNumber(value: number): string {
  if (value === 0) return '0'
  if (Math.abs(value) < 0.01) return value.toExponential(2)
  if (Math.abs(value) < 1000) return value.toFixed(value < 10 ? 1 : 0)

  const tier = Math.floor(Math.log10(Math.abs(value)) / 3)
  if (tier > 0 && tier < SUFFIXES.length) {
    const scaled = value / Math.pow(10, tier * 3)
    return `${scaled.toFixed(2)} ${SUFFIXES[tier]}`
  }
  const exp = Math.floor(Math.log10(Math.abs(value)))
  const mant = value / Math.pow(10, exp)
  return `${mant.toFixed(2)}e${exp}`
}

export function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}
```

**Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 6: Commit**

```bash
git add frontend/src/api/ frontend/src/utils/
git commit -m "feat: typed API client + number formatting utilities"
```

---

## Task 7: Play Page — Core Game Loop

**Files:**
- Create: `frontend/src/hooks/useGameSession.ts`
- Create: `frontend/src/hooks/useGameTick.ts`
- Create: `frontend/src/components/game/ResourceDisplay.tsx`
- Create: `frontend/src/components/game/GeneratorCard.tsx`
- Create: `frontend/src/components/game/ProductionSummary.tsx`
- Modify: `frontend/src/pages/PlayPage.tsx`

**Step 1: Create useGameSession hook**

```typescript
// frontend/src/hooks/useGameSession.ts
import { useState, useEffect, useCallback } from 'react'
import type { SessionState } from '../api/types'
import * as engineApi from '../api/engine'

export function useGameSession(gameId: string) {
  const [state, setState] = useState<SessionState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    engineApi.startSession(gameId).then(
      (s) => { if (!cancelled) { setState(s); setLoading(false) } },
      (e) => { if (!cancelled) { setError(e.message); setLoading(false) } },
    )

    return () => { cancelled = true }
  }, [gameId])

  const advanceTime = useCallback(async (seconds: number) => {
    if (!state) return
    try {
      const newState = await engineApi.advance(state.session_id, seconds)
      setState(newState)
    } catch (e: any) {
      setError(e.message)
    }
  }, [state?.session_id])

  const purchaseItem = useCallback(async (nodeId: string, count = 1) => {
    if (!state) return
    try {
      const newState = await engineApi.purchase(state.session_id, nodeId, count)
      setState(newState)
    } catch (e: any) {
      setError(e.message)
    }
  }, [state?.session_id])

  const triggerPrestige = useCallback(async () => {
    if (!state) return
    try {
      const newState = await engineApi.prestige(state.session_id)
      setState(newState)
    } catch (e: any) {
      setError(e.message)
    }
  }, [state?.session_id])

  return { state, loading, error, advanceTime, purchaseItem, triggerPrestige, setState }
}
```

**Step 2: Create useGameTick hook**

```typescript
// frontend/src/hooks/useGameTick.ts
import { useEffect, useRef } from 'react'

export function useGameTick(
  callback: (seconds: number) => void,
  speed: number,
  enabled: boolean,
) {
  const callbackRef = useRef(callback)
  callbackRef.current = callback

  useEffect(() => {
    if (!enabled) return
    const interval = setInterval(() => {
      callbackRef.current(speed)
    }, 1000)
    return () => clearInterval(interval)
  }, [speed, enabled])
}
```

**Step 3: Create game UI components**

```typescript
// frontend/src/components/game/ResourceDisplay.tsx
import type { ResourceState } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface Props {
  resources: Record<string, ResourceState>
}

export default function ResourceDisplay({ resources }: Props) {
  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Resources</h2>
      {Object.entries(resources).map(([id, res]) => (
        <div key={id} className="bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm">
          <div className="font-medium capitalize">{id}</div>
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {formatNumber(res.current_value)}
          </div>
          <div className="text-xs text-gray-500">
            {formatNumber(res.production_rate)}/s
          </div>
        </div>
      ))}
    </div>
  )
}
```

```typescript
// frontend/src/components/game/GeneratorCard.tsx
import type { GeneratorState } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface Props {
  id: string
  gen: GeneratorState
  balance: number
  onBuy: (id: string, count: number) => void
}

export default function GeneratorCard({ id, gen, balance, onBuy }: Props) {
  const affordable = balance >= gen.cost_next

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium capitalize">{id.replace(/_/g, ' ')}</span>
        <span className="text-sm text-gray-500">x{gen.owned}</span>
      </div>
      <div className="text-sm text-gray-500 mb-3">
        {formatNumber(gen.production_per_sec)}/s
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-sm font-mono ${affordable ? 'text-green-600' : 'text-gray-400'}`}>
          {formatNumber(gen.cost_next)}
        </span>
        <div className="flex gap-1 ml-auto">
          <button
            onClick={() => onBuy(id, 1)}
            disabled={!affordable}
            className="px-3 py-1 text-xs rounded bg-blue-600 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
          >
            Buy 1
          </button>
          <button
            onClick={() => onBuy(id, 10)}
            className="px-3 py-1 text-xs rounded bg-blue-500 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-blue-600 transition-colors"
          >
            Buy 10
          </button>
        </div>
      </div>
    </div>
  )
}
```

```typescript
// frontend/src/components/game/ProductionSummary.tsx
import type { ResourceState } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface Props {
  resources: Record<string, ResourceState>
  elapsedTime: number
}

export default function ProductionSummary({ resources, elapsedTime }: Props) {
  const totalRate = Object.values(resources).reduce((sum, r) => sum + r.production_rate, 0)

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
        Production
      </h2>
      <div className="text-xl font-bold text-green-600 dark:text-green-400">
        {formatNumber(totalRate)}/s
      </div>
      <div className="text-xs text-gray-500 mt-1">
        Time: {Math.floor(elapsedTime)}s
      </div>
    </div>
  )
}
```

**Step 4: Assemble Play Page**

```typescript
// frontend/src/pages/PlayPage.tsx
import { useState, useCallback } from 'react'
import { useGameSession } from '../hooks/useGameSession'
import { useGameTick } from '../hooks/useGameTick'
import ResourceDisplay from '../components/game/ResourceDisplay'
import GeneratorCard from '../components/game/GeneratorCard'
import ProductionSummary from '../components/game/ProductionSummary'

export default function PlayPage() {
  const [gameId] = useState('minicap')
  const [speed, setSpeed] = useState(1)
  const [running, setRunning] = useState(true)
  const { state, loading, error, advanceTime, purchaseItem } = useGameSession(gameId)

  useGameTick(
    useCallback((s: number) => advanceTime(s), [advanceTime]),
    speed,
    running && !!state,
  )

  if (loading) return <div className="text-center py-20">Loading game...</div>
  if (error) return <div className="text-center py-20 text-red-500">Error: {error}</div>
  if (!state) return null

  const primaryResource = Object.entries(state.resources)[0]
  const balance = primaryResource ? primaryResource[1].current_value : 0

  return (
    <div className="grid grid-cols-[240px_1fr] gap-6">
      {/* Left sidebar */}
      <div className="space-y-4">
        <ResourceDisplay resources={state.resources} />
        <ProductionSummary resources={state.resources} elapsedTime={state.elapsed_time} />
      </div>

      {/* Main area */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => setRunning(!running)}
            className="px-4 py-2 rounded bg-gray-200 dark:bg-gray-700 text-sm font-medium"
          >
            {running ? 'Pause' : 'Resume'}
          </button>
          {[1, 10, 100].map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
                speed === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
          Generators
        </h2>
        <div className="space-y-3">
          {Object.entries(state.generators).map(([id, gen]) => (
            <GeneratorCard
              key={id}
              id={id}
              gen={gen}
              balance={balance}
              onBuy={purchaseItem}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
```

**Step 5: Verify the full stack works**

Run (two terminals):
- Terminal 1: `make server`
- Terminal 2: `cd frontend && npm run dev`

Expected: Visit http://localhost:5173/play, see MiniCap game with generators, cash ticking up, buy buttons work.

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: Play Page core — game session, tick loop, resource display, generator cards"
```

---

## Task 8: Play Page — Upgrades + Prestige

**Files:**
- Create: `frontend/src/components/game/UpgradeCard.tsx`
- Create: `frontend/src/components/game/PrestigePanel.tsx`
- Modify: `frontend/src/pages/PlayPage.tsx`

**Step 1: Create upgrade card**

```typescript
// frontend/src/components/game/UpgradeCard.tsx
import type { UpgradeState } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface Props {
  id: string
  upgrade: UpgradeState
  onBuy: (id: string) => void
}

export default function UpgradeCard({ id, upgrade, onBuy }: Props) {
  if (upgrade.purchased) return null

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm flex items-center justify-between">
      <div>
        <div className="font-medium text-sm capitalize">{id.replace(/_/g, ' ')}</div>
        <div className={`text-xs font-mono ${upgrade.affordable ? 'text-green-600' : 'text-gray-400'}`}>
          {formatNumber(upgrade.cost)}
        </div>
      </div>
      <button
        onClick={() => onBuy(id)}
        disabled={!upgrade.affordable}
        className="px-3 py-1 text-xs rounded bg-amber-500 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-amber-600 transition-colors"
      >
        Buy
      </button>
    </div>
  )
}
```

**Step 2: Create prestige panel**

```typescript
// frontend/src/components/game/PrestigePanel.tsx
import type { PrestigeState } from '../../api/types'

interface Props {
  prestige: PrestigeState | null
  onPrestige: () => void
}

export default function PrestigePanel({ prestige, onPrestige }: Props) {
  if (!prestige) return null

  return (
    <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-purple-600 dark:text-purple-400 mb-2">
        Prestige
      </h2>
      <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
        Formula: {prestige.formula_preview}
      </div>
      <button
        onClick={onPrestige}
        className="w-full px-4 py-2 rounded bg-purple-600 text-white hover:bg-purple-700 transition-colors text-sm font-medium"
      >
        Prestige
      </button>
    </div>
  )
}
```

**Step 3: Add upgrades and prestige to PlayPage**

Add the upgrade list and prestige panel to the left sidebar of the PlayPage, below the production summary. Import and render `UpgradeCard` for each unpurchased upgrade in `state.upgrades`, and `PrestigePanel` with `state.prestige` and the `triggerPrestige` callback.

**Step 4: Verify**

Run the full stack. Buy generators, accumulate cash, buy upgrades. Prestige button should reset the game.

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: Play Page upgrades + prestige panel"
```

---

## Task 9: Play Page — Auto-Optimizer

**Files:**
- Create: `frontend/src/hooks/useAutoOptimize.ts`
- Create: `frontend/src/components/game/PurchaseTimeline.tsx`
- Modify: `frontend/src/pages/PlayPage.tsx`

**Step 1: Create useAutoOptimize hook**

```typescript
// frontend/src/hooks/useAutoOptimize.ts
import { useState, useCallback } from 'react'
import type { AutoOptimizeResponse } from '../api/types'
import * as engineApi from '../api/engine'

export function useAutoOptimize(sessionId: string | null) {
  const [result, setResult] = useState<AutoOptimizeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (targetTime = 300, maxSteps = 200) => {
    if (!sessionId) return
    setLoading(true)
    setError(null)
    try {
      const res = await engineApi.autoOptimize(sessionId, {
        target_time: targetTime,
        max_steps: maxSteps,
      })
      setResult(res)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  const clear = useCallback(() => setResult(null), [])

  return { result, loading, error, run, clear }
}
```

**Step 2: Create purchase timeline component**

```typescript
// frontend/src/components/game/PurchaseTimeline.tsx
import type { PurchaseStep } from '../../api/types'
import { formatNumber, formatTime } from '../../utils/formatting'

interface Props {
  purchases: PurchaseStep[]
  finalProduction: number
  finalBalance: number
}

export default function PurchaseTimeline({ purchases, finalProduction, finalBalance }: Props) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex gap-6">
        <div>
          <div className="text-xs text-gray-500">Final Production</div>
          <div className="font-bold text-green-600">{formatNumber(finalProduction)}/s</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Final Balance</div>
          <div className="font-bold text-blue-600">{formatNumber(finalBalance)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Purchases</div>
          <div className="font-bold">{purchases.length}</div>
        </div>
      </div>
      <div className="max-h-64 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700 sticky top-0">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-500">Time</th>
              <th className="px-4 py-2 text-left font-medium text-gray-500">Node</th>
              <th className="px-4 py-2 text-right font-medium text-gray-500">Cost</th>
            </tr>
          </thead>
          <tbody>
            {purchases.map((p, i) => (
              <tr key={i} className="border-t border-gray-100 dark:border-gray-700">
                <td className="px-4 py-2 text-gray-500">{formatTime(p.time)}</td>
                <td className="px-4 py-2 capitalize">{p.node_id.replace(/_/g, ' ')}</td>
                <td className="px-4 py-2 text-right font-mono">{formatNumber(p.cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

**Step 3: Add auto-optimize button and timeline to PlayPage**

Add an "Auto-Optimize" button in the controls bar. When clicked, pause the game tick, call the optimizer, display the purchase timeline below the generators panel. Add a "Clear" button to dismiss results and resume playing.

**Step 4: Verify**

Start the game, click Auto-Optimize, see the purchase timeline appear with all steps.

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: Play Page auto-optimizer with purchase timeline display"
```

---

## Task 10: Analyze Page — Controls + Results

**Files:**
- Create: `frontend/src/hooks/useAnalysis.ts`
- Create: `frontend/src/components/analysis/AnalysisControls.tsx`
- Create: `frontend/src/components/analysis/ResultsPanel.tsx`
- Modify: `frontend/src/pages/AnalyzePage.tsx`

**Step 1: Create useAnalysis hook**

```typescript
// frontend/src/hooks/useAnalysis.ts
import { useState, useCallback } from 'react'
import type { AnalysisResult, CompareResult } from '../api/types'
import * as analysisApi from '../api/analysis'

export function useAnalysis() {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runAnalysis = useCallback(async (gameId: string, simulationTime: number, optimizer: string) => {
    setLoading(true)
    setError(null)
    setCompareResult(null)
    try {
      const res = await analysisApi.runAnalysis({
        game_id: gameId,
        simulation_time: simulationTime,
        optimizer,
      })
      setResult(res)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const runCompare = useCallback(async (gameId: string, simulationTime: number) => {
    setLoading(true)
    setError(null)
    try {
      const res = await analysisApi.compareStrategies({
        game_id: gameId,
        strategies: ['free', 'paid'],
        simulation_time: simulationTime,
      })
      setCompareResult(res)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, compareResult, loading, error, runAnalysis, runCompare }
}
```

**Step 2: Create AnalysisControls component**

A form with: game dropdown (populated from `listGames()`), optimizer tier select (greedy/beam/mcts/bnb), simulation time input, "Run Analysis" and "Compare Free vs Paid" buttons.

**Step 3: Create ResultsPanel component**

Shows dead upgrades, progression walls, dominant strategy, and summary stats from the analysis result. Uses simple card layout.

**Step 4: Assemble AnalyzePage**

Wire controls to `useAnalysis` hook. Show results panel when analysis completes. Show loading spinner while running.

**Step 5: Verify**

Navigate to /analyze, select MiniCap, click Run Analysis. Results should appear.

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: Analyze Page — controls, analysis execution, results display"
```

---

## Task 11: Analyze Page — Charts

**Files:**
- Create: `frontend/src/components/analysis/ChartPanel.tsx`
- Modify: `frontend/src/pages/AnalyzePage.tsx`

**Step 1: Create ChartPanel with Plotly charts**

```typescript
// frontend/src/components/analysis/ChartPanel.tsx
import Plot from 'react-plotly.js'
import type { AnalysisResult } from '../../api/types'

interface Props {
  result: AnalysisResult
}

export default function ChartPanel({ result }: Props) {
  const opt = result.optimizer_result
  if (!opt) return null

  return (
    <div className="space-y-6">
      {/* Production Rate Over Time */}
      {opt.timeline.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
          <Plot
            data={[{
              x: opt.timeline.map(t => t.time),
              y: opt.timeline.map(t => t.production_rate),
              type: 'scatter',
              mode: 'lines+markers',
              name: 'Production Rate',
              line: { color: '#3b82f6' },
            }]}
            layout={{
              title: 'Production Rate Over Time',
              xaxis: { title: 'Time (s)' },
              yaxis: { title: 'Rate' },
              margin: { t: 40, r: 20, b: 40, l: 60 },
              height: 300,
              paper_bgcolor: 'transparent',
              plot_bgcolor: 'transparent',
            }}
            config={{ responsive: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* Purchase Cost Distribution */}
      {opt.purchases.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
          <Plot
            data={[{
              x: opt.purchases.map(p => p.node_id),
              y: opt.purchases.map(p => p.cost),
              type: 'bar',
              name: 'Cost',
              marker: { color: '#10b981' },
            }]}
            layout={{
              title: 'Purchase Costs',
              xaxis: { title: 'Node' },
              yaxis: { title: 'Cost' },
              margin: { t: 40, r: 20, b: 40, l: 60 },
              height: 300,
              paper_bgcolor: 'transparent',
              plot_bgcolor: 'transparent',
            }}
            config={{ responsive: true }}
            style={{ width: '100%' }}
          />
        </div>
      )}
    </div>
  )
}
```

**Step 2: Add ChartPanel to AnalyzePage alongside ResultsPanel**

Use a two-column layout: ResultsPanel on left, ChartPanel on right.

**Step 3: Verify**

Run analysis, see Plotly charts render with production curves and cost distribution.

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: Analyze Page Plotly charts — production curves, cost distribution"
```

---

## Task 12: Analyze Page — Comparison + Purchase Timeline

**Files:**
- Create: `frontend/src/components/analysis/ComparisonView.tsx`
- Modify: `frontend/src/pages/AnalyzePage.tsx`

**Step 1: Create ComparisonView component**

Shows baseline production vs each filtered variant, with ratio display. Uses a simple table or card layout.

**Step 2: Add purchase timeline table**

Reuse the `PurchaseTimeline` component from Task 9 on the Analyze Page when analysis results include purchases.

**Step 3: Wire compare button to `useAnalysis.runCompare`**

**Step 4: Verify**

Click "Compare Free vs Paid", see side-by-side results with performance ratios.

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: Analyze Page — strategy comparison view + purchase timeline"
```

---

## Task 13: Game Selector + File Upload

**Files:**
- Modify: `frontend/src/pages/PlayPage.tsx`
- Modify: `frontend/src/pages/AnalyzePage.tsx`
- Create: `frontend/src/components/layout/GameSelector.tsx`

**Step 1: Create GameSelector component**

A dropdown that fetches games from `listGames()`, shows bundled + user games, and includes a "Upload JSON" button that opens a file input and calls `createGame()`.

**Step 2: Add GameSelector to both PlayPage and AnalyzePage**

In PlayPage, changing the game restarts the session with the new game. In AnalyzePage, it updates the game_id for the next analysis run.

**Step 3: Implement file upload**

Upload button reads JSON file, validates it's valid JSON, posts to `POST /games/`, refreshes the game list.

**Step 4: Verify**

Upload a custom game JSON via the UI, see it appear in the dropdown, select it and play/analyze.

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: game selector with file upload on Play and Analyze pages"
```

---

## Task 14: Polish — Loading States, Error Handling, Dark Mode

**Files:**
- Various frontend components

**Step 1: Add loading spinners**

Create a simple `Spinner` component. Show during: session creation, analysis runs, auto-optimize.

**Step 2: Add error display**

Show error messages in a red alert banner when API calls fail. Include retry button.

**Step 3: Verify dark mode works**

Tailwind's `dark:` classes should already work if the user's system preference is dark. Verify all components have appropriate dark variants.

**Step 4: Add favicon and page title**

Update `frontend/index.html` title to "IdleFramework".

**Step 5: Verify full flow end-to-end**

Start server + frontend. Play a game. Run analysis. Upload a custom game. Compare strategies. Check error handling (stop server, verify frontend shows error).

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: UI polish — loading states, error handling, dark mode, responsive layout"
```

---

## Task 15: Integration Tests + Final Verification

**Files:**
- Create: `tests/test_api/test_integration.py`
- Modify: `.gitignore`

**Step 1: Write API integration tests**

```python
# tests/test_api/test_integration.py
"""End-to-end integration tests: full game session lifecycle."""
import pytest
from fastapi.testclient import TestClient
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestFullGameLifecycle:
    def test_play_session_flow(self, client):
        """Start -> advance -> purchase -> advance -> verify state."""
        # Start session
        resp = client.post("/api/v1/engine/start", json={"game_id": "minicap"})
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        # Advance time
        resp = client.post(f"/api/v1/engine/{session_id}/advance", json={"seconds": 30.0})
        assert resp.status_code == 200
        state = resp.json()
        assert state["elapsed_time"] > 0

        # Purchase a generator
        resp = client.post(f"/api/v1/engine/{session_id}/purchase", json={
            "node_id": "lemonade", "count": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["generators"]["lemonade"]["owned"] >= 1

        # Advance more
        resp = client.post(f"/api/v1/engine/{session_id}/advance", json={"seconds": 60.0})
        assert resp.status_code == 200

        # Auto-optimize
        resp = client.post(f"/api/v1/engine/{session_id}/auto-optimize", json={
            "target_time": 120.0, "max_steps": 50,
        })
        assert resp.status_code == 200
        assert len(resp.json()["purchases"]) > 0

        # Cleanup
        resp = client.delete(f"/api/v1/engine/{session_id}")
        assert resp.status_code == 204

    def test_analysis_then_report(self, client):
        """Run analysis, then generate HTML report."""
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "minicap",
            "simulation_time": 60.0,
        })
        assert resp.status_code == 200
        assert resp.json()["optimizer_result"] is not None

        resp = client.post("/api/v1/analysis/report", json={
            "game_id": "minicap",
            "simulation_time": 60.0,
        })
        assert resp.status_code == 200
        assert "<!DOCTYPE html>" in resp.text

    def test_game_upload_and_analyze(self, client):
        """Upload a game, analyze it, delete it."""
        game = {
            "schema_version": "1.0",
            "name": "Integration Test",
            "nodes": [
                {"id": "gold", "type": "resource", "name": "Gold", "initial_value": 0},
                {"id": "miner", "type": "generator", "name": "Miner",
                 "base_production": 1.0, "cost_base": 10.0,
                 "cost_growth_rate": 1.15, "cycle_time": 1.0},
            ],
            "edges": [
                {"id": "e1", "source": "miner", "target": "gold", "edge_type": "production_target"},
            ],
            "stacking_groups": {},
        }
        resp = client.post("/api/v1/games/", json=game)
        assert resp.status_code == 201
        game_id = resp.json()["id"]

        resp = client.post("/api/v1/analysis/run", json={
            "game_id": game_id,
            "simulation_time": 30.0,
        })
        assert resp.status_code == 200

        resp = client.delete(f"/api/v1/games/{game_id}")
        assert resp.status_code == 204
```

**Step 2: Update .gitignore**

```
# Add to .gitignore
frontend/node_modules/
frontend/dist/
server/games/user/
```

**Step 3: Run full test suite**

Run: `pytest tests/ -v --timeout=300`
Expected: All Phase 1 tests (401) + all new API tests PASS

**Step 4: Build and verify production mode**

Run: `make build && make run`
Expected: FastAPI serves the built frontend at http://localhost:8000, all features work.

**Step 5: Commit**

```bash
git add tests/test_api/test_integration.py .gitignore
git commit -m "test: API integration tests + gitignore updates"
```

---

## Execution Order

| Task | Component | Dependencies | Est. Commits |
|------|-----------|-------------|-------------|
| 1 | Server scaffold + deps | None | 1 |
| 2 | Schemas + Game CRUD routes | Task 1 | 1 |
| 3 | Analysis routes | Task 2 | 1 |
| 4 | Engine session routes | Task 2 | 1 |
| 5 | Frontend scaffold | None | 1 |
| 6 | API client + types | Task 5 | 1 |
| 7 | Play Page core | Tasks 4, 6 | 1 |
| 8 | Play Page upgrades + prestige | Task 7 | 1 |
| 9 | Play Page auto-optimizer | Task 7 | 1 |
| 10 | Analyze Page controls + results | Tasks 3, 6 | 1 |
| 11 | Analyze Page charts | Task 10 | 1 |
| 12 | Analyze Page comparison | Task 10 | 1 |
| 13 | Game selector + upload | Tasks 7, 10 | 1 |
| 14 | Polish | Tasks 8, 9, 12 | 1 |
| 15 | Integration tests | All | 1 |

**Parallelizable:** Tasks 1-4 (server) and 5-6 (frontend scaffold) can run in parallel. Tasks 7-9 (Play) and 10-12 (Analyze) are independent after their deps.

**Total:** ~15 commits, 15 tasks.
