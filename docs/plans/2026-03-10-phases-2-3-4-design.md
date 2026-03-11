# IdleFramework Phases 2, 3 & 4 — Design Document

**Date:** 2026-03-10
**Status:** Draft
**Depends on:** Phase 1 (complete — 401 tests, 15 tasks, merged to main)
**Design Doc:** `docs/plans/2026-03-07-idleframework-design.md` (Revision 4)

---

## Executive Summary

Phase 1 delivered a complete Python library with CLI, Plotly reports, and full test suite. Phases 2-4 make the framework **visible and usable** as an open-source showcase:

| Phase | Deliverable | Purpose |
|-------|-------------|---------|
| **Phase 2** | FastAPI backend | REST API wrapping the library |
| **Phase 4** | Example Game UI | Playable demo + auto-optimizer showcase |
| **Phase 3** | React Flow Node Editor | Visual game designer with live analysis |

**Execution order:** Phase 2 + 4 together (API + consumer), then Phase 3 (heaviest, benefits from both existing).

**Deployment model:** Single cloneable repo. `make run` starts everything. FastAPI serves the API at `/api/v1/` and the built frontend as static files at `/`. No external services, no database.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                   Browser                                 │
│  ┌─────────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │ Play Page        │  │ Analyze Page│  │ Node Editor  │ │
│  │ (Phase 4)        │  │ (Phase 4)   │  │ (Phase 3)    │ │
│  └────────┬─────────┘  └──────┬──────┘  └──────┬───────┘ │
└───────────┼────────────────────┼────────────────┼─────────┘
            │ REST               │ REST           │ REST + WS
┌───────────┴────────────────────┴────────────────┴─────────┐
│                   FastAPI (Phase 2)                         │
│  ┌──────────┐  ┌────────────┐  ┌───────────┐              │
│  │ /games/  │  │ /analysis/ │  │ /engine/  │              │
│  └────┬─────┘  └─────┬──────┘  └─────┬─────┘              │
└───────┼───────────────┼───────────────┼────────────────────┘
        │               │               │
