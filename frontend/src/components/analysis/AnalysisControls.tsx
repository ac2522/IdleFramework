import { useState } from 'react'
import type { OptimizerType } from '../../api/types'
import GameSelector from '../layout/GameSelector'

const OPTIMIZERS = [
  { value: 'greedy', label: 'Greedy' },
  { value: 'beam', label: 'Beam Search' },
  { value: 'mcts', label: 'MCTS' },
  { value: 'bnb', label: 'Branch & Bound' },
]

interface AnalysisControlsProps {
  loading: boolean
  onRunAnalysis: (gameId: string, time: number, optimizer: OptimizerType) => void
  onRunCompare: (gameId: string, time: number) => void
}

export default function AnalysisControls({
  loading,
  onRunAnalysis,
  onRunCompare,
}: AnalysisControlsProps) {
  const [gameId, setGameId] = useState('minicap')
  const [optimizer, setOptimizer] = useState<OptimizerType>('greedy')
  const [simulationTime, setSimulationTime] = useState(300)

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Analysis Controls</h2>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Game select via GameSelector */}
        <div>
          <GameSelector value={gameId} onChange={setGameId} disabled={loading} />
        </div>

        {/* Optimizer select */}
        <div>
          <label htmlFor="optimizer-select" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Optimizer
          </label>
          <select
            id="optimizer-select"
            value={optimizer}
            onChange={(e) => setOptimizer(e.target.value as OptimizerType)}
            disabled={loading}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          >
            {OPTIMIZERS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        {/* Simulation time */}
        <div>
          <label htmlFor="sim-time" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Simulation Time (s)
          </label>
          <input
            id="sim-time"
            type="number"
            min={1}
            value={simulationTime}
            onChange={(e) => setSimulationTime(Number(e.target.value))}
            disabled={loading}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>
      </div>

      {/* Buttons */}
      <div className="mt-4 flex flex-wrap gap-3">
        <button
          onClick={() => onRunAnalysis(gameId, simulationTime, optimizer)}
          disabled={loading}
          className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer dark:focus:ring-offset-gray-900"
        >
          Run Analysis
        </button>
        <button
          onClick={() => onRunCompare(gameId, simulationTime)}
          disabled={loading}
          className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 dark:focus:ring-offset-gray-900"
        >
          Compare Free vs Paid
        </button>
      </div>
    </div>
  )
}
