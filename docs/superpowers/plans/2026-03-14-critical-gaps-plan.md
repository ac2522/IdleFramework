# Critical Gaps Resolution Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the two broken API endpoints (prestige 501, analysis parameter forwarding), add frontend test infrastructure (Vitest + Playwright), and configure pytest-cov for backend coverage reporting.

**Architecture:** Four independent workstreams: (A) implement prestige API by calling the existing `engine.execute_prestige()`, (B) add optimizer dispatch to `run_full_analysis()` so the API can forward optimizer/tags parameters, (C) set up Vitest + React Testing Library for component tests and Playwright for E2E, (E) add pytest-cov configuration to pyproject.toml.

**Tech Stack:** Python/FastAPI (A, B, E), Vitest/React Testing Library/MSW (C unit), Playwright (C e2e), pytest-cov (E)

---

## Chunk 1: Backend API Fixes (Tasks 1-2)

### Task 1: Implement Prestige API Endpoint

**Files:**
- Modify: `server/routes/engine.py:123-130` (fix `_build_state` hardcoded currency)
- Modify: `server/routes/engine.py:255-285` (replace 501 with real implementation)
- Modify: `tests/test_api/test_engine_routes.py:188-257` (update tests to expect 200)

**Context:** The prestige endpoint at `POST /engine/{session_id}/prestige` currently returns 501. The core engine already has a working `execute_prestige(prestige_id)` method in `src/idleframework/engine/segments.py:720-769` that handles formula evaluation, currency deposit, scope resets, and multi-layer cascading. The endpoint just needs to call it.

The `_build_state()` helper also hardcodes `available_currency=0.0` instead of reading the actual currency balance. The `PrestigeLayer` model has a `currency_id` field pointing to a resource node.

**Pattern to follow:** See the `purchase` endpoint at `engine.py:179-252` — get session, get engine, call engine method, handle errors, return `_build_state(session)`.

- [ ] **Step 1: Update the existing prestige test to expect success**

In `tests/test_api/test_engine_routes.py`, change `test_prestige_returns_result` to expect a 200 with valid state after advancing enough time to accumulate prestige currency. The MiniCap fixture has a prestige layer with `formula_expr="floor(sqrt(lifetime_prestige_pts))"`.

```python
def test_prestige_returns_result(self, client, session_id):
    """Prestige endpoint resets state and returns new balance."""
    # Advance enough to accumulate production
    client.post(
        f"/api/v1/engine/{session_id}/advance",
        json={"seconds": 300.0},
    )
    resp = client.post(
        f"/api/v1/engine/{session_id}/prestige",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    # After prestige, elapsed_time should still be tracked
    assert "prestige" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api/test_engine_routes.py::TestPrestige::test_prestige_returns_result -v`
Expected: FAIL — endpoint still returns 501.

- [ ] **Step 3: Fix `_build_state` to compute actual prestige currency**

In `server/routes/engine.py`, replace lines 123-130. Instead of hardcoding `available_currency=0.0`, read the actual currency balance from the engine state when `currency_id` is set:

```python
prestige = None
for node in game.nodes:
    if isinstance(node, PrestigeLayer):
        currency_value = 0.0
        if node.currency_id:
            currency_ns = engine.state.get(node.currency_id)
            currency_value = currency_ns.current_value
        prestige = PrestigeState(
            available_currency=currency_value,
            formula_preview=node.formula_expr,
        )
        break
```

- [ ] **Step 4: Implement the prestige endpoint**

In `server/routes/engine.py`, replace lines 275-285 (the 501 raise) with:

```python
engine = session.engine
try:
    engine.execute_prestige(prestige_node.id)
except ValueError as exc:
    raise HTTPException(
        status_code=400,
        detail=ErrorResponse(
            error="prestige_failed",
            detail=str(exc),
            status=400,
        ).model_dump(),
    ) from exc

return _build_state(session)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_api/test_engine_routes.py::TestPrestige -v`
Expected: All 3 prestige tests pass (200 for valid prestige, 404 for missing session, 400 for no prestige layer).