┌───────┴───────────────┴───────────────┴────────────────────┐
│              idleframework Python Library (Phase 1)          │
│  GameDefinition · PiecewiseEngine · Optimizers · Analysis    │
│  BigFloat · DSL · Graph Validation · Reports                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
IdleFramework/
├── src/idleframework/              # Phase 1 (existing, unchanged)
│
├── server/                         # Phase 2 — FastAPI backend
│   ├── __init__.py
│   ├── app.py                      # FastAPI app, CORS, static mount, lifespan
│   ├── config.py                   # Settings (port, games dir, CORS origins)
│   ├── dependencies.py             # Shared deps (game loader, session manager)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── games.py                # Game CRUD endpoints
│   │   ├── analysis.py             # Analysis + comparison endpoints
│   │   └── engine.py               # Interactive engine session endpoints
│   ├── schemas.py                  # API request/response Pydantic models
│   ├── sessions.py                 # In-memory engine session manager
│   └── games/                      # Bundled game definitions
│       ├── minicap.json            # Symlink or copy from tests/fixtures/
│       └── mediumcap.json
│
├── frontend/                       # Phase 4 + Phase 3 — React app
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                    # Typed API client
│       │   ├── client.ts           # Base fetch wrapper
│       │   ├── games.ts            # Game endpoints
│       │   ├── analysis.ts         # Analysis endpoints
│       │   ├── engine.ts           # Engine session endpoints
│       │   └── types.ts            # TypeScript types (mirroring Pydantic schemas)
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Nav.tsx         # Top navigation
│       │   │   └── Layout.tsx      # Page shell
│       │   ├── game/               # Phase 4 — playable game components
│       │   │   ├── ResourceDisplay.tsx
│       │   │   ├── GeneratorCard.tsx
│       │   │   ├── UpgradeCard.tsx
│       │   │   ├── PrestigePanel.tsx
│       │   │   ├── ProductionSummary.tsx
│       │   │   └── PurchaseTimeline.tsx
│       │   ├── analysis/           # Phase 4 — analysis display components
│       │   │   ├── AnalysisControls.tsx
│       │   │   ├── ResultsPanel.tsx
│       │   │   ├── ChartPanel.tsx
│       │   │   ├── DeadUpgradeList.tsx
│       │   │   ├── WallIndicator.tsx
│       │   │   └── ComparisonView.tsx
│       │   └── editor/             # Phase 3 — node editor components
│       │       ├── GameCanvas.tsx   # React Flow canvas
│       │       ├── NodePalette.tsx  # Drag-and-drop node creation
│       │       ├── PropertyPanel.tsx # Node/edge property editor
│       │       ├── custom-nodes/    # Custom React Flow node components
│       │       │   ├── ResourceNode.tsx
│       │       │   ├── GeneratorNode.tsx
│       │       │   ├── UpgradeNode.tsx
│       │       │   ├── PrestigeNode.tsx
│       │       │   └── ...
│       │       ├── custom-edges/
│       │       │   ├── ResourceEdge.tsx   # Solid line
│       │       │   └── StateEdge.tsx      # Dotted line
│       │       └── LiveAnalysisPanel.tsx  # Real-time analysis sidebar
│       ├── pages/
│       │   ├── PlayPage.tsx        # Phase 4 — interactive game
│       │   ├── AnalyzePage.tsx     # Phase 4 — analysis dashboard
│       │   └── EditorPage.tsx      # Phase 3 — node editor
│       ├── hooks/
│       │   ├── useGameSession.ts   # Engine session state management
│       │   ├── useAnalysis.ts      # Analysis result state
│       │   ├── useGameTick.ts      # Interval-based game advancement
│       │   └── useAutoOptimize.ts  # Auto-optimizer state + animation
│       └── utils/
│           ├── formatting.ts       # BigFloat display formatting
│           └── constants.ts
│
├── tests/                          # Existing Phase 1 tests + new
│   ├── test_api/                   # Phase 2 API tests
│   │   ├── test_games_routes.py
│   │   ├── test_analysis_routes.py
│   │   └── test_engine_routes.py
│   └── ...
│
├── pyproject.toml                  # Updated with server deps
├── Makefile                        # dev, build, run targets
├── docker-compose.yml              # Optional: single-command startup
└── README.md                       # Updated with usage instructions
```

---

## Phase 2: FastAPI Backend

### Overview

A thin REST API layer wrapping the existing library. No business logic in the server — all computation delegates to `idleframework`. Pydantic models from the library are reused directly where possible.

### Dependencies (additions to pyproject.toml)

```
fastapi>=0.110
uvicorn[standard]>=0.27
python-multipart>=0.0.9   # For file uploads
```

### API Endpoints

#### Game Definitions — `/api/v1/games/`

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| `GET` | `/games/` | List all available games | — | `GameListResponse` |
| `GET` | `/games/{game_id}` | Get a game definition | — | `GameDefinition` (Pydantic) |
| `POST` | `/games/` | Upload a new game definition | `GameDefinition` JSON body | `GameCreateResponse` |
| `POST` | `/games/upload` | Upload a game JSON file | Multipart file | `GameCreateResponse` |
| `DELETE` | `/games/{game_id}` | Delete a user-uploaded game | — | 204 |
| `GET` | `/games/{game_id}/schema` | Export JSON Schema | — | JSON Schema dict |
| `GET` | `/games/{game_id}/export` | Export as YAML or XML | `?format=yaml\|xml` | text |

**Storage:** Game definitions stored as JSON files in `server/games/`. Bundled games (MiniCap, MediumCap) are read-only. User-uploaded games go to a `server/games/user/` subdirectory.

**Game IDs:** Derived from filename (slug of the `name` field). Bundled games have stable IDs (`minicap`, `mediumcap`).

#### Analysis — `/api/v1/analysis/`

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| `POST` | `/analysis/run` | Run full analysis | `AnalysisRequest` | `AnalysisReport` |
| `POST` | `/analysis/compare` | Compare strategies | `CompareRequest` | `CompareResponse` |
| `POST` | `/analysis/report` | Generate HTML report | `ReportRequest` | HTML string |

**Request models:**

```python
class AnalysisRequest(BaseModel):
    game_id: str
    simulation_time: float = 300.0
    optimizer: Literal["greedy", "beam", "mcts", "bnb"] = "greedy"
    beam_width: int = 100           # beam only
    mcts_iterations: int = 1000     # mcts only
    mcts_seed: int | None = None    # mcts only
    bnb_depth: int = 20             # bnb only
    tags: list[str] | None = None   # tag filtering

