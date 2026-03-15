# E2E Testing, Game Fixtures & UI Testing Design

**Date:** 2026-03-15
**Status:** Draft
**Approach:** Parallel Layers (Foundation → Backend E2E → UI Roundtrip → UI Comprehensive)

## Problem

- Only MiniCap has E2E test coverage. MediumCap/LargeCap/FullMechanics have minimal or broken coverage.
- No tests verify Phase 5 mechanics (drains, buffs, synergies, tickspeed, autobuyers) in a full pipeline context.
- Frontend has only 4 Vitest unit tests (conversion roundtrip). No Playwright E2E tests. No coverage of Play/Editor/Analyze pages.
- No proof that games built in the editor actually work when played or analyzed.
- No diverse game fixtures to stress-test the engine across varied idle game designs.

## Existing Infrastructure

The following tooling is already configured and should be extended, not replaced:

- **Vitest** — `frontend/vitest.config.ts` with jsdom, globals, v8 coverage. Setup file at `src/test/setup.ts`.
- **MSW** — `msw` v2 installed. Mock handlers at `src/test/mocks/handlers.ts` (games list, engine start, advance). MSW server configured in setup.ts.
- **Playwright** — `frontend/playwright.config.ts` with dual webServer (Vite on 5173, FastAPI on 8000), Chromium, retries: 1, screenshots on failure.
- **Existing conversion tests** — `frontend/src/editor/__tests__/conversion.test.ts` (4 tests: graphToGame basic, metadata, gameToGraph, roundtrip).
- **FullMechanics fixture** — `tests/fixtures/fullmechanics.py` exercises all Phase 5 mechanics (drain, buff, synergy, tickspeed, autobuyer, capacity, prestige). 6 existing tests.
- **597 existing backend tests** (unit, integration, API, E2E).

## Solution Overview

Four phases, each building on the last:

1. **Foundation** — Create 9 new game fixtures, extend MSW handlers
2. **Backend E2E** — ~70 new Python E2E tests covering all fixtures and mechanics
3. **UI Roundtrip** — ~15 Playwright live-backend tests proving editor → play → analyze works
4. **UI Comprehensive** — ~40 new Vitest unit tests + ~35 Playwright mocked tests for full UI coverage

## Phase 1: Test Game Fixtures

### Relationship to Existing Fixtures

- **MiniCap** (3 gen, 10 upg, 1 prestige) — keeps its existing E2E tests, serves as baseline
- **MediumCap** (8 gen, 30 upg, 2 prestige) — existing but has known optimizer bugs. Cross-fixture tests will exercise it.
- **LargeCap** (procedural, 10-100 gen) — stress test only, not used for UI tests
- **FullMechanics** (all Phase 5 mechanics) — the new minimal fixtures decompose its mechanics into isolated tests. FullMechanics remains as the "all mechanics at once" integration fixture.

### Minimal Mechanic Fixtures (6 games, 3-8 nodes each)

Each isolates a specific mechanic combination. Where FullMechanics tests all mechanics together, these test mechanics in isolation to pinpoint failures:

| Fixture | File | Mechanics Tested | Key Assertions |
|---------|------|-----------------|----------------|
| DrainBuff | `drainbuff.json` | Drain + Buff + Resource capacity | Drain reduces resource, buff multiplies production, capacity caps |
| SynergyTickspeed | `synergy_tickspeed.json` | Synergy + Tickspeed + 2 generators | Synergy bonus scales with source, tickspeed multiplies all rates |
| MultiPrestige | `multi_prestige.json` | 2 prestige layers + generators | Layer 1 resets for currency, layer 2 resets layer 1, currencies accumulate |
| AutobuyerChain | `autobuyer_chain.json` | Autobuyer + 3 generators + upgrades | Autobuyer purchases in priority order, respects thresholds |
| ConverterEconomy | `converter_economy.json` | Converter + 2 resources + drain | Input consumed, output produced at recipe ratio, drain creates pressure |
| GateUnlock | `gate_unlock.json` | UnlockGate + Achievement + ChoiceGroup | Gate blocks until condition met, achievement fires, choice is exclusive |

