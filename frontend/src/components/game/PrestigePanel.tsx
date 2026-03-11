import type { PrestigeState } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface PrestigePanelProps {
  prestige: PrestigeState
  onPrestige: () => void
}

export default function PrestigePanel({ prestige, onPrestige }: PrestigePanelProps) {
  const canPrestige = prestige.available_currency > 0

  return (
    <div className="rounded-lg border-2 border-purple-300 dark:border-purple-700 bg-purple-50 dark:bg-purple-900/20 p-4 shadow-sm">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-purple-700 dark:text-purple-300 mb-2">
        Prestige
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">
        Available: <span className="font-bold text-purple-600 dark:text-purple-400">{formatNumber(prestige.available_currency)}</span>
      </p>
      {prestige.formula_preview && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          {prestige.formula_preview}
        </p>
      )}
      <button
        onClick={onPrestige}
        disabled={!canPrestige}
        className={`w-full py-2 text-sm font-semibold rounded-md transition-colors ${
          canPrestige
            ? 'bg-purple-600 hover:bg-purple-700 text-white cursor-pointer'
            : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
        }`}
      >
        Prestige Now
      </button>
    </div>
  )
}