class CompareRequest(BaseModel):
    game_id: str
    strategies: list[str] = ["free", "paid"]
    simulation_time: float = 300.0

class ReportRequest(BaseModel):
    game_id: str
    simulation_time: float = 300.0
    use_cdn: bool = True
```

**Response models:** Reuse `AnalysisReport` and `OptimizeResult` from the library, wrapped in API response envelopes with request metadata.

#### Engine Sessions — `/api/v1/engine/`

For interactive playable game mode. Sessions are in-memory `PiecewiseEngine` instances.

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| `POST` | `/engine/start` | Start a new game session | `StartSessionRequest` | `SessionState` |
| `GET` | `/engine/{session_id}/state` | Get current state | — | `SessionState` |
| `POST` | `/engine/{session_id}/advance` | Advance time | `AdvanceRequest` | `SessionState` |
| `POST` | `/engine/{session_id}/purchase` | Buy a generator or upgrade | `PurchaseRequest` | `SessionState` |
| `POST` | `/engine/{session_id}/prestige` | Trigger prestige reset | — | `SessionState` |
| `POST` | `/engine/{session_id}/auto-optimize` | Run optimizer from current state | `AutoOptimizeRequest` | `AutoOptimizeResponse` |
| `DELETE` | `/engine/{session_id}` | End session | — | 204 |

**Request models:**

```python
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
```

**Response models:**

```python
class SessionState(BaseModel):
    session_id: str
    game_id: str
    elapsed_time: float
    resources: dict[str, ResourceState]    # id -> {current_value, production_rate}
    generators: dict[str, GeneratorState]  # id -> {owned, cost_next, production_per_sec}
    upgrades: dict[str, UpgradeState]      # id -> {purchased, cost, affordable}
    prestige: PrestigeState | None         # {available_currency, formula_preview}
    achievements: list[AchievementState]   # [{id, name, unlocked}]

class AutoOptimizeResponse(BaseModel):
    purchases: list[PurchaseStep]
    timeline: list[TimelineEntry]
    final_production: float
    final_balance: float
```

### Session Manager

```python
class SessionManager:
    """In-memory engine session store."""

    def __init__(self, max_sessions: int = 100, ttl_seconds: int = 3600):
        self._sessions: dict[str, EngineSession] = {}
        # LRU eviction when max_sessions exceeded
        # TTL-based cleanup on access

    def create(self, game: GameDefinition, initial_balance: float) -> str: ...
    def get(self, session_id: str) -> EngineSession: ...
    def delete(self, session_id: str) -> None: ...
```

- Session IDs: UUID4
- Max 100 concurrent sessions (configurable)
- 1-hour TTL per session
- LRU eviction if limit reached
- No persistence — sessions lost on restart (acceptable for a showcase)

### Configuration

```python
class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    games_dir: str = "server/games"
    cors_origins: list[str] = ["http://localhost:5173"]  # Vite dev server
    max_sessions: int = 100
    session_ttl: int = 3600
