# Phase C: Playwright UI E2E Tests — Detailed Plan

**Date:** 2026-03-16
**Status:** COMPLETE — 43 Playwright tests passing, review feedback incorporated
**Depends on:** Phase A (game fixtures), working backend

## Overview

Comprehensive Playwright tests for all 3 frontend pages, organized into C1-C4 sub-phases with shared helper infrastructure.

## Shared Infrastructure

### `frontend/e2e/helpers/fixtures.ts`
- `fixtureDir()` — resolves `tests/fixtures/` using ESM-compatible path resolution
- `fixturePath(name)` — path to specific fixture JSON
- `readFixture(name)` — parse fixture JSON
- Fixes the `__dirname` ESM issue in existing tests

### `frontend/e2e/helpers/mocks.ts`
Consolidated API mock functions (extracted from scattered ui/*.spec.ts):
- `mockGamesList`, `mockStartSession`, `mockAdvance`, `mockPurchase`
- `mockPrestige`, `mockAutoOptimize`, `mockAnalysis`, `mockCompare`
- `mockCreateGame`, `mockGetGame`

### `frontend/e2e/helpers/session.ts`
- `startGameSession(page, gameId?)` — navigate + wait for session
- `waitForResourceChange(page, name, predicate)` — poll resource value
- `buyGenerator(page, genName)` — click Buy 1 on generator card
- `waitForTick(page)` — wait for advance API response

### `frontend/e2e/helpers/editor.ts`
- `uploadFixtureInEditor(page, name)` — upload via file input
- `dragNodeFromPalette(page, nodeType, position?)` — DnD with dataTransfer
- `selectNode(page, nodeId?)` — click React Flow node
- `getNodeCount(page)`, `getEdgeCount(page)` — count canvas elements
- `waitForValidationBar(page, text?)` — wait for validation state

## File Organization

```
frontend/e2e/
  helpers/
    fixtures.ts
    mocks.ts
    session.ts
    editor.ts
  play/
    gameplay.spec.ts       # C1: 9 tests
    game-selector.spec.ts  # C1: 2 tests
  editor/
    canvas.spec.ts         # C2: 6 tests
    toolbar.spec.ts        # C2: 4 tests
    property-panel.spec.ts # C2: 4 tests
  roundtrip/
    editor-to-play.spec.ts # C3: 4 tests
  analyze/
    analysis.spec.ts       # C4: 6 tests
```

## C1: Play Page Tests (35 tests total)

### gameplay.spec.ts

1. **uploads custom game fixture and starts session** — setInputFiles → POST → verify resources/generators visible
2. **buys a generator and verifies UI updates** — click Buy 1 → verify owned count, cost change, balance decrease
3. **production tick increases resource balance** — Resume → waitForResponse(/advance) → verify balance increased
4. **speed controls change tick speed** — click 10x → verify advance body has seconds:10
5. **pause stops production, resume restarts** — pause → no API calls → resume → balance increases
6. **prestige resets UI and shows currency** — mock prestige-ready state → click Prestige Now → verify reset
7. **auto-optimize shows purchase timeline** — click Auto-Optimize → verify timeline heading, rows, stats
8. **auto-optimize clear removes timeline** — click Clear → verify timeline gone
9. **upgrade card shows and can be purchased** — find upgrade → Buy → verify purchased

### game-selector.spec.ts

10. **game selector shows available games** — verify select has options
11. **switching games restarts session** — change select → verify new game's UI

## C2: Editor Page Tests (14 tests total)

### canvas.spec.ts

12. **drag node from palette onto canvas** — DnD with synthetic dataTransfer events → node count increases
13. **select node and verify property panel** — click node → Properties heading, ID, Name, type-specific fields
14. **edit node properties and verify persistence** — change field → deselect → reselect → value persists
15. **connect two nodes with edge** — drag source handle to target handle → edge count increases
16. **delete a node** — select → Delete key → node count decreases
17. **delete an edge** — select edge → Delete key → edge count decreases

### toolbar.spec.ts

18. **save game sends POST to API** — enter name → Save → verify 201 response
19. **load game populates canvas from API** — Load → select game → verify nodes appear
20. **download JSON creates file** — waitForEvent('download') → verify file content
21. **upload JSON populates canvas** — setInputFiles → verify node count matches fixture

### property-panel.spec.ts

22. **formula field shows validation error** — type `sqrt(` → wait 300ms → red error
23. **formula field shows valid for correct syntax** — type `sqrt(x * 2)` → green valid
24. **edge properties panel for selected edge** — click edge → Edge Properties heading, source/target fields
25. **validation bar shows correct status** — valid fixture → green "Valid"; orphaned node → red errors

## C3: Editor → Play Roundtrip (4 tests)

### editor-to-play.spec.ts

26. **load game in editor then play it** — upload → Save → navigate /play → verify gameplay
27. **edit game, save, replay, verify changes** — modify base_production → save → play → verify new rate
28. **upload → editor → analyze** — upload → save → /analyze → Run Analysis → verify charts
29. **fixture roundtrip preserves nodes/edges** — upload → download → re-upload → same counts

## C4: Analysis Page Tests (6 tests)

### analysis.spec.ts

30. **select game and run analysis** — Run Analysis → verify Summary, Dead Upgrades, Walls, Strategy
31. **Plotly charts render** — verify `.js-plotly-plot` elements with SVG content
32. **compare free vs paid** — click Compare → verify baseline + variant rows
33. **switching optimizer changes results** — Greedy → Beam → verify results update
34. **changing simulation time** — set 60s → Run → verify reflected in summary
35. **loading spinner during computation** — verify "Running analysis..." appears then disappears

## Technical Notes

### Drag-and-Drop in React Flow
React Flow uses HTML5 DnD with `dataTransfer.setData('application/reactflow', type)`. Use `page.evaluate()` to dispatch synthetic DragEvent with DataTransfer on the canvas. Fallback to Playwright `dragTo()` if supported.

### Waiting for Game Ticks
```typescript
const response = await page.waitForResponse(r => r.url().includes('/advance') && r.status() === 200)
```

### Verifying Plotly Charts
```typescript
await expect(page.locator('.js-plotly-plot').first()).toBeVisible({ timeout: 10_000 })
expect(await page.locator('.js-plotly-plot').count()).toBe(2)
```

### File Upload
- GameSelector: `page.locator('#game-upload-input').setInputFiles(path)`
- Editor: `page.locator('input[type="file"][accept=".json"]').setInputFiles(path)`

## Implementation Sequence

1. Build helpers (fixtures.ts → mocks.ts → session.ts → editor.ts)
2. C1 Play Page tests (highest priority)
3. C2 Editor tests (DnD complexity)
4. C3 Roundtrip tests (depends on C1+C2)
5. C4 Analysis tests (relatively straightforward)

## Known Risks

1. HTML5 DnD may not work with Playwright's dragTo — synthetic events fallback
2. Backend startup > 15s — may need increased webServer timeout
3. Game tick timing sensitivity — use waitForResponse, not waitForTimeout
4. Plotly async rendering — generous timeouts for chart assertions
