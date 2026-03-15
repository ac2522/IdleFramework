# Design Doc Gaps: Editor Enhancements Spec

## Overview

Fill 4 gaps from the original design doc in the node editor: inline Plotly charts, tag autocomplete, inline strategy comparison, and faster analysis feedback. All changes stay in the editor — no new pages, no new backend endpoints, no WebSocket.

**Priority:** Easy for self-hosters to clone and run. No new dependencies.

## 1. Inline Charts in LiveAnalysisPanel

**What:** Add two small Plotly charts below the existing text results in the LiveAnalysisPanel.

**Charts:**
- **Production Rate sparkline** — line chart from `optimizer_result.timeline` (time vs production_rate). Height ~120px, no axis titles (space is tight), tooltips on hover.
- **Cost Distribution mini-bar** — bar chart from `optimizer_result.purchases`, aggregated by node_id. Same compact sizing.

**Behavior:**
- Charts appear in a collapsible section, default expanded
- Reuse dark mode detection from ChartPanel (`document.documentElement.classList.contains('dark')`)
- Show "No optimizer data" placeholder when `optimizer_result` is null
- Use `displayModeBar: false` and `responsive: true` for clean compact look
- Minimal margins to fit the 272px sidebar width

**Files modified:** `frontend/src/editor/LiveAnalysisPanel.tsx`

## 2. Tag Autocomplete in PropertyPanel

**What:** Enhance the existing TagsField to suggest tags already used elsewhere in the graph.

**How:**
- EditorPage passes all current nodes to PropertyPanel (it already has `selectedNode`, but needs the full node list for tag collection)
- PropertyPanel computes `allTags`: unique set of all tags across all nodes, minus tags already on the selected node
- TagsField receives `suggestions: string[]` prop
- On input change, filter suggestions by prefix match (case-insensitive)
- Show a simple dropdown below the input with matching suggestions
- Click suggestion or arrow-down + Enter to select
- Dropdown dismissed on blur or Escape

**Files modified:**
- `frontend/src/editor/PropertyPanel.tsx` — add suggestions logic to TagsField, accept `allNodes` prop
- `frontend/src/pages/EditorPage.tsx` — pass `nodes` to PropertyPanel

## 3. Inline Strategy Comparison in LiveAnalysisPanel

**What:** Add a "Compare Tags" section to LiveAnalysisPanel that calls the existing compare endpoint and shows results inline.

**Behavior:**
- After analysis completes successfully, check if any nodes in the graph have non-empty tags
- If tags exist, show a "Compare Tags" button
- On click, call `compareStrategies({ game_id, strategies: uniqueTags })` using the draft game
- Show results inline as a compact list: tag name → "X% of baseline" with color coding (red if <100%, green if >=100%)
- Show baseline production value at top
- Loading state: small spinner replacing the button text
- Results persist until next analysis run clears them

**Files modified:**
- `frontend/src/editor/LiveAnalysisPanel.tsx` — add comparison section
- Import `compareStrategies` from `../api/analysis.ts`

## 4. Faster Analysis Feedback

**What:** Reduce perceived latency of live analysis.

**Changes:**
- Reduce debounce from 1000ms to 400ms
- Add a shimmer/skeleton loading state during analysis instead of just the "Analyzing..." text — show gray placeholder bars where results would appear
- Keep REST polling (no WebSocket)

**Files modified:** `frontend/src/editor/LiveAnalysisPanel.tsx`

## Non-Goals

- No WebSocket implementation (REST is simpler for self-hosters)
- No new npm dependencies (Plotly already installed)
- No benchmarking to hit <200ms (server-side simulation time is the bottleneck, not the transport)
- No separate tag management panel (autocomplete on the existing TagsField is sufficient)
- No changes to backend endpoints

## Testing

- Existing tests should continue to pass
- Manual verification: open editor, add nodes, verify charts render, tags autocomplete, comparison works