```

Loaded from environment variables with `IDLE_` prefix (e.g., `IDLE_PORT=9000`).

### Error Handling

All errors return structured JSON:

```json
{
    "error": "game_not_found",
    "detail": "No game with ID 'foo' exists",
    "status": 404
}
```

Standard error codes:
- `game_not_found` (404)
- `session_not_found` (404)
- `validation_error` (422) — Pydantic validation failures
- `analysis_error` (500) — Engine/optimizer failures
- `session_limit_reached` (429)

### CORS

Dev mode: Allow `http://localhost:5173` (Vite dev server).
Production: Allow same-origin only (frontend served by FastAPI).

### Testing Strategy

- Use FastAPI's `TestClient` (built on httpx)
- Test each route group independently
- Test error cases (bad game IDs, invalid purchases, expired sessions)
- Integration test: start session -> advance -> purchase -> advance -> verify state consistency
- No mocking of the library — tests exercise the real engine

---

## Phase 4: Example Game UI

### Overview

A React + TypeScript + Vite + Tailwind web application with two modes:

1. **Play Mode** — Interactive playable idle game (AdCap-like)
2. **Analyze Mode** — Framework analysis dashboard with charts and insights

Ships with MiniCap loaded by default so there's always something to see on first launch.

### Tech Stack

| Tool | Version | Purpose |
|------|---------|---------|
| React | 19 | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 6.x | Build tool, dev server with HMR |
| Tailwind CSS | 4.x | Utility-first styling |
| React Router | 7.x | Client-side routing |
| Plotly.js | 2.x | Charts (analysis page, matches Phase 1 reports) |
| react-plotly.js | 7.x | React wrapper for Plotly |

No state management library — React hooks + context are sufficient for this scope.

### Pages

#### Play Page (`/play`)

The flagship demo. A simplified AdCap-like interface showing the framework's engine in action.

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│  Nav: [Play] [Analyze]                    MiniCap ▼     │
├──────────────────────┬──────────────────────────────────┤
│                      │                                   │
│  Resources           │  Generators                       │
│  ┌────────────────┐  │  ┌─────────────────────────────┐ │
│  │ 💰 Cash: 1.23M │  │  │ Lemonade Stand     x15      │ │
│  │ 👼 Angels: 0   │  │  │ 1.00/s  Cost: 45.2         │ │
│  └────────────────┘  │  │ [Buy 1] [Buy 10] [Buy Max]  │ │
│                      │  ├─────────────────────────────┤ │
│  Production          │  │ Newspaper Delivery  x8       │ │
│  ┌────────────────┐  │  │ 160/s   Cost: 1.2K          │ │
│  │ Total: 2.5K/s  │  │  │ [Buy 1] [Buy 10] [Buy Max]  │ │
│  └────────────────┘  │  ├─────────────────────────────┤ │
│                      │  │ Car Wash            x3       │ │
│  Upgrades            │  │ 360/s   Cost: 8.4K           │ │
│  ┌────────────────┐  │  │ [Buy 1] [Buy 10] [Buy Max]  │ │
│  │ x3 Lemonade    │  │  └─────────────────────────────┘ │
│  │ Cost: 1K [Buy] │  │                                   │
│  │                │  │  ┌─────────────────────────────┐ │
│  │ x3 Newspaper   │  │  │ Prestige                     │ │
│  │ Cost: 5K [Buy] │  │  │ Reset for: 12 Angels (+2%ea)│ │
│  └────────────────┘  │  │ [Prestige]                   │ │
│                      │  └─────────────────────────────┘ │
├──────────────────────┴──────────────────────────────────┤
│  [▶ Auto-Optimize]  Speed: [1x] [10x] [100x]           │
│  ┌──────────────────────────────────────────────────────┐│
│  │ Purchase Timeline (when auto-optimize is active)      ││
│  │ 0s─────50s─────100s─────150s─────200s─────250s───300s││
│  │ ● buy lemon  ● buy news  ● x3 lemon  ● prestige     ││
│  └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Behavior:**

