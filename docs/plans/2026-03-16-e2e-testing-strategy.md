# E2E Testing Strategy — Comprehensive Plan

**Date:** 2026-03-16
**Status:** Planning
**Goal:** Create realistic idle game fixtures and comprehensive end-to-end tests across backend, frontend UI, and editor workflows.

## Current State

- **782 tests** (676 backend + 106 frontend)
- **13 game fixtures** — minimal, single-mechanic focused
- **26 Playwright tests** — shallow page-load checks
- **101 backend E2E tests** — good but use small fixtures

## Gaps

1. No realistic multi-mechanic game fixtures
2. Shallow Playwright tests (page loads, not gameplay)
3. No editor → play → analyze roundtrip tests
4. No conversion fidelity tests with complex games
5. No cross-mechanic interaction validation
6. No visual regression testing

---

## Phase A: Realistic Game Fixtures

Design 5 games representing real idle game archetypes:

| Game | Archetype | Key Mechanics |
|------|-----------|---------------|
| **CookieClicker** | Simple clicker | Generators, upgrades (mult stacking), achievements, unlock gates |
| **FactoryIdle** | Converter economy | Generators → Converters (multi-input), drains, buffs, autobuyers |
| **PrestigeTower** | Deep prestige | 3+ prestige layers, sacrifice, nested generators, synergies |
| **SpeedRunner** | Tickspeed-focused | Tickspeed, probability, synergies, buff procs, end conditions |
| **FullKitchen** | Everything | All 22 node types, all 8 edge types, every mechanic |

Each fixture must:
- Be playable end-to-end (start → progress → prestige → win/stabilize)
- Have golden values at known time points
- Load in the editor, play page, and analysis page
- Exercise multiple mechanics interacting together

## Phase B: Backend E2E Tests (pytest)

For each game fixture:
1. **Simulation correctness** — golden value checks at t=60, t=300, t=3600
2. **Purchase sequences** — ordered buys, verify state
3. **Prestige cycles** — play → prestige → verify reset/bonus → replay
4. **Optimizer ordering** — greedy ≥ baseline; beam ≥ greedy
5. **Cross-mechanic interactions** — synergy+tickspeed, buff+drain, autobuyer+converter
6. **Edge cases** — capacity overflow, drain-to-zero, buff expiry mid-tick

## Phase C: Frontend E2E Tests (Playwright)

### C1: Play Page Tests
- Upload game → start session → verify resources
- Buy generator → verify cost deducted, count incremented
- Wait for production → verify resources increase
- Purchase upgrade → verify multiplier
- Speed controls (1x/10x/100x)
- Prestige → verify reset and currency
- Pause/Resume

### C2: Editor Page Tests
- Drag nodes from palette → verify canvas
- Connect nodes with edges
- Edit node properties
- Save → verify API call
- Load → verify restoration

### C3: Editor → Play Roundtrip
- Load game JSON in editor
- Verify all nodes/edges present
- Save → navigate to Play → verify gameplay works
- Navigate to Analyze → verify results render

### C4: Analysis Page Tests
- Select game → run analysis
- Verify results panel (dead upgrades, walls, strategy)
- Verify charts render
- Compare strategies
- Switch optimizer type

## Phase D: Conversion Fidelity Tests

For every fixture:
- JSON → gameToGraph() → graphToGame() → compare with original
- Verify all node/edge properties preserved
- Verify metadata preserved

## Phase E: Visual Regression (Future)

- Playwright screenshot comparison
- Baseline captures of Play/Editor/Analyze pages
- CSS/layout regression detection

---

## Implementation Priority

1. **Phase A** — foundation; everything depends on realistic fixtures
2. **Phase C1** — highest-value UI tests (Play Page)
3. **Phase B** — backend simulation correctness
4. **Phase C3** — editor roundtrip proves end-to-end
5. **Phase C2** — editor workflow tests
6. **Phase D** — conversion guards
7. **Phase C4** — analysis UI