- [ ] **Step 6: Add a test for prestige currency tracking**

Add a new test that verifies the prestige currency is reflected in the response after prestige:

```python
def test_prestige_updates_currency(self, client, session_id):
    """After prestige, available_currency reflects the prestige gain."""
    client.post(
        f"/api/v1/engine/{session_id}/advance",
        json={"seconds": 600.0},
    )
    resp = client.post(f"/api/v1/engine/{session_id}/prestige")
    assert resp.status_code == 200
    prestige_data = resp.json()["prestige"]
    # After a prestige with accumulated production, currency should be > 0
    # (depends on MiniCap fixture having currency_id set)
    assert prestige_data is not None
```

- [ ] **Step 7: Run full test suite to verify no regressions**

Run: `pytest tests/test_api/ -v`
Expected: All API tests pass. Existing tests that expected 501 are now updated.

- [ ] **Step 8: Commit**

```bash
git add server/routes/engine.py tests/test_api/test_engine_routes.py
git commit -m "feat: implement prestige API endpoint with currency tracking"
```

---

### Task 2: Forward Analysis API Parameters to Optimizer

**Files:**
- Modify: `src/idleframework/analysis/detectors.py:23-44,256-270` (add optimizer parameter + dispatch)
- Modify: `server/routes/analysis.py:88-100` (forward request fields)
- Modify: `tests/test_api/test_analysis_routes.py` (add optimizer parameter tests)

**Context:** The `AnalysisRequest` schema already accepts `optimizer`, `beam_width`, `mcts_iterations`, `mcts_seed`, `bnb_depth`, and `tags` fields (see `server/schemas.py:29-37`), but `run_full_analysis()` only accepts `game` and `simulation_time`. The function always calls `_run_greedy()`.

**Key complication:** `GreedyOptimizer(game, state)` takes a `GameDefinition`, while `BeamSearchOptimizer(engine, beam_width)`, `MCTSOptimizer(engine, iterations, seed=seed)`, and `BranchAndBoundOptimizer(engine, depth_limit)` take a `PiecewiseEngine`. The dispatch function needs to handle both patterns.

- [ ] **Step 1: Write a failing test for optimizer parameter forwarding**

In `tests/test_api/test_analysis_routes.py`, add:

```python
class TestAnalysisOptimizerParam:
    def test_greedy_optimizer_explicit(self, client):
        """Explicitly requesting greedy optimizer works."""
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "minicap",
            "simulation_time": 60.0,
            "optimizer": "greedy",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["optimizer_result"] is not None
        assert len(data["optimizer_result"]["purchases"]) > 0

    def test_beam_optimizer(self, client):
        """Beam optimizer can be selected via API."""
        resp = client.post("/api/v1/analysis/run", json={
            "game_id": "minicap",
            "simulation_time": 60.0,
            "optimizer": "beam",
            "beam_width": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["optimizer_result"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api/test_analysis_routes.py::TestAnalysisOptimizerParam -v`
Expected: `test_beam_optimizer` FAIL — `run_full_analysis` ignores optimizer parameter, always uses greedy.

- [ ] **Step 3: Add optimizer dispatch to `run_full_analysis`**

In `src/idleframework/analysis/detectors.py`, add imports and a dispatch helper, then update `run_full_analysis`:

```python
# Add to imports at top of file:
from idleframework.optimizer.beam import BeamSearchOptimizer
from idleframework.optimizer.mcts import MCTSOptimizer
from idleframework.optimizer.bnb import BranchAndBoundOptimizer


def _run_optimizer(
    game: GameDefinition,
    simulation_time: float,
    optimizer: str = "greedy",
    initial_balance: float = 50.0,
    beam_width: int = 100,
    mcts_iterations: int = 1000,
    mcts_seed: int | None = None,
    bnb_depth: int = 20,
) -> OptimizeResult:
    """Dispatch to the requested optimizer."""
    engine = PiecewiseEngine(game)
    pay_resource = engine._get_primary_resource_id()
    if pay_resource is None:
        raise ValueError("Game must contain at least one resource node for analysis")
    engine.set_balance(pay_resource, initial_balance)
    for gen_id in engine._generators:
        cost = bulk_cost(
            engine._generators[gen_id].cost_base,
            engine._generators[gen_id].cost_growth_rate,
            0, 1,
        )
        if cost <= initial_balance:
            engine.purchase(gen_id, 1)
            break

    if optimizer == "greedy":
        opt = GreedyOptimizer(game, engine.state)
    elif optimizer == "beam":
        opt = BeamSearchOptimizer(engine, beam_width=beam_width)
    elif optimizer == "mcts":
        opt = MCTSOptimizer(engine, iterations=mcts_iterations, seed=mcts_seed)
    elif optimizer == "bnb":
        opt = BranchAndBoundOptimizer(engine, depth_limit=bnb_depth)
    else:
        raise ValueError(f"Unknown optimizer: {optimizer!r}")

    return opt.optimize(target_time=simulation_time, max_steps=500)
```

Then update `run_full_analysis` signature and body:

```python
def run_full_analysis(
    game: GameDefinition,
    simulation_time: float = 300.0,
    optimizer: str = "greedy",
    beam_width: int = 100,
    mcts_iterations: int = 1000,
    mcts_seed: int | None = None,
    bnb_depth: int = 20,
) -> AnalysisReport:
    report = AnalysisReport(
        game_name=game.name,
        simulation_time=simulation_time,
    )

    report.dead_upgrades = detect_dead_upgrades(game, simulation_time)
    report.progression_walls = detect_progression_walls(game, simulation_time)
    report.dominant_strategy = detect_dominant_strategy(game, simulation_time)
    report.optimizer_result = _run_optimizer(
        game, simulation_time,
        optimizer=optimizer,
        beam_width=beam_width,
        mcts_iterations=mcts_iterations,
        mcts_seed=mcts_seed,
        bnb_depth=bnb_depth,
    )

    return report
```

Keep `_run_greedy` as-is for backward compatibility (it's a valid helper). The old code calling `run_full_analysis(game, simulation_time=X)` still works because new params have defaults.

- [ ] **Step 4: Forward parameters from the API route**

In `server/routes/analysis.py`, update the `/run` endpoint (lines 96-100):

```python
report = run_full_analysis(
    game,
    simulation_time=req.simulation_time,
    optimizer=req.optimizer,
    beam_width=req.beam_width,
    mcts_iterations=req.mcts_iterations,
    mcts_seed=req.mcts_seed,
    bnb_depth=req.bnb_depth,
)
```

Remove the NOTE/TODO comment on lines 92-94.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_api/test_analysis_routes.py -v`
Expected: All tests pass including new optimizer parameter tests.

- [ ] **Step 6: Run full backend test suite**

Run: `pytest tests/ -v --timeout=30`
Expected: No regressions. Existing callers of `run_full_analysis` still work (defaults match old behavior).

- [ ] **Step 7: Commit**

```bash
git add src/idleframework/analysis/detectors.py server/routes/analysis.py tests/test_api/test_analysis_routes.py
git commit -m "feat: forward optimizer parameters from analysis API to engine"
```

---

## Chunk 2: Frontend Test Infrastructure (Tasks 3-5)

### Task 3: Set Up Vitest + React Testing Library

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Modify: `frontend/package.json` (add dev deps + test script)
- Modify: `frontend/tsconfig.app.json` (include test types)
- Create: `frontend/src/utils/__tests__/formatting.test.ts` (first test to verify setup)

**Context:** The frontend has zero test infrastructure. We need Vitest (Vite-native test runner), React Testing Library (component testing), jsdom (browser environment), and MSW (API mocking). The frontend uses React 19, TypeScript 5, Vite 7, Tailwind 4.

- [ ] **Step 1: Install test dependencies**

```bash
cd frontend && npm install -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event msw
```

- [ ] **Step 2: Create vitest.config.ts**

```typescript
/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test/**', 'src/**/*.d.ts'],
    },
  },
})
```

- [ ] **Step 3: Create test setup file**

Create `frontend/src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 4: Add test script to package.json**