- On load: Creates an engine session via `POST /engine/start` with MiniCap
- Game tick: `setInterval` calls `POST /engine/{id}/advance` every second (adjusted by speed multiplier)
- Purchases: Click buy -> `POST /engine/{id}/purchase` -> UI updates from response
- Prestige: Click prestige -> `POST /engine/{id}/prestige` -> UI resets visually
- Speed controls: 1x (real-time), 10x, 100x — adjusts the `seconds` param in advance calls
- Auto-Optimize: Calls `POST /engine/{id}/auto-optimize`, then replays the purchase sequence with animated timeline. User watches the optimizer play the game.
- Game selector dropdown: Switch between MiniCap, MediumCap, or uploaded games

**Key UI details:**

- Cash display uses idle-game notation (1.23M, 4.56B, 7.89T) — mirrors `format_bigfloat` from the library
- Generator cost turns green when affordable, grey when not
- Production rate updates smoothly (interpolated between ticks for visual fluidity)
- Achievements pop in as toast notifications when unlocked
- Prestige panel shows a preview of currency gain before committing

#### Analyze Page (`/analyze`)

The framework showcase. Load a game, run the optimizer, see what the framework finds.

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│  Nav: [Play] [Analyze]                                   │
├──────────────────────────────────────────────────────────┤
│  Controls                                                │
│  Game: [MiniCap ▼]  Optimizer: [Greedy ▼]               │
│  Time: [300]s  Tags: [all ▼]  [Run Analysis]            │
│  [Compare: Free vs Paid]                                 │
├──────────────────────┬──────────────────────────────────┤
│  Findings            │  Charts                           │
│  ┌────────────────┐  │  ┌─────────────────────────────┐ │
│  │ Dead Upgrades  │  │  │ Production Rate Over Time    │ │
│  │ • paid_x10:    │  │  │ [Plotly line chart]          │ │
│  │   never bought │  │  │                              │ │
│  ├────────────────┤  │  ├─────────────────────────────┤ │
│  │ Prog. Walls    │  │  │ Purchase Cost Distribution   │ │
│  │ • none found   │  │  │ [Plotly bar chart]           │ │
│  ├────────────────┤  │  ├─────────────────────────────┤ │
│  │ Dominant Strat  │  │  │ Generator Count Breakdown   │ │
│  │ • carwash 2.3x │  │  │ [Plotly bar chart]           │ │
│  ├────────────────┤  │  └─────────────────────────────┘ │
│  │ Summary         │  │                                   │
│  │ • 45 purchases │  │                                   │
│  │ • 2.5e6 prod   │  │                                   │
│  │ • 1.8e7 cash   │  │                                   │
│  └────────────────┘  │                                   │
├──────────────────────┴──────────────────────────────────┤
│  Purchase Timeline                                       │
│  ┌──────────────────────────────────────────────────────┐│
│  │ Time │ Node      │ Cost    │ Efficiency              ││
│  │ 0.0s │ lemonade  │ 4.00    │ 0.250                   ││
│  │ 4.0s │ lemonade  │ 4.28    │ 0.234                   ││
│  │ ...  │ ...       │ ...     │ ...                      ││
│  └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Behavior:**

- Controls panel: Select game, optimizer tier, simulation time, tag filters
- Run Analysis: `POST /analysis/run` -> Display all results
- Compare button: `POST /analysis/compare` -> Side-by-side findings panel with performance gap
- Charts: Rendered with react-plotly.js, matching the library's Plotly report style
- Purchase timeline: Sortable, filterable table
- Upload game: Drag-and-drop JSON file -> `POST /games/upload` -> Available in dropdown
- Loading state: Spinner during analysis (can take seconds for MCTS/B&B)

### API Client

Typed fetch wrapper in `frontend/src/api/`:

