import type { ResourceState } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface ResourceDisplayProps {
  resources: Record<string, ResourceState>
}

export default function ResourceDisplay({ resources }: ResourceDisplayProps) {
  const entries = Object.entries(resources)

  if (entries.length === 0) {
    return <p className="text-sm text-gray-400 dark:text-gray-500">No resources</p>
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        Resources
      </h3>
      {entries.map(([name, res]) => (
        <div
          key={name}
          className="flex items-center justify-between rounded-lg bg-white dark:bg-gray-800 px-3 py-2 shadow-sm"
        >
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">
            {name}
          </span>
          <div className="text-right ml-2 shrink-0">
            <span className="text-sm font-bold text-gray-900 dark:text-gray-100">
              {formatNumber(res.current_value)}
            </span>
            {res.production_rate > 0 && (
              <span className="ml-1 text-xs text-green-600 dark:text-green-400">
                +{formatNumber(res.production_rate)}/s
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