### Archetype Games (3 games, 10-30 nodes each)

Model real idle game patterns:

| Archetype | File | Modeled After | Nodes | Key Features |
|-----------|------|---------------|-------|--------------|
| AdCapClone | `adcap_clone.json` | Adventure Capitalist | ~28 | 8 generators, 20 upgrades, 1 prestige. Generator chains (t^n/n!), x3/x3_all upgrades, angel investors. |
| PrestigeTree | `prestige_tree.json` | Prestige Tree | ~18 | 5 generators, 10 upgrades, 3 prestige layers. Deep prestige chains, layer-specific currencies, cross-layer synergies. |
| CraftingIdle | `crafting_idle.json` | Idle Miner / crafting hybrids | ~15 | 3 resources, 4 generators, 2 converters, drains, buffs, autobuyer. Multi-resource economy, conversion chains, timed buffs. |

### Fixture Storage & Sync

JSON fixtures live in a **single canonical location**: `tests/fixtures/`. The `server/games/` directory loads from there via symlinks or a copy step in the build/test setup. This avoids duplicate files drifting out of sync.

Implementation: `conftest.py` fixture that copies `tests/fixtures/*.json` to a temp `server/games/` directory for API tests, or `server/app.py` startup loads from both directories.

### Test Checkpoint Data

Expected simulation values are stored in **separate companion files** (`tests/fixtures/checkpoints/<fixture>_checkpoints.json`), not embedded in game definitions. This keeps game JSON clean and engine-agnostic. Example:

```json
{
  "drainbuff": {
    "t=10": { "gold": { "min": 80, "max": 120 } },
    "t=60": { "gold": { "min": 400, "max": 600 } }
  }
}
```

### Tolerance Strategy

All simulation checkpoint assertions use **relative tolerance of 5%** (`pytest.approx(expected, rel=0.05)`) for backend tests. This accounts for floating-point accumulation over time. Individual fixtures may override with tighter tolerances where analytical solutions are exact.

## Phase 2: Backend E2E Test Expansion

### Per-Fixture Pipeline Tests (`tests/test_e2e_<fixture>.py`)

Each fixture gets the same test pattern:

1. **Load & validate** — Game definition loads, Pydantic validates, graph is acyclic
2. **Simulate to checkpoints** — `engine.advance_to(t)` at key time points, assert resource values within tolerance (see checkpoint files)
3. **Purchase sequence** — Buy specific generators/upgrades, verify state changes
4. **Mechanic-specific assertions** — Whatever the fixture is designed to test
5. **Optimizer produces valid strategy** — Greedy optimizer returns a purchase sequence that doesn't violate constraints
6. **Prestige cycle** (where applicable) — Execute prestige, verify reset + currency grant + production boost

### Cross-Fixture Tests (`tests/test_e2e_cross.py`)