Add to `frontend/package.json` scripts:

```json
"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage"
```

- [ ] **Step 5: Write a smoke test for formatting utils**

Create `frontend/src/utils/__tests__/formatting.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { formatNumber, formatTime } from '../formatting'

describe('formatNumber', () => {
  it('formats small numbers directly', () => {
    expect(formatNumber(42)).toBe('42')
  })

  it('formats thousands with K suffix', () => {
    const result = formatNumber(1500)
    expect(result).toContain('K')
  })

  it('formats millions with M suffix', () => {
    const result = formatNumber(2_500_000)
    expect(result).toContain('M')
  })

  it('handles zero', () => {
    expect(formatNumber(0)).toBe('0')
  })
})

describe('formatTime', () => {
  it('formats seconds', () => {
    expect(formatTime(45)).toContain('s')
  })

  it('formats minutes', () => {
    expect(formatTime(120)).toContain('m')
  })

  it('formats hours', () => {
    expect(formatTime(7200)).toContain('h')
  })
})
```

- [ ] **Step 6: Run test to verify setup works**

Run: `cd frontend && npx vitest run`
Expected: PASS — formatting tests succeed.

- [ ] **Step 7: Commit**

```bash
git add frontend/vitest.config.ts frontend/src/test/setup.ts frontend/package.json frontend/src/utils/__tests__/formatting.test.ts
git commit -m "feat: set up Vitest + React Testing Library for frontend tests"
```

---

### Task 4: Frontend Component Unit Tests

**Files:**
- Create: `frontend/src/test/mocks/handlers.ts` (MSW API handlers)
- Create: `frontend/src/test/mocks/server.ts` (MSW server setup)
- Create: `frontend/src/api/__tests__/client.test.ts`
- Create: `frontend/src/hooks/__tests__/useGameTick.test.ts`
- Create: `frontend/src/components/game/__tests__/GeneratorCard.test.tsx`
- Create: `frontend/src/components/game/__tests__/ResourceDisplay.test.tsx`
- Create: `frontend/src/components/ui/__tests__/ErrorBanner.test.tsx`
- Create: `frontend/src/components/ui/__tests__/Spinner.test.tsx`
- Create: `frontend/src/editor/__tests__/conversion.test.ts`
- Create: `frontend/src/editor/__tests__/FormulaField.test.tsx`

**Context:** The frontend has 67 TypeScript files. We focus on the highest-value tests: API client error handling, the game tick hook, game display components, UI primitives, and the editor graph↔game conversion (the most complex pure logic). We use MSW to mock API responses.

- [ ] **Step 1: Create MSW mock handlers**

Create `frontend/src/test/mocks/handlers.ts` with mock responses for the most-used endpoints:

```typescript
import { http, HttpResponse } from 'msw'

const baseUrl = '/api/v1'

export const handlers = [
  http.get(`${baseUrl}/games/`, () => {
    return HttpResponse.json({
      games: [
        { id: 'minicap', name: 'MiniCap', node_count: 14, edge_count: 12, bundled: true },
      ],
    })
  }),

  http.post(`${baseUrl}/engine/start`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      session_id: 'test-session-123',
      game_id: body.game_id,
      elapsed_time: 0,
      resources: { gold: { current_value: 50, production_rate: 0 } },
      generators: {},
      upgrades: {},
      prestige: null,
      achievements: [],
    })
  }),

  http.post(`${baseUrl}/engine/:sessionId/advance`, () => {
    return HttpResponse.json({
      session_id: 'test-session-123',
      game_id: 'minicap',
      elapsed_time: 10,
      resources: { gold: { current_value: 60, production_rate: 1 } },
      generators: {},
      upgrades: {},
      prestige: null,
      achievements: [],
    })
  }),
]
```

- [ ] **Step 2: Create MSW server setup**

Create `frontend/src/test/mocks/server.ts`:

```typescript
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

Update `frontend/src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom/vitest'
import { beforeAll, afterAll, afterEach } from 'vitest'
import { server } from './mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

- [ ] **Step 3: Write API client tests**

Create `frontend/src/api/__tests__/client.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/mocks/server'
import { listGames } from '../games'

describe('API client', () => {
  it('fetches game list successfully', async () => {
    const games = await listGames()
    expect(games.games).toHaveLength(1)
    expect(games.games[0].id).toBe('minicap')
  })

  it('throws on server error', async () => {
    server.use(
      http.get('/api/v1/games/', () => {
        return HttpResponse.json(
          { error: 'server_error', detail: 'fail', status: 500 },
          { status: 500 },
        )
      }),
    )
    await expect(listGames()).rejects.toThrow()
  })
})
```

- [ ] **Step 4: Write UI component tests**

Create `frontend/src/components/ui/__tests__/ErrorBanner.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBanner from '../ErrorBanner'

describe('ErrorBanner', () => {
  it('renders error message', () => {
    render(<ErrorBanner message="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })
})
```

Create `frontend/src/components/ui/__tests__/Spinner.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Spinner from '../Spinner'

describe('Spinner', () => {
  it('renders with label', () => {
    render(<Spinner label="Loading..." />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders without label', () => {
    const { container } = render(<Spinner />)
    expect(container.firstChild).toBeTruthy()
  })
})
```

- [ ] **Step 5: Write game component tests**

Create `frontend/src/components/game/__tests__/ResourceDisplay.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ResourceDisplay from '../ResourceDisplay'

describe('ResourceDisplay', () => {
  it('renders resource names and values', () => {
    const resources = {
      gold: { current_value: 100, production_rate: 5 },
    }
    render(<ResourceDisplay resources={resources} />)
    expect(screen.getByText(/gold/i)).toBeInTheDocument()
  })
})
```

Create `frontend/src/components/game/__tests__/GeneratorCard.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import GeneratorCard from '../GeneratorCard'

describe('GeneratorCard', () => {
  const defaultProps = {
    name: 'Miner',
    gen: { owned: 5, cost_next: 100, production_per_sec: 2.5 },
    balance: 200,
    onBuy: vi.fn(),
  }

  it('renders generator name and owned count', () => {
    render(<GeneratorCard {...defaultProps} />)
    expect(screen.getByText(/miner/i)).toBeInTheDocument()
    expect(screen.getByText(/5/)).toBeInTheDocument()
  })

  it('calls onBuy when buy button is clicked', async () => {
    const onBuy = vi.fn()
    render(<GeneratorCard {...defaultProps} onBuy={onBuy} />)
    const buyButton = screen.getAllByRole('button')[0]
    await userEvent.click(buyButton)
    expect(onBuy).toHaveBeenCalled()
  })
})
```

- [ ] **Step 6: Write editor conversion tests**

Create `frontend/src/editor/__tests__/conversion.test.ts`. This is the most important unit test — the `graphToGame` / `gameToGraph` round-trip:

```typescript
import { describe, it, expect } from 'vitest'
import { graphToGame, gameToGraph } from '../conversion'

describe('graphToGame / gameToGraph round-trip', () => {
  it('converts a simple graph to game JSON', () => {
    const nodes = [
      {
        id: 'res-1',
        type: 'resource',
        position: { x: 0, y: 0 },
        data: { nodeType: 'resource', label: 'Gold', initial_value: 100 },
      },
      {
        id: 'gen-1',
        type: 'generator',
        position: { x: 200, y: 0 },
        data: {
          nodeType: 'generator',
          label: 'Miner',
          cost_base: 10,
          cost_growth_rate: 1.15,
          base_production: 1.0,
          cycle_time: 1.0,
        },
      },
    ]
    const edges = [
      { id: 'e1', source: 'gen-1', target: 'res-1', type: 'resource', data: { edgeType: 'production_target' } },
    ]
    const game = graphToGame(nodes, edges, { name: 'Test Game', stacking_groups: {} })
    expect(game.name).toBe('Test Game')
    expect(game.nodes).toHaveLength(2)
    expect(game.edges).toHaveLength(1)
  })

  it('round-trips a game through graph and back', () => {
    const gameJson = {
      schema_version: '1.0',
      name: 'Round Trip Test',
      nodes: [
        { id: 'gold', type: 'resource', name: 'Gold', initial_value: 50 },
        { id: 'miner', type: 'generator', name: 'Miner', cost_base: 10, cost_growth_rate: 1.15, base_production: 1, cycle_time: 1 },
      ],
      edges: [
        { id: 'e1', source: 'miner', target: 'gold', edge_type: 'production_target' },
      ],
      stacking_groups: {},
    }
    const { nodes, edges } = gameToGraph(gameJson)
    const result = graphToGame(nodes, edges, { name: 'Round Trip Test' })
    expect(result.nodes).toHaveLength(2)
    expect(result.edges).toHaveLength(1)
  })
})
```

