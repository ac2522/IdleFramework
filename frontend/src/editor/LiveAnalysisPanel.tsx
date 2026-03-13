import { useState, useEffect, useRef, useCallback } from 'react'
import type { Edge } from '@xyflow/react'
import Plot from 'react-plotly.js'
import type Plotly from 'plotly.js'
import { graphToGame } from './conversion.ts'
import { runAnalysis } from '../api/analysis.ts'
import { compareStrategies } from '../api/analysis.ts'
import { createGame, deleteGame } from '../api/games.ts'
import type { AnalysisResult } from '../api/types.ts'
import type { CompareResult } from '../api/types.ts'
import type { EditorNode } from './types.ts'

// -- Status types --

type AnalysisStatus = 'idle' | 'analyzing' | 'healthy' | 'warnings' | 'error'

interface LiveAnalysisPanelProps {
  nodes: EditorNode[]
  edges: Edge[]
  gameName: string
}

function StatusIndicator({ status, errorMsg }: { status: AnalysisStatus; errorMsg: string | null }) {
  switch (status) {
    case 'idle':
      return (
        <span className="text-xs text-gray-400 dark:text-gray-500">
          Waiting for graph...
        </span>
      )
    case 'analyzing':
      return (
        <span className="inline-flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400">
          <span className="inline-block h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
          Analyzing...
        </span>
      )
    case 'healthy':
      return (
        <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          Healthy
        </span>
      )
    case 'warnings':
      return (
        <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
          <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          Warnings
        </span>
      )
    case 'error':
      return (
        <span className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400" title={errorMsg ?? undefined}>
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          Error
        </span>
      )
  }
}

function ResultRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-baseline py-1">
      <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
      <span className="text-xs font-medium text-gray-800 dark:text-gray-200">{value}</span>
    </div>
  )
}

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

  const timelineX = opt.timeline.map((t) => t.time)
  const timelineY = opt.timeline.map((t) => t.production_rate)

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

function CompareTagsSection({ gameId, nodes }: { gameId: string | null; nodes: EditorNode[] }) {
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null)
  const [comparing, setComparing] = useState(false)

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
                <span className="text-xs text-gray-600 dark:text-gray-400">Without &quot;{tag}&quot;</span>
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

export default function LiveAnalysisPanel({ nodes, edges, gameName }: LiveAnalysisPanelProps) {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [status, setStatus] = useState<AnalysisStatus>('idle')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [lastGameId, setLastGameId] = useState<string | null>(null)
  const versionRef = useRef(0)
  const draftGameIdRef = useRef<string | null>(null)

  const analyze = useCallback(async (
    currentNodes: EditorNode[],
    currentEdges: Edge[],
    currentName: string,
    version: number,
  ) => {
    // Skip if no nodes
    if (currentNodes.length === 0) {
      setStatus('idle')
      setResult(null)
      return
    }

    setStatus('analyzing')
    setErrorMsg(null)

    try {
      // Use a stable draft name so createGame overwrites the same file each time
      const draftName = `_live-preview-${currentName || 'untitled'}`
      const gameJson = graphToGame(currentNodes, currentEdges, {
        name: draftName,
        stacking_groups: {},
      })

      // Save game (overwrites previous draft since slugified name is stable)
      const { id: gameId } = await createGame(gameJson as unknown as Record<string, unknown>)
      draftGameIdRef.current = gameId
      setLastGameId(gameId)

      // Discard if stale
      if (version !== versionRef.current) return

      // Run analysis
      const analysisResult = await runAnalysis({ game_id: gameId, simulation_time: 60 })

      // Discard if stale
      if (version !== versionRef.current) return

      setResult(analysisResult)

      // Determine status from results
      const hasWarnings =
        analysisResult.dead_upgrades.length > 0 ||
        analysisResult.progression_walls.length > 0 ||
        (analysisResult.dominant_strategy?.dominant_gen != null)

      setStatus(hasWarnings ? 'warnings' : 'healthy')
    } catch (err) {
      // Discard if stale
      if (version !== versionRef.current) return

      const message = err instanceof Error ? err.message : 'Analysis failed'
      setErrorMsg(message)
      setStatus('error')
    }
  }, [])

  // Debounce analysis on graph/name changes
  useEffect(() => {
    const version = ++versionRef.current

    const timer = setTimeout(() => {
      void analyze(nodes, edges, gameName, version)
    }, 400)

    return () => clearTimeout(timer)
  }, [nodes, edges, gameName, analyze])

  // Cleanup draft game on unmount
  useEffect(() => {
    return () => {
      const draftId = draftGameIdRef.current
      if (draftId) {
        void deleteGame(draftId).catch(() => { /* best-effort cleanup */ })
      }
    }
  }, [])

  // Compute production rate from optimizer result
  const productionRate = result?.optimizer_result?.final_production ?? null

  return (
    <div className="p-4 overflow-y-auto h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Live Analysis
        </h3>
        <StatusIndicator status={status} errorMsg={errorMsg} />
      </div>

      {status === 'error' && errorMsg && (
        <p className="text-xs text-red-500 dark:text-red-400 mb-3 break-words">{errorMsg}</p>
      )}

      {status === 'analyzing' && !result && <SkeletonRows />}

      {result && status !== 'error' && (
        <div className="space-y-1">
          {productionRate != null && (
            <ResultRow label="Production Rate" value={formatNumber(productionRate)} />
          )}
          <ResultRow
            label="Dead Upgrades"
            value={String(result.dead_upgrades.length)}
          />
          <ResultRow
            label="Progression Walls"
            value={String(result.progression_walls.length)}
          />
          <ResultRow
            label="Dominant Strategy"
            value={result.dominant_strategy?.dominant_gen ?? 'None'}
          />

          {result.dead_upgrades.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                Dead Upgrades
              </p>
              <ul className="space-y-0.5">
                {result.dead_upgrades.map((du) => (
                  <li key={du.upgrade_id} className="text-xs text-amber-700 dark:text-amber-300">
                    {du.upgrade_id}: {du.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.progression_walls.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                Progression Walls
              </p>
              <ul className="space-y-0.5">
                {result.progression_walls.map((pw, i) => (
                  <li key={i} className="text-xs text-amber-700 dark:text-amber-300">
                    {pw.reason}{pw.severity ? ` (${pw.severity})` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <MiniCharts result={result} />
          <CompareTagsSection gameId={lastGameId} nodes={nodes} />
        </div>
      )}

      {status === 'idle' && !result && (
        <p className="text-xs text-gray-400 dark:text-gray-500">
          Add nodes to start analysis.
        </p>
      )}
    </div>
  )
}

function formatNumber(n: number): string {
  if (Math.abs(n) >= 1e9) return n.toExponential(2)
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(2)}M`
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(2)}K`
  return n.toFixed(2)
}
