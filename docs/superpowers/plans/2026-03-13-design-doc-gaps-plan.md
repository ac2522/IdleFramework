# Design Doc Gaps: Editor Enhancements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add inline Plotly charts, tag autocomplete, inline strategy comparison, and faster analysis feedback to the node editor.

**Architecture:** All changes are frontend-only, touching 3 files: LiveAnalysisPanel.tsx (charts, comparison, debounce), PropertyPanel.tsx (tag autocomplete), EditorPage.tsx (pass nodes to PropertyPanel). No backend changes, no new dependencies.

**Tech Stack:** React 19, Plotly.js (already installed), TypeScript 5, Tailwind 4

**Spec:** `docs/superpowers/specs/2026-03-13-design-doc-gaps-spec.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/editor/LiveAnalysisPanel.tsx` | Modify | Add inline charts, strategy comparison, skeleton loading, reduce debounce |
| `frontend/src/editor/PropertyPanel.tsx` | Modify | Add tag autocomplete dropdown to TagsField, accept `allNodes` prop |
| `frontend/src/pages/EditorPage.tsx` | Modify | Pass `nodes` to PropertyPanel |

## Chunk 1: Faster Analysis Feedback + Skeleton Loading

### Task 1: Reduce debounce and add skeleton loading

**Files:**
- Modify: `frontend/src/editor/LiveAnalysisPanel.tsx:140-145` (debounce), `frontend/src/editor/LiveAnalysisPanel.tsx:160-228` (render)

- [ ] **Step 1: Reduce debounce from 1000ms to 400ms**

In `frontend/src/editor/LiveAnalysisPanel.tsx`, change line 142:

```tsx
// Before:
    const timer = setTimeout(() => {
      void analyze(nodes, edges, gameName, version)
    }, 1000)

// After:
    const timer = setTimeout(() => {
      void analyze(nodes, edges, gameName, version)
    }, 400)
```

- [ ] **Step 2: Add SkeletonRows component**

Add this component above the `LiveAnalysisPanel` function (after `ResultRow`, around line 71):

```tsx
function SkeletonRows() {
  return (
    <div className="space-y-2 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="flex justify-between items-baseline py-1">
          <div className="h-3 w-24 rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-3 w-12 rounded bg-gray-200 dark:bg-gray-700" />
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Show skeleton during analysis**

Replace the render section. Change the body inside the return (lines 161-228) to show the skeleton when `status === 'analyzing'` and there's no prior result:

In the return block, after the error display (`{status === 'error' && errorMsg && ...}`), add:

```tsx
      {status === 'analyzing' && !result && <SkeletonRows />}
```

This shows the skeleton only on the first analysis (before any result exists). Subsequent analyses keep the previous result visible with the "Analyzing..." indicator.

- [ ] **Step 4: Verify build compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/editor/LiveAnalysisPanel.tsx
git commit -m "feat(editor): reduce analysis debounce to 400ms, add skeleton loading"
```

---

## Chunk 2: Inline Plotly Charts in LiveAnalysisPanel

### Task 2: Add production rate sparkline and cost distribution chart

**Files:**
- Modify: `frontend/src/editor/LiveAnalysisPanel.tsx`

- [ ] **Step 1: Add Plotly import**

At the top of `frontend/src/editor/LiveAnalysisPanel.tsx`, add:

```tsx
import Plot from 'react-plotly.js'
import type Plotly from 'plotly.js'
```

- [ ] **Step 2: Add MiniCharts component**

Add this component after `SkeletonRows` (added in Task 1):