```typescript
// types.ts — mirrors server schemas
interface SessionState {
    session_id: string;
    game_id: string;
    elapsed_time: number;
    resources: Record<string, ResourceState>;
    generators: Record<string, GeneratorState>;
    upgrades: Record<string, UpgradeState>;
    prestige: PrestigeState | null;
    achievements: AchievementState[];
}

// client.ts — base wrapper
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`/api/v1${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!res.ok) {
        const error = await res.json();
        throw new ApiError(error);
    }
    return res.json();
}
```

### Custom Hooks

- `useGameSession(gameId)` — Manages session lifecycle (create on mount, cleanup on unmount)
- `useGameTick(sessionId, speed)` — Interval-based `advance` calls, returns latest state
- `useAutoOptimize(sessionId)` — Triggers optimizer, manages animated playback state
- `useAnalysis(gameId)` — Runs analysis, caches results, handles loading/error states

### Styling

- Tailwind CSS utility classes throughout
- Dark/light mode via `dark:` variant, respects `prefers-color-scheme`
- Color palette: Neutral grays for chrome, blue accents for interactive elements, green for "affordable", amber for "prestige available"
- Responsive: Works on desktop (primary), degrades gracefully on tablet. Not targeting mobile.
- No custom CSS files — all Tailwind utilities

### Number Formatting

Frontend mirrors the library's `format_bigfloat` suffixes:

```typescript
const SUFFIXES = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"];

function formatNumber(value: number): string {
    if (value === 0) return "0";
    if (value < 1000) return value.toFixed(value < 10 ? 1 : 0);
    const tier = Math.floor(Math.log10(value) / 3);
    if (tier < SUFFIXES.length) {
        const scaled = value / Math.pow(10, tier * 3);
        return `${scaled.toFixed(2)} ${SUFFIXES[tier]}`;
    }
    const exp = Math.floor(Math.log10(value));
    const mant = value / Math.pow(10, exp);
    return `${mant.toFixed(2)}e${exp}`;
}
```

---

## Phase 3: React Flow Node Editor

### Overview

Visual game designer using React Flow (@xyflow/react v12). Users drag-and-drop nodes, connect edges, edit properties, and see live analysis feedback. This is the "use the framework yourself" tool.

### Dependencies (additions to frontend/package.json)

```
@xyflow/react: ^12
```

### Editor Page (`/editor`)

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│  Nav: [Play] [Analyze] [Editor]          [Save] [Load]  │
├──────────┬──────────────────────────────┬───────────────┤
│  Palette │  Canvas (React Flow)          │  Properties   │
│  ┌──────┐│  ┌───────┐    ┌───────┐      │  ┌──────────┐│
│  │Resrc ││  │ Cash  │───▶│Lemon  │      │  │ Lemonade ││
│  │Gen   ││  └───────┘    │ Stand │      │  │          ││
│  │Upg   ││               └───┬───┘      │  │ base: 1  ││
│  │Prest ││                   │           │  │ cost: 4  ││
│  │Achiev││               ┌───▼───┐      │  │ rate:1.07││
│  │Gate  ││               │ x3    │      │  │ cycle: 1 ││
│  │Reg   ││               │Lemon  │      │  │          ││
│  │Conv  ││               └───────┘      │  │ Tags: [] ││
│  └──────┘│                               │  └──────────┘│
│          │                               │               │
│          │                               │  Live Analysis│
│          │                               │  ┌──────────┐│
│          │                               │  │ Prod: 5/s││
│          │                               │  │ Dead: 0  ││
│          │                               │  │ Walls: 0 ││
│          │                               │  └──────────┘│
├──────────┴──────────────────────────────┴───────────────┤
│  Validation: ✓ Valid (2 nodes, 1 edge)  │ JSON Preview  │
└─────────────────────────────────────────────────────────┘
```

### Components

#### Node Palette (left sidebar)

- Categorized list of all 16 node types from the model
- Drag from palette onto canvas to create a node
- Each entry shows icon + name + brief description
- Categories: Resources, Producers, Modifiers, Meta (prestige/achievement/gate), Advanced (register/converter/queue/gate)

