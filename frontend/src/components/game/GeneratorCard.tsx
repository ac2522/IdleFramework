import type { GeneratorState } from '../../api/types'
import { formatNumber } from '../../utils/formatting'

interface GeneratorCardProps {
  name: string
  gen: GeneratorState
  balance: number
  onBuy: (count: number) => void
}

export default function GeneratorCard({ name, gen, balance, onBuy }: GeneratorCardProps) {
  const canAfford1 = balance >= gen.cost_next
  // Rough check: can afford 10 if can afford at least the first
  const canAfford10 = canAfford1

  return (
    <div className="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="font-semibold text-gray-900 dark:text-gray-100">{name}</h4>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Owned: <span className="font-medium text-gray-700 dark:text-gray-200">{gen.owned}</span>
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-green-600 dark:text-green-400">
            {formatNumber(gen.production_per_sec)}/s
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3">
        <span className="text-sm text-gray-600 dark:text-gray-300">
          Cost: <span className="font-medium">{formatNumber(gen.cost_next)}</span>
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => onBuy(1)}
            disabled={!canAfford1}
            className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
              canAfford1
                ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
            }`}
          >
            Buy 1
          </button>
          <button
            onClick={() => onBuy(10)}
            disabled={!canAfford10}
            className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
              canAfford10
                ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
            }`}
          >
            Buy 10
          </button>
        </div>
      </div>
    </div>
  )
}
