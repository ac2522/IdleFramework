import { useEffect, useCallback } from 'react'
import { useGameSession } from '../hooks/useGameSession'
import { useGameTick } from '../hooks/useGameTick'
import { useAutoOptimize } from '../hooks/useAutoOptimize'
import ResourceDisplay from '../components/game/ResourceDisplay'
import GeneratorCard from '../components/game/GeneratorCard'
import ProductionSummary from '../components/game/ProductionSummary'
import UpgradeCard from '../components/game/UpgradeCard'
import PrestigePanel from '../components/game/PrestigePanel'
import PurchaseTimeline from '../components/game/PurchaseTimeline'

const DEFAULT_GAME = 'minicap'
const SPEED_OPTIONS = [1, 10, 100] as const

export default function PlayPage() {
  const {
    state,
    loading,
    error,
    start,
    advanceTime,
    purchaseNode,
    doPrestige,
    runAutoOptimize,
    clearError,
  } = useGameSession()

  const tick = useGameTick({ onTick: advanceTime })
  const optimizer = useAutoOptimize(runAutoOptimize)

  // Start session on mount
  useEffect(() => {
    start(DEFAULT_GAME)
  }, [start])

  const handleAutoOptimize = useCallback(async () => {
    tick.pause()
    await optimizer.run()
  }, [tick, optimizer])

  // Loading / error states
  if (loading && !state) {
    return (
      <div className="text-center py-20 text-gray-500 dark:text-gray-400">
        Starting game session...
      </div>
    )
  }

  if (error && !state) {
    return (
      <div className="text-center py-20">
        <p className="text-red-500 mb-4">{error}</p>
        <button
          onClick={() => { clearError(); start(DEFAULT_GAME); }}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!state) return null

  // Derive balance from first resource (typically "coins" or similar)
  const resourceEntries = Object.entries(state.resources)
  const balance = resourceEntries.length > 0 ? resourceEntries[0][1].current_value : 0

  const generatorEntries = Object.entries(state.generators)
  const upgradeEntries = Object.entries(state.upgrades).filter(([, u]) => !u.purchased)
  const hasPrestige = state.prestige !== null

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      {/* Left sidebar */}
      <div className="w-full lg:w-72 shrink-0 space-y-6">
        {/* Controls */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <button
              onClick={tick.toggle}
              className={`flex-1 py-2 text-sm font-semibold rounded-md transition-colors cursor-pointer ${
                tick.running
                  ? 'bg-red-500 hover:bg-red-600 text-white'
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              {tick.running ? 'Pause' : 'Resume'}
            </button>
          </div>

          {/* Speed controls */}
          <div className="flex gap-1">
            {SPEED_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => tick.setSpeed(s)}
                className={`flex-1 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  tick.speed === s
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          {/* Auto-optimize button */}
          <button
            onClick={handleAutoOptimize}
            disabled={optimizer.loading}
            className={`w-full py-2 text-sm font-semibold rounded-md transition-colors cursor-pointer ${
              optimizer.loading
                ? 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white'
            }`}
          >
            {optimizer.loading ? 'Optimizing...' : 'Auto-Optimize'}
          </button>
        </div>

        {/* Resources */}
        <ResourceDisplay resources={state.resources} />

        {/* Production summary */}
        <ProductionSummary resources={state.resources} elapsedTime={state.elapsed_time} />

        {/* Upgrades */}
        {upgradeEntries.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
              Upgrades
            </h3>
            {upgradeEntries.map(([name, upg]) => (
              <UpgradeCard
                key={name}
                name={name}
                upgrade={upg}
                onBuy={() => purchaseNode(name)}
              />
            ))}
          </div>
        )}

        {/* Prestige */}
        {hasPrestige && state.prestige && (
          <PrestigePanel prestige={state.prestige} onPrestige={doPrestige} />
        )}
      </div>

      {/* Main area */}
      <div className="flex-1 space-y-6">
        {/* Error banner */}
        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 flex items-center justify-between">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            <button
              onClick={clearError}
              className="text-red-400 hover:text-red-600 dark:hover:text-red-300 text-sm cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Optimizer result */}
        {optimizer.error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3">
            <p className="text-sm text-red-600 dark:text-red-400">{optimizer.error}</p>
          </div>
        )}

        {optimizer.result && (
          <PurchaseTimeline result={optimizer.result} onClear={optimizer.clear} />
        )}

        {/* Generators */}
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-3">Generators</h2>
          {generatorEntries.length === 0 ? (
            <p className="text-gray-400 dark:text-gray-500">No generators available</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {generatorEntries.map(([name, gen]) => (
                <GeneratorCard
                  key={name}
                  name={name}
                  gen={gen}
                  balance={balance}
                  onBuy={(count) => purchaseNode(name, count)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
