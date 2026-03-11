import type { AutoOptimizeResponse } from '../../api/types'
import { formatNumber, formatTime } from '../../utils/formatting'

interface PurchaseTimelineProps {
  result: AutoOptimizeResponse
  onClear: () => void
}

export default function PurchaseTimeline({ result, onClear }: PurchaseTimelineProps) {
  return (
    <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-blue-700 dark:text-blue-300">
          Optimizer Timeline
        </h3>
        <button
          onClick={onClear}
          className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 cursor-pointer"
        >
          Clear
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">Final Production</p>
          <p className="text-sm font-bold text-green-600 dark:text-green-400">
            {formatNumber(result.final_production)}/s
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">Final Balance</p>
          <p className="text-sm font-bold text-gray-900 dark:text-gray-100">
            {formatNumber(result.final_balance)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">Purchases</p>
          <p className="text-sm font-bold text-gray-900 dark:text-gray-100">
            {result.purchases.length}
          </p>
        </div>
      </div>

      {/* Purchase table */}
      {result.purchases.length > 0 && (
        <div className="overflow-x-auto max-h-64 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-blue-50 dark:bg-blue-900/30">
              <tr className="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-blue-200 dark:border-blue-800">
                <th className="py-1 pr-2">#</th>
                <th className="py-1 pr-2">Time</th>
                <th className="py-1 pr-2">Node</th>
                <th className="py-1 pr-2 text-right">Qty</th>
                <th className="py-1 text-right">Cost</th>
              </tr>
            </thead>
            <tbody>
              {result.purchases.map((step, i) => (
                <tr
                  key={i}
                  className="border-b border-blue-100 dark:border-blue-900/30 last:border-0"
                >
                  <td className="py-1 pr-2 text-gray-400 dark:text-gray-500">{i + 1}</td>
                  <td className="py-1 pr-2 text-gray-600 dark:text-gray-300">{formatTime(step.time)}</td>
                  <td className="py-1 pr-2 font-medium text-gray-900 dark:text-gray-100">{step.node_id}</td>
                  <td className="py-1 pr-2 text-right text-gray-600 dark:text-gray-300">{step.count}</td>
                  <td className="py-1 text-right text-gray-600 dark:text-gray-300">{formatNumber(step.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
