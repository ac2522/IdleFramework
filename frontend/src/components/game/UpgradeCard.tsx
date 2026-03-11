import type { UpgradeState } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface UpgradeCardProps {
  name: string
  upgrade: UpgradeState
  onBuy: () => void
}

export default function UpgradeCard({ name, upgrade, onBuy }: UpgradeCardProps) {
  if (upgrade.purchased) return null

  return (
    <div className="flex items-center justify-between rounded-lg bg-white dark:bg-gray-800 px-3 py-2 shadow-sm border border-amber-200 dark:border-amber-800/50">
      <div className="min-w-0 mr-2">
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate block">
          {name}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {formatNumber(upgrade.cost)}
        </span>
      </div>
      <button
        onClick={onBuy}
        disabled={!upgrade.affordable}
        className={`shrink-0 px-3 py-1 text-sm font-medium rounded-md transition-colors ${
          upgrade.affordable
            ? 'bg-amber-500 hover:bg-amber-600 text-white cursor-pointer'
            : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
        }`}
      >
        Buy
      </button>
    </div>
  )
}