- All 9 new fixtures + existing MiniCap/MediumCap/FullMechanics load and validate without errors
- All fixtures simulate 60s without exceptions
- Greedy optimizer runs on all without crashing
- Analysis engine finds dead upgrades / walls where expected (e.g., LargeCap's intentional dead upgrade)

### Estimated Count

~60-80 new backend E2E tests.

## Phase 3: UI Roundtrip Tests (Playwright, Live Backend)

### Existing Playwright Config

The existing `frontend/playwright.config.ts` already configures dual webServer (Vite + FastAPI), Chromium, retries, and screenshots. No config changes needed — just add test files.

### Roundtrip Strategy: Upload, Not Drag-and-Drop

Building a 30-node game via drag-and-drop is brittle and slow. Instead, roundtrip tests use the **Upload JSON** workflow:

1. **Upload in Editor** — Navigate to `/editor`, upload archetype JSON via file input
2. **Verify graph renders** — Correct number of nodes/edges appear on canvas
3. **Edit a property** — Select a node, change a value in PropertyPanel, verify JsonPreview updates
4. **Validate** — Check ValidationBar shows 0 errors
5. **Save to server** — Click "Save to Server", verify success
6. **Load in Play** — Navigate to `/play`, select the game from dropdown, verify it loads
7. **Simulate** — Click resume, wait for ticks, verify resource values increase
8. **Purchase** — Buy a generator/upgrade, verify state updates
9. **Analyze** — Navigate to `/analyze`, select same game, run analysis, verify results appear

One dedicated drag-and-drop test verifies that mechanic works (drag 1 generator + 1 resource, connect, validate).

### Fixture Shortcut Tests

For the 6 minimal fixtures:

1. **Upload JSON** in editor → verify graph renders with correct node count
2. **Download JSON** → verify output matches input (roundtrip conversion)
3. **Load in Play** via game selector → verify simulation produces expected resource changes

### Test Isolation

Each Playwright test gets a clean server state:
- `beforeEach`: POST to a test-only `/api/v1/games/` to seed the fixture, record created game ID
- `afterEach`: DELETE the created game via API to clean up
- Playwright's `webServer` config uses `reuseExistingServer: true` — tests share one server instance but clean up their own data

### Flaky Test Mitigation

- Use `expect(locator).toPass({ timeout: 10_000 })` for assertions that depend on simulation ticks
- Playwright config already has `retries: 1` for transient failures
- Upload Playwright trace files as CI artifacts on failure (`trace: 'retain-on-failure'` in config)
- Simulation-dependent tests advance time via API calls where possible (deterministic) rather than waiting for real-time ticks

### Estimated Count

~15 roundtrip/fixture tests.

## Phase 4: Comprehensive UI Tests

### Vitest Unit Tests (`frontend/src/**/*.test.ts`)

Fast, no browser. MSW already configured in `src/test/setup.ts`.

**Conversion functions** (extend `editor/__tests__/conversion.test.ts`, ~10 new tests):
- Existing 4 tests cover basic graphToGame, gameToGraph, roundtrip, metadata
- Add: each of the 21 node types converts correctly (parametrized)
- Add: edge type detection for all state edge subtypes
- Add: edge cases (empty graph, disconnected nodes, duplicate IDs)

**Hooks** (`hooks/*.test.ts`, ~15 tests):
- `useGameSession` — start/advance/purchase/prestige state transitions
- `useGameTick` — ticks at correct interval, pauses, speed multiplier
- `useAutoOptimize` — calls API, returns purchase timeline

**ValidationBar logic** (~15 tests):
- ValidationBar contains inline validation logic (no separate `validation.ts` module exists). Tests will render the ValidationBar component with various graph states and assert error/warning output.
- Duplicate IDs caught
- Missing names caught
- Invalid formula syntax caught
- Generators without resources caught
- Valid graphs pass

**MSW handler expansion**: Add handlers to `src/test/mocks/handlers.ts` for analysis, prestige, purchase, auto-optimize, and game CRUD endpoints.

### Playwright Mocked Tests (`frontend/e2e/ui/`)

Browser tests with `page.route()` API interception (Playwright-native, simpler than MSW in browser context):

**Editor page** (`editor.spec.ts`, ~15 tests):
- All 21 concrete node types render when placed on canvas (parametrized)
- PropertyPanel shows correct fields for each node type
- FormulaField validates syntax (error on invalid, clears on valid)
- Edge creation between compatible nodes
- Delete node/edge works
- ValidationBar updates in real-time
- JsonPreview reflects current state
- Download produces valid JSON

**Play page** (`play.spec.ts`, ~12 tests):
- Game selector lists available games
- Upload custom JSON loads game
- Resume/pause toggles ticking
- Speed multiplier buttons work
- Generator cards show name, owned, cost, production
- Buy button disabled when unaffordable
- Upgrade purchased state
- Prestige panel shows currency preview

**Analyze page** (`analyze.spec.ts`, ~8 tests):
- Game selector works
- Run analysis shows loading then results
- Charts render (Plotly containers have content)
- Strategy comparison shows baseline vs variants
- Report generation produces HTML

## Directory Structure

```
frontend/
  vitest.config.ts                    # existing, no changes
  playwright.config.ts                # existing, add trace config
  src/
    test/
      setup.ts                        # existing MSW setup
      mocks/
        handlers.ts                   # existing, extend with new endpoints
        server.ts                     # existing
    editor/
      __tests__/
        conversion.test.ts            # existing, extend with new tests
      ValidationBar.test.ts           # new
    hooks/
      useGameSession.test.ts          # new
      useGameTick.test.ts             # new
      useAutoOptimize.test.ts         # new
  e2e/
    roundtrip/
      adcap-clone.spec.ts             # new
      prestige-tree.spec.ts           # new
      crafting-idle.spec.ts           # new
      fixture-upload.spec.ts          # new
      drag-and-drop.spec.ts           # new (single DnD verification)
    ui/
      editor.spec.ts                  # new
      play.spec.ts                    # new
      analyze.spec.ts                 # new
tests/
  fixtures/
    drainbuff.json                    # new
    synergy_tickspeed.json            # new
    multi_prestige.json               # new
    autobuyer_chain.json              # new
    converter_economy.json            # new
    gate_unlock.json                  # new
    adcap_clone.json                  # new
    prestige_tree.json                # new
    crafting_idle.json                # new
    checkpoints/                      # new — expected simulation values
      drainbuff_checkpoints.json
      synergy_tickspeed_checkpoints.json
      ...
  test_e2e_drainbuff.py              # new
  test_e2e_synergy.py                # new
  test_e2e_prestige.py               # new
  test_e2e_autobuyer.py              # new
  test_e2e_converter.py              # new
  test_e2e_gate.py                   # new
  test_e2e_adcap_clone.py            # new
  test_e2e_prestige_tree.py          # new
  test_e2e_crafting_idle.py          # new
  test_e2e_cross.py                  # new
```

## CI Integration

### New CI Jobs (`.github/workflows/ci.yml`)

Added as separate jobs alongside the existing `test` job. No dependencies between jobs — they run in parallel.

**`frontend-unit`** (~10s):
- `npm ci` → `npm run test:unit` (vitest)
- Runs on every push/PR, no backend needed

**`frontend-e2e`** (~2-3 min):
- Install Python deps + `pip install -e ".[dev]"`
- Install Node deps + `npx playwright install chromium`
- Playwright's webServer config auto-starts both servers
- `npm run test:e2e` (playwright)
- Upload Playwright trace artifacts on failure
- Runs on every push/PR

### Package.json Scripts

```json
"test:unit": "vitest run",
"test:e2e": "playwright test",
"test": "vitest run && playwright test"
```

## Test Count Summary

| Layer | New Tests | Runtime |
|-------|-----------|---------|
| Backend E2E | ~70 | ~30s |
| Vitest unit (new) | ~40 | ~5s |
| Vitest unit (existing) | 4 | — |
| Playwright roundtrip (live) | ~15 | ~60s |
| Playwright UI (mocked) | ~35 | ~30s |
| **Total new** | **~160** | **~2 min** |

Combined with existing 597 backend tests + 4 frontend tests: **~761 tests** across all layers.

## Existing Dependencies (Already Installed)

- `@playwright/test` — browser E2E testing
- `vitest` — fast unit test runner (Vite-native)
- `@testing-library/react` — React component testing utilities
- `@testing-library/jest-dom` — DOM assertion matchers
- `@testing-library/user-event` — user interaction simulation
- `msw` v2 — Mock Service Worker for API mocking in Vitest
- `jsdom` — DOM environment for Vitest

No new dependencies required.

## Out of Scope

- Visual regression testing (screenshot comparison)
- Performance/load testing of the UI
- Mobile/responsive testing beyond basic viewport checks
- Accessibility testing (a11y) — valuable but separate initiative
- Coverage targets — defer until baseline is established after Phase 4
