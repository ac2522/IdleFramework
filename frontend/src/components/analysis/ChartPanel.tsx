import Plot from 'react-plotly.js'
import type { AnalysisResult } from '../../api/types'

interface ChartPanelProps {
  result: AnalysisResult
}

export default function ChartPanel({ result }: ChartPanelProps) {
  const opt = result.optimizer_result
  if (!opt) {
    return (
      <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        No optimizer data available for charts.
      </p>
    )
  }

  // Production rate over time (line chart)
  const timelineX = opt.timeline.map((t) => t.time)
  const timelineY = opt.timeline.map((t) => t.production_rate)

  // Purchase cost distribution (bar chart)
  // Aggregate costs by node_id
  const costByNode: Record<string, number> = {}
  for (const p of opt.purchases) {
    costByNode[p.node_id] = (costByNode[p.node_id] ?? 0) + p.cost * p.count
  }
  const barLabels = Object.keys(costByNode)
  const barValues = Object.values(costByNode)

  const darkMode =
    typeof window !== 'undefined' && document.documentElement.classList.contains('dark')

  const layoutBase: Partial<Plotly.Layout> = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { color: darkMode ? '#d1d5db' : '#374151', size: 12 },
    margin: { l: 60, r: 20, t: 40, b: 50 },
    xaxis: {
      gridcolor: darkMode ? '#374151' : '#e5e7eb',
      zerolinecolor: darkMode ? '#4b5563' : '#d1d5db',
    },
    yaxis: {
      gridcolor: darkMode ? '#374151' : '#e5e7eb',
      zerolinecolor: darkMode ? '#4b5563' : '#d1d5db',
    },
  }

  return (
    <div className="space-y-4">
      {/* Production Rate Over Time */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-2 text-base font-semibold">Production Rate Over Time</h3>
        <Plot
          data={[
            {
              x: timelineX,
              y: timelineY,
              type: 'scatter',
              mode: 'lines',
              line: { color: '#3b82f6', width: 2 },
              name: 'Production',
            },
          ]}
          layout={{
            ...layoutBase,
            xaxis: { ...layoutBase.xaxis, title: { text: 'Time (s)', standoff: 10 } },
            yaxis: { ...layoutBase.yaxis, title: { text: 'Production Rate', standoff: 10 } },
            title: undefined,
            showlegend: false,
          }}
          config={{ responsive: true, displayModeBar: false }}
          useResizeHandler
          style={{ width: '100%', height: '300px' }}
        />
      </div>

      {/* Purchase Cost Distribution */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-2 text-base font-semibold">Purchase Cost Distribution</h3>
        {barLabels.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No purchases made.</p>
        ) : (
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
              },
            ]}
            layout={{
              ...layoutBase,
              xaxis: { ...layoutBase.xaxis, title: { text: 'Node', standoff: 10 } },
              yaxis: { ...layoutBase.yaxis, title: { text: 'Total Cost', standoff: 10 } },
              title: undefined,
              showlegend: false,
            }}
            config={{ responsive: true, displayModeBar: false }}
            useResizeHandler
            style={{ width: '100%', height: '300px' }}
          />
        )}
      </div>
    </div>
  )
}