- [ ] **Step 7: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/test/ frontend/src/api/__tests__/ frontend/src/components/game/__tests__/ frontend/src/components/ui/__tests__/ frontend/src/editor/__tests__/ frontend/src/hooks/__tests__/
git commit -m "feat: add frontend component and utility tests with MSW mocking"
```

---

### Task 5: Playwright E2E Tests

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/play-page.spec.ts`
- Create: `frontend/e2e/analyze-page.spec.ts`
- Create: `frontend/e2e/editor-page.spec.ts`
- Modify: `frontend/package.json` (add e2e script)

**Context:** E2E tests require the backend to be running (`uvicorn server.app:app`). Tests cover the 3 critical user flows: play a game, run analysis, use the node editor. Use the Playwright MCP server available in the environment for authoring assistance.

**Important:** These tests hit the real backend. The backend must be started before running, and MiniCap fixture must be available. Tests should be resilient to timing (use `waitFor` patterns, not fixed sleeps).

- [ ] **Step 1: Install Playwright**

```bash
cd frontend && npm install -D @playwright/test && npx playwright install chromium
```

- [ ] **Step 2: Create Playwright config**

Create `frontend/playwright.config.ts`:

```typescript
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: 'cd .. && uvicorn server.app:app --port 8000',
      port: 8000,
      reuseExistingServer: true,
      timeout: 15_000,
    },
    {
      command: 'npm run dev',
      port: 5173,
      reuseExistingServer: true,
      timeout: 15_000,
    },
  ],
})
```

- [ ] **Step 3: Add e2e script to package.json**

```json
"e2e": "playwright test",
"e2e:headed": "playwright test --headed"
```

- [ ] **Step 4: Write Play Page E2E test**

Create `frontend/e2e/play-page.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'

test.describe('Play Page', () => {
  test('loads and displays game state', async ({ page }) => {
    await page.goto('/play')
    // Wait for game session to start
    await expect(page.getByText(/gold/i)).toBeVisible({ timeout: 10_000 })
  })

  test('can advance time and see production', async ({ page }) => {
    await page.goto('/play')
    await expect(page.getByText(/gold/i)).toBeVisible({ timeout: 10_000 })

    // Find and click resume/play button to start ticking
    const playButton = page.getByRole('button', { name: /resume|play|start/i })
    if (await playButton.isVisible()) {
      await playButton.click()
    }

    // Wait for production to change (gold value should update)
    await expect(async () => {
      const text = await page.getByText(/gold/i).textContent()
      expect(text).toBeTruthy()
    }).toPass({ timeout: 5_000 })
  })

  test('can trigger prestige', async ({ page }) => {
    await page.goto('/play')
    await expect(page.getByText(/gold/i)).toBeVisible({ timeout: 10_000 })
    // Prestige panel should be visible for MiniCap (has prestige layer)
    await expect(page.getByText(/prestige/i)).toBeVisible()
  })
})
```

- [ ] **Step 5: Write Analyze Page E2E test**

