import type { ResourceState } from '../../api/types'
import { formatNumber, formatTime } from '../../utils/formatting'

interface ProductionSummaryProps {
  resources: Record<string, ResourceState>
  elapsedTime: number
}

export default function ProductionSummary({ resources, elapsedTime }: ProductionSummaryProps) {
  const totalRate = Object.values(resources).reduce((sum, r) => sum + r.production_rate, 0)

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        Production
      </h3>
      <div className="rounded-lg bg-white dark:bg-gray-800 px-3 py-2 shadow-sm space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-300">Total rate</span>
          <span className="font-medium text-green-600 dark:text-green-400">
            {formatNumber(totalRate)}/s
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-300">Elapsed</span>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {formatTime(elapsedTime)}
          </span>
        </div>
      </div>
    </div>
  )
}
