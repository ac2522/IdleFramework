import type { CompareResult } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface ComparisonViewProps {
  compareResult: CompareResult
}

export default function ComparisonView({ compareResult }: ComparisonViewProps) {
  const variants = Object.entries(compareResult.variants)

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-base font-semibold">Free vs Paid Comparison</h3>

      {/* Baseline */}
      <div className="mb-4 rounded-md bg-blue-50 p-3 dark:bg-blue-900/20">
        <p className="text-sm font-medium text-blue-800 dark:text-blue-300">Baseline (all content)</p>
        <p className="mt-1 text-lg font-semibold text-blue-900 dark:text-blue-100">
          {formatNumber(compareResult.baseline.final_production)}/s
        </p>
      </div>

      {/* Variants */}
      {variants.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">No variants to compare.</p>
      ) : (
        <div className="space-y-3">
          {variants.map(([name, data]) => {
            const ratio = data.ratio_vs_baseline
            const isWorse = ratio < 1
            return (
              <div
                key={name}
                className="flex items-center justify-between rounded-md border border-gray-100 p-3 dark:border-gray-700"
              >
                <div>
                  <p className="text-sm font-medium">{name}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {formatNumber(data.final_production)}/s
                  </p>
                </div>
                <div className="text-right">
                  <span
                    className={`inline-block rounded-full px-2.5 py-1 text-xs font-semibold ${
                      isWorse
                        ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                        : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                    }`}
                  >
                    {(ratio * 100).toFixed(1)}% of baseline
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