#### Canvas (center)

- React Flow canvas with custom node components
- **Resource edges** (resource_flow, consumption, production_target): Solid colored lines
- **State edges** (state_modifier, activator, trigger, unlock_dependency, upgrade_target): Dotted/dashed lines
- Visual distinction makes the resource-flow vs state-influence separation immediately clear
- Nodes colored by type (e.g., blue for resources, green for generators, orange for upgrades, purple for prestige)
- Minimap in bottom-right corner
- Zoom/pan controls

#### Custom Node Components

Each node type gets a custom React Flow node:

```typescript
// Example: GeneratorNode
function GeneratorNode({ data }: NodeProps<GeneratorNodeData>) {
    return (
        <div className="bg-green-50 border-2 border-green-400 rounded-lg p-3 min-w-48">
            <div className="font-semibold text-green-800">{data.name}</div>
            <div className="text-sm text-green-600">
                <div>Production: {data.base_production}/cycle</div>
                <div>Cost: {data.cost_base} × {data.cost_growth_rate}^n</div>
                <div>Cycle: {data.cycle_time}s</div>
            </div>
            <Handle type="source" position={Position.Right} />
            <Handle type="target" position={Position.Left} />
        </div>
    );
}
```

Node types to implement:
- `ResourceNode` — Shows current value, production rate
- `GeneratorNode` — Shows production formula, cost curve
- `UpgradeNode` — Shows type, magnitude, target, stacking group
- `PrestigeNode` — Shows formula, reset scope, persistence scope
- `AchievementNode` — Shows condition, bonus
- `UnlockGateNode` — Shows prerequisites, condition
- `ChoiceGroupNode` — Shows options, max selections
- `RegisterNode` — Shows formula, inputs
- `ConverterNode` — Shows inputs/outputs, rate
- `EndConditionNode` — Shows target threshold

#### Property Panel (right sidebar)

- Appears when a node or edge is selected
- Form fields matching the Pydantic model for that node type
- Validation feedback inline (red borders + messages for invalid values)
- Stacking group dropdown populated from game-level `stacking_groups`
- Tag editor (chip-style input)
- Formula editor with syntax highlighting for DSL expressions

#### Live Analysis Panel (right sidebar, below properties)

- Runs greedy analysis automatically after each edit (debounced, 500ms)
- Shows: total production rate, dead upgrades count, progression wall count
- Expandable for full analysis details
- Visual indicator: green checkmark (healthy), amber warning (walls/dead upgrades), red alert (validation errors)
- Target: <200ms for greedy on <100 nodes (matches design doc latency requirement)

#### Validation Bar (bottom)

- Real-time validation as user edits
- Shows: node count, edge count, validation status
- Errors: Missing required fields, invalid edge connections, duplicate IDs, broken references
- Mirrors the `GameDefinition` Pydantic validation + `validate_graph` from the library

### Import / Export

- **Save:** Converts React Flow graph state → `GameDefinition` JSON → `POST /games/`
- **Load:** `GET /games/{id}` → Parse → Place nodes on canvas with auto-layout (dagre/elkjs)
- **JSON Preview:** Toggle panel showing the raw game JSON, updated live
- **Download:** Export current game as `.json` file

### WebSocket (Phase 3 only)

For live analysis feedback during editing:

```
WS /api/v1/ws/editor/{session_id}

Client -> Server: { "type": "update_game", "game": GameDefinition }
Server -> Client: { "type": "validation", "errors": [...] }
Server -> Client: { "type": "analysis", "result": AnalysisReport }
```

- Debounced: Server waits 500ms after last update before running analysis
- Validation runs immediately (fast)
- Analysis runs after validation passes (greedy only for speed)

This is the **only WebSocket endpoint** in the entire API. Added in Phase 3 when there's an actual consumer.

---

## Cross-Phase Concerns

### Development Workflow