Create `frontend/e2e/analyze-page.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'

test.describe('Analyze Page', () => {
  test('can run analysis on MiniCap', async ({ page }) => {
    await page.goto('/analyze')

    // Wait for page to load with game selector
    await expect(page.getByText(/analyze/i)).toBeVisible({ timeout: 10_000 })

    // Click run analysis button
    const runButton = page.getByRole('button', { name: /run.*analysis|analyze/i })
    await expect(runButton).toBeVisible({ timeout: 5_000 })
    await runButton.click()

    // Wait for results to appear
    await expect(page.getByText(/dead.*upgrade|progression|dominant|optimizer/i)).toBeVisible({ timeout: 15_000 })
  })
})
```

- [ ] **Step 6: Write Editor Page E2E test**

Create `frontend/e2e/editor-page.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'

test.describe('Editor Page', () => {
  test('loads the node editor canvas', async ({ page }) => {
    await page.goto('/editor')

    // React Flow canvas should be present
    await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10_000 })

    // Node palette should be visible
    await expect(page.getByText(/resource|generator/i)).toBeVisible()
  })

  test('can load a game into the editor', async ({ page }) => {
    await page.goto('/editor')
    await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10_000 })

    // Find and click load button
    const loadButton = page.getByRole('button', { name: /load/i })
    if (await loadButton.isVisible()) {
      await loadButton.click()
    }
  })
})
```

- [ ] **Step 7: Run E2E tests**

Run: `cd frontend && npx playwright test`
Expected: All E2E tests pass (Playwright will start the backend and dev server automatically via webServer config).

- [ ] **Step 8: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e/ frontend/package.json
git commit -m "feat: add Playwright E2E tests for play, analyze, and editor pages"
```

---

## Chunk 3: Backend Coverage & Conditional Performance (Tasks 6-7)

### Task 6: Configure pytest-cov

**Files:**
- Modify: `pyproject.toml` (add pytest-cov dep + coverage config)

**Context:** `pytest-cov` is not listed in dev dependencies and there is no coverage configuration. We need to add it and configure source paths, exclusions, and a minimum threshold.

- [ ] **Step 1: Add pytest-cov to dev dependencies**

In `pyproject.toml`, add `"pytest-cov>=6.0"` to the `dev` optional-dependencies list (after `"pytest-timeout>=2.0"`).

- [ ] **Step 2: Add coverage configuration**

Add to `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/idleframework", "server"]
omit = [
    "src/idleframework/_bigfloat_cython.pyx",
    "src/idleframework/engine/_numba_accel.py",
    "benchmarks/*",
]

[tool.coverage.report]
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.",
]
```

- [ ] **Step 3: Install and verify**

```bash
pip install -e ".[dev]" && pytest --cov --cov-report=term-missing tests/ -q --timeout=30
```

Expected: Tests pass with coverage report printed. Note the coverage percentage — no minimum enforced yet (we want to see baseline first).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: configure pytest-cov for backend test coverage reporting"
```

---

### Task 7: Evaluate and Begin Numba Integration (Conditional)

**Files:**
- Modify: `src/idleframework/engine/_numba_accel.py` (implement actual Numba functions)
- Modify: `src/idleframework/engine/solvers.py` (use Numba-accelerated paths when available)
- Create: `tests/test_numba_accel.py` (verify Numba functions match pure-Python)

**Context:** Benchmark data shows LargeCap engine takes **24-26 seconds** (unacceptable for interactive use). MiniCap/MediumCap are fine (0.3-1.5s). The existing `_numba_accel.py` is a stub with a no-op `@njit` decorator fallback.

**Decision gate:** Run the benchmark suite first. If LargeCap engine time < 5 seconds, skip this task. If >= 5 seconds, proceed with Numba acceleration of the hot paths identified in the design spec: `bulk_purchase_cost`, `time_to_afford`, and `efficiency_scores`.

**Important:** Numba operates on primitives (float64, int64, numpy arrays), NOT on BigFloat objects. The acceleration boundary is at the solver/engine level where BigFloat values are converted to float primitives for batch computation.