```tsx
function MiniCharts({ result }: { result: AnalysisResult }) {
  const [collapsed, setCollapsed] = useState(false)
  const opt = result.optimizer_result
  if (!opt) {
    return (
      <div className="mt-3">
        <p className="text-xs text-gray-400 dark:text-gray-500">No optimizer data for charts.</p>
      </div>
    )
  }

  const darkMode =
    typeof window !== 'undefined' && document.documentElement.classList.contains('dark')

  const layoutBase: Partial<Plotly.Layout> = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: darkMode ? '#9ca3af' : '#6b7280', size: 9 },
    margin: { l: 30, r: 8, t: 4, b: 24 },
    xaxis: {
      gridcolor: darkMode ? '#374151' : '#f3f4f6',
      zerolinecolor: darkMode ? '#4b5563' : '#e5e7eb',
    },
    yaxis: {
      gridcolor: darkMode ? '#374151' : '#f3f4f6',
      zerolinecolor: darkMode ? '#4b5563' : '#e5e7eb',
    },
  }

  const plotConfig: Partial<Plotly.Config> = {
    responsive: true,
    displayModeBar: false,
    staticPlot: false,
  }

  // Production timeline data
  const timelineX = opt.timeline.map((t) => t.time)
  const timelineY = opt.timeline.map((t) => t.production_rate)

  // Cost distribution data
  const costByNode: Record<string, number> = {}
  for (const p of opt.purchases) {
    costByNode[p.node_id] = (costByNode[p.node_id] ?? 0) + p.cost * p.count
  }
  const barLabels = Object.keys(costByNode)
  const barValues = Object.values(costByNode)

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 hover:text-gray-700 dark:hover:text-gray-300"
      >
        <svg
          className={`h-3 w-3 transition-transform ${collapsed ? '' : 'rotate-90'}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        Charts
      </button>

      {!collapsed && (
        <div className="space-y-3">
          {/* Production Rate Sparkline */}
          {timelineX.length > 0 && (
            <div>
              <p className="text-[10px] text-gray-400 dark:text-gray-500 mb-0.5">Production Rate</p>
              <Plot
                data={[
                  {
                    x: timelineX,
                    y: timelineY,
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: '#3b82f6', width: 1.5 },
                    hovertemplate: 't=%{x:.0f}s<br>rate=%{y:.2f}<extra></extra>',
                  },
                ]}
                layout={{
                  ...layoutBase,
                  height: 120,
                  showlegend: false,
                }}
                config={plotConfig}
                useResizeHandler
                style={{ width: '100%', height: '120px' }}
              />
            </div>
          )}

          {/* Cost Distribution */}
          {barLabels.length > 0 && (
            <div>
              <p className="text-[10px] text-gray-400 dark:text-gray-500 mb-0.5">Cost Distribution</p>
              <Plot
                data={[
                  {
                    x: barLabels,
                    y: barValues,
                    type: 'bar',
                    marker: {
                      color: barLabels.map(
                        (_, i) =>
                          ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'][i % 6],
                      ),
                    },
                    hovertemplate: '%{x}<br>cost=%{y:.2f}<extra></extra>',
                  },
                ]}
                layout={{
                  ...layoutBase,
                  height: 120,
                  showlegend: false,
                }}
                config={plotConfig}
                useResizeHandler
                style={{ width: '100%', height: '120px' }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Add useState import if not present**

The file already imports `useState` on line 1. No change needed — just verify it's there.

- [ ] **Step 4: Render MiniCharts in the panel**

In the `LiveAnalysisPanel` return, after the progression walls list (after the closing `)}` around line 219) and before the closing `</div>` of the `{result && status !== 'error' && (` block, add:

```tsx
          <MiniCharts result={result} />
```

- [ ] **Step 5: Verify build compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/editor/LiveAnalysisPanel.tsx
git commit -m "feat(editor): add inline Plotly charts to LiveAnalysisPanel"
```

---

## Chunk 3: Tag Autocomplete in PropertyPanel

### Task 3: Add autocomplete suggestions to TagsField

**Files:**
- Modify: `frontend/src/editor/PropertyPanel.tsx:88-139` (TagsField component)
- Modify: `frontend/src/editor/PropertyPanel.tsx:266-306` (PropertyPanel component — accept allNodes)
- Modify: `frontend/src/pages/EditorPage.tsx:145-151` (pass nodes to PropertyPanel)

- [ ] **Step 1: Update PropertyPanel to accept and pass allNodes**

In `frontend/src/editor/PropertyPanel.tsx`, update the `PropertyPanelProps` interface (line 266-269):

```tsx
// Before:
interface PropertyPanelProps {
  selectedNode: Node<EditorNodeData> | null
  onUpdateNode: (nodeId: string, data: Partial<EditorNodeData>) => void
}

// After:
interface PropertyPanelProps {
  selectedNode: Node<EditorNodeData> | null
  onUpdateNode: (nodeId: string, data: Partial<EditorNodeData>) => void
  allNodes: Node<EditorNodeData>[]
}
```

Update the `PropertyPanel` function signature (line 271):

```tsx
// Before:
export default function PropertyPanel({ selectedNode, onUpdateNode }: PropertyPanelProps) {

// After:
export default function PropertyPanel({ selectedNode, onUpdateNode, allNodes }: PropertyPanelProps) {
```

Compute `allTags` and pass to TagsField. After `const data = selectedNode.data` (line 280), add:

```tsx
  // Collect all tags across all nodes, minus tags on the selected node
  const allTags = Array.from(
    new Set(allNodes.flatMap((n) => (n.data as EditorNodeData).tags ?? []))
  ).filter((t) => !data.tags.includes(t))
```

Update the TagsField usage (line 295):

```tsx
// Before:
      <TagsField label="Tags" tags={data.tags} onChange={(tags) => update({ tags } as Partial<EditorNodeData>)} />

// After:
      <TagsField label="Tags" tags={data.tags} onChange={(tags) => update({ tags } as Partial<EditorNodeData>)} suggestions={allTags} />
```

- [ ] **Step 2: Add autocomplete dropdown to TagsField**

Replace the `TagsField` function (lines 88-139) with:

```tsx
function TagsField({ label, tags, onChange, suggestions = [] }: {
  label: string
  tags: string[]
  onChange: (tags: string[]) => void
  suggestions?: string[]
}) {
  const [input, setInput] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)

  const filtered = input.trim()
    ? suggestions.filter((s) => s.toLowerCase().startsWith(input.toLowerCase()))
    : []

  function addTag(tag: string) {
    if (!tags.includes(tag)) {
      onChange([...tags, tag])
    }
    setInput('')
    setShowDropdown(false)
    setHighlightIndex(-1)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown' && showDropdown && filtered.length > 0) {
      e.preventDefault()
      setHighlightIndex((prev) => (prev + 1) % filtered.length)
    } else if (e.key === 'ArrowUp' && showDropdown && filtered.length > 0) {
      e.preventDefault()
      setHighlightIndex((prev) => (prev <= 0 ? filtered.length - 1 : prev - 1))
    } else if (e.key === 'Enter' && input.trim()) {
      e.preventDefault()
      if (highlightIndex >= 0 && highlightIndex < filtered.length) {
        addTag(filtered[highlightIndex])
      } else if (filtered.length > 0) {
        addTag(filtered[0])
      } else {
        addTag(input.trim())
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
      setHighlightIndex(-1)
    }
  }

  function handleInputChange(value: string) {
    setInput(value)
    setShowDropdown(value.trim().length > 0)
    setHighlightIndex(-1)
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag))
  }

  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
      <div className="flex flex-wrap gap-1 mb-1">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-0.5 rounded-full bg-blue-100 dark:bg-blue-900 px-2 py-0.5 text-xs text-blue-800 dark:text-blue-200"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="ml-0.5 text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-100"
            >
              &times;
            </button>
          </span>
        ))}
      </div>
      <div className="relative">
        <input
          type="text"
          value={input}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (input.trim()) setShowDropdown(true) }}
          onBlur={() => { setTimeout(() => setShowDropdown(false), 150) }}
          placeholder="Type + Enter to add"
          className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {showDropdown && filtered.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 shadow-lg max-h-32 overflow-y-auto">
            {filtered.map((suggestion, idx) => (
              <li key={suggestion}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => addTag(suggestion)}
                  className={`w-full px-2 py-1.5 text-left text-sm text-gray-900 dark:text-gray-100 ${idx === highlightIndex ? 'bg-blue-50 dark:bg-blue-900/30' : 'hover:bg-blue-50 dark:hover:bg-blue-900/30'}`}
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Update EditorPage to pass nodes to PropertyPanel**

In `frontend/src/pages/EditorPage.tsx`, update the PropertyPanel usage (around line 147):

```tsx
// Before:
            <PropertyPanel
              selectedNode={selectedNode as Node<EditorNodeData> | null}
              onUpdateNode={onUpdateNode}
            />

// After:
            <PropertyPanel
              selectedNode={selectedNode as Node<EditorNodeData> | null}
              onUpdateNode={onUpdateNode}
              allNodes={nodes as unknown as Node<EditorNodeData>[]}
            />
```

- [ ] **Step 4: Verify build compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/editor/PropertyPanel.tsx frontend/src/pages/EditorPage.tsx
git commit -m "feat(editor): add tag autocomplete suggestions to PropertyPanel"
```

---

## Chunk 4: Inline Strategy Comparison

### Task 4: Add Compare Tags section to LiveAnalysisPanel

**Files:**
- Modify: `frontend/src/editor/LiveAnalysisPanel.tsx`

- [ ] **Step 1: Add compareStrategies import**

At the top of `frontend/src/editor/LiveAnalysisPanel.tsx`, add to the imports:

```tsx
import { compareStrategies } from '../api/analysis.ts'
import type { CompareResult } from '../api/types.ts'
```

- [ ] **Step 2: Add CompareTagsSection component**

Add this component after `MiniCharts`:

```tsx
function CompareTagsSection({ gameId, nodes }: { gameId: string | null; nodes: EditorNode[] }) {
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null)
  const [comparing, setComparing] = useState(false)

  // Collect unique tags from all nodes
  const uniqueTags = Array.from(
    new Set(nodes.flatMap((n) => n.data.tags ?? []))
  )

  if (uniqueTags.length === 0 || !gameId) return null

  async function handleCompare() {
    if (!gameId) return
    setComparing(true)
    try {
      const result = await compareStrategies({
        game_id: gameId,
        strategies: uniqueTags,
      })
      setCompareResult(result)
    } catch {
      setCompareResult(null)
    } finally {
      setComparing(false)
    }
  }

  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
        Tag Comparison
      </p>

      {!compareResult && (
        <button
          type="button"
          onClick={handleCompare}
          disabled={comparing}
          className="w-full rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {comparing ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-white animate-pulse" />
              Comparing...
            </span>
          ) : (
            'Compare Tags'
          )}
        </button>
      )}

      {compareResult && (
        <div className="space-y-1.5">
          <div className="flex justify-between items-baseline py-0.5">
            <span className="text-[10px] text-gray-400 dark:text-gray-500">Baseline</span>
            <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
              {formatNumber(compareResult.baseline.final_production)}/s
            </span>
          </div>
          {Object.entries(compareResult.variants).map(([tag, data]) => {
            const pct = (data.ratio_vs_baseline * 100).toFixed(1)
            const isWorse = data.ratio_vs_baseline < 1
            return (
              <div key={tag} className="flex justify-between items-baseline py-0.5">
                <span className="text-xs text-gray-600 dark:text-gray-400">Without "{tag}"</span>
                <span className={`text-xs font-medium ${isWorse ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                  {pct}%
                </span>
              </div>
            )
          })}
          <button
            type="button"
            onClick={() => setCompareResult(null)}
            className="mt-1 text-[10px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            Re-run comparison
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Update LiveAnalysisPanel to track gameId and render CompareTagsSection**

The `draftGameIdRef` already stores the game ID. We need to expose it as state so the comparison component can use it.

Add a new state variable in `LiveAnalysisPanel` after the existing state declarations (line 78):

```tsx
  const [lastGameId, setLastGameId] = useState<string | null>(null)
```

In the `analyze` callback, after `draftGameIdRef.current = gameId` (line 106), add:

```tsx
      setLastGameId(gameId)
```

In the return block, after `<MiniCharts result={result} />` and before the closing `</div>` of the `{result && status !== 'error' && (` block, add:

```tsx
          <CompareTagsSection gameId={lastGameId} nodes={nodes} />
```

- [ ] **Step 4: Verify build compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/editor/LiveAnalysisPanel.tsx
git commit -m "feat(editor): add inline tag strategy comparison to LiveAnalysisPanel"
```

---

## Chunk 5: Final Verification

### Task 5: Build check and existing test suite

- [ ] **Step 1: Run frontend build**

Run: `cd frontend && npx vite build`
Expected: Build succeeds with no errors

- [ ] **Step 2: Run existing backend tests**

Run: `cd /home/zaia/Development/IdleFramework && python -m pytest tests/ -x -q`
Expected: All tests pass (no backend changes, so this should be unchanged)

- [ ] **Step 3: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Run linter**

Run: `cd frontend && npx eslint src/editor/LiveAnalysisPanel.tsx src/editor/PropertyPanel.tsx src/pages/EditorPage.tsx`
Expected: No errors (or only pre-existing warnings)

- [ ] **Step 5: Fix any lint/type issues found**

Address any issues from steps 1-4.

- [ ] **Step 6: Final commit if fixes were needed**

```bash
git add -A
git commit -m "fix(editor): address lint/type issues from design doc gap features"
```