```bash
# One-command startup
make dev          # Starts FastAPI (port 8000) + Vite dev server (port 5173)

# Or individually
make server       # uvicorn server.app:app --reload --port 8000
make frontend     # cd frontend && npm run dev

# Production build
make build        # Builds frontend, copies to server/static/
make run          # Runs FastAPI serving everything on port 8000

# Docker (optional)
docker-compose up # Single container, everything included
```

### Testing Strategy

| Layer | Tool | What |
|-------|------|------|
| Library | pytest (existing) | 401 existing tests unchanged |
| API routes | pytest + httpx TestClient | Each endpoint, error cases, session lifecycle |
| API integration | pytest | Full flow: create game -> start session -> play -> analyze |
| Frontend components | Vitest + React Testing Library | Component rendering, user interactions |
| Frontend integration | Playwright | Full E2E: load page, play game, run analysis, use editor |

### Bundled Game Fixtures

| Fixture | Complexity | Purpose | Source |
|---------|-----------|---------|--------|
| MiniCap | 3 gen, 10 upg, 1 prestige | Quick demo, unit testing | `tests/fixtures/minicap.json` |
| MediumCap | 8 gen, 30 upg, 2 prestige | Full showcase, integration testing | `tests/fixtures/mediumcap.json` |

Both are copied to `server/games/` at build time (or symlinked in dev).

### Error Boundaries

- Frontend: React error boundaries per page. If analysis crashes, the play page still works.
- API: FastAPI exception handlers return structured JSON, never HTML tracebacks.
- Engine sessions: If a session's engine enters an invalid state, the session is terminated with a clear error message.

---

## Execution Order

### Phase 2 + 4 (parallel, ~12-15 tasks)

Build together since the frontend needs the API:

1. **Server scaffold** — FastAPI app, config, CORS, Makefile
2. **Game routes** — CRUD endpoints, file-based storage, bundled fixtures
3. **Analysis routes** — Run analysis, compare, report generation
4. **Engine routes** — Session manager, start/advance/purchase/prestige/auto-optimize
5. **API tests** — Full route coverage with TestClient
6. **Frontend scaffold** — Vite + React + TypeScript + Tailwind + Router
7. **API client** — Typed fetch wrappers, error handling
8. **Play Page: core** — Generator cards, resource display, buy/advance loop
9. **Play Page: prestige + upgrades** — Prestige panel, upgrade shop, achievements
10. **Play Page: auto-optimize** — Optimizer integration, timeline animation
11. **Analyze Page: controls + results** — Game selector, optimizer config, findings display
12. **Analyze Page: charts** — Plotly integration, production curves, cost distribution
13. **Analyze Page: compare** — Side-by-side free vs paid
14. **Polish** — Loading states, error handling, responsive layout, dark mode
15. **E2E tests** — Playwright tests for critical paths

### Phase 3 (~8-10 tasks)

After Phase 2 + 4 are stable:

1. **React Flow setup** — Canvas, custom node registration, edge types
2. **Node palette** — Drag-and-drop creation for all 16 node types
3. **Custom node components** — Visual representation for each type
4. **Custom edge components** — Solid (resource) vs dotted (state) edges
5. **Property panel** — Form-based editing with validation
6. **Import/export** — Save/load game definitions, auto-layout
7. **WebSocket endpoint** — Server-side WS for live analysis
8. **Live analysis panel** — Real-time validation + greedy analysis on edit
9. **JSON preview** — Live-updating raw JSON view
10. **Polish + testing** — Error boundaries, Playwright tests

---

## Non-Goals (Deferred)

- **Authentication / multi-user** — This is a local/demo tool, not a SaaS
- **Database** — JSON files on disk + in-memory sessions
- **Real-time multiplayer** — Single-user sessions
- **Mobile optimization** — Desktop-first, responsive but not mobile-native
- **Offline mode / PWA** — Requires server running
- **Custom themes** — Dark/light mode only
- **Game state persistence** — Sessions are ephemeral. Users can export game definitions but not save mid-game state.