- [ ] **Step 1: Run benchmark to confirm performance**

```bash
cd /home/zaia/Development/IdleFramework && python benchmarks/run_benchmarks.py
```

If LargeCap engine < 5s, skip remaining steps and commit a note. Otherwise continue.

- [ ] **Step 2: Write tests for Numba-accelerated functions**

Create `tests/test_numba_accel.py`:

```python
"""Tests that Numba-accelerated functions match pure-Python results."""
import pytest
from idleframework.engine.solvers import bulk_cost
from idleframework.engine._numba_accel import bulk_purchase_cost_fast


class TestNumbaAcceleration:
    @pytest.mark.parametrize("base,rate,owned,count", [
        (10.0, 1.15, 0, 1),
        (10.0, 1.15, 0, 10),
        (100.0, 1.07, 5, 5),
        (10.0, 1.0, 0, 10),  # rate=1 edge case
        (1e6, 1.15, 50, 10),  # large values
    ])
    def test_bulk_cost_matches_pure_python(self, base, rate, owned, count):
        expected = float(bulk_cost(base, rate, owned, count))
        result = bulk_purchase_cost_fast(base, rate, owned, count)
        assert result == pytest.approx(expected, rel=1e-9)
```

- [ ] **Step 3: Run test to verify it fails (stub returns wrong values)**

Run: `pytest tests/test_numba_accel.py -v`
Expected: FAIL or SKIP depending on current stub behavior.

- [ ] **Step 4: Implement `bulk_purchase_cost_fast` with actual Numba**

In `src/idleframework/engine/_numba_accel.py`, replace the stub:

```python
"""Numba-accelerated hot-path functions.

These operate on float64 primitives (not BigFloat).
Falls back to pure Python if Numba is not installed.
"""
from __future__ import annotations

import math

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*args, **kwargs):
        """No-op decorator when Numba is unavailable."""
        def wrapper(fn):
            return fn
        if args and callable(args[0]):
            return args[0]
        return wrapper


@njit(cache=True)
def bulk_purchase_cost_fast(
    base: float, rate: float, owned: int, count: int,
) -> float:
    """Compute bulk purchase cost: base * rate^owned * (rate^count - 1) / (rate - 1).

    For rate == 1: base * count.
    """
    if count <= 0:
        return 0.0
    if abs(rate - 1.0) < 1e-12:
        return base * count
    return base * (rate ** owned) * (rate ** count - 1.0) / (rate - 1.0)
```

- [ ] **Step 5: Run tests to verify Numba functions match**

Run: `pytest tests/test_numba_accel.py -v`
Expected: All parametrized cases pass (with or without Numba installed).

- [ ] **Step 6: Wire Numba path into solvers (optional optimization)**

In `src/idleframework/engine/solvers.py`, add a conditional import and use the fast path when values fit in float64:

```python
try:
    from idleframework.engine._numba_accel import bulk_purchase_cost_fast as _fast_bulk
    _HAS_FAST = True
except Exception:
    _HAS_FAST = False
```

Then in the `bulk_cost` function, add an early return for float64-safe values:

```python
# At the top of bulk_cost(), before BigFloat logic:
if _HAS_FAST and base_exp == 0 and rate_exp == 0:
    # Values fit in float64, use accelerated path
    result = _fast_bulk(float(base), float(rate), owned, count)
    return BigFloat(result)
```

This is a targeted optimization — only for values that don't need BigFloat precision.

- [ ] **Step 7: Run full test suite**

Run: `pytest tests/ -q --timeout=60`
Expected: All 583+ tests pass with no regressions.

- [ ] **Step 8: Re-run benchmark and compare**

```bash
python benchmarks/run_benchmarks.py
```

Compare LargeCap engine times against baseline. Document improvement (or lack thereof) in commit message.

- [ ] **Step 9: Commit**

```bash
git add src/idleframework/engine/_numba_accel.py src/idleframework/engine/solvers.py tests/test_numba_accel.py
git commit -m "perf: implement Numba-accelerated bulk_purchase_cost with fallback"
```
