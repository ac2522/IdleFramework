import { useState, useEffect } from 'react'
import { listGames } from '../../api/games'
import type { GameSummary } from '../../api/types'

const OPTIMIZERS = [
  { value: 'greedy', label: 'Greedy' },
  { value: 'beam', label: 'Beam Search' },
  { value: 'mcts', label: 'MCTS' },
  { value: 'bnb', label: 'Branch & Bound' },
]

interface AnalysisControlsProps {
  loading: boolean
  onRunAnalysis: (gameId: string, time: number, optimizer: string) => void
  onRunCompare: (gameId: string, time: number) => void
}

export default function AnalysisControls({
  loading,
  onRunAnalysis,
  onRunCompare,
}: AnalysisControlsProps) {
  const [games, setGames] = useState<GameSummary[]>([])
  const [gameId, setGameId] = useState('minicap')
  const [optimizer, setOptimizer] = useState('greedy')
  const [simulationTime, setSimulationTime] = useState(300)
  const [gamesError, setGamesError] = useState<string | null>(null)

  useEffect(() => {
    listGames()
      .then(({ games: g }) => {
        setGames(g)
        if (g.length > 0 && !g.find((x) => x.id === gameId)) {
          setGameId(g[0].id)
        }
      })
      .catch((err) => {
        setGamesError(err instanceof Error ? err.message : 'Failed to load games')
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <h2 className="mb-4 text-lg font-semibold">Analysis Controls</h2>

      {gamesError && (
        <p className="mb-3 text-sm text-red-500">{gamesError}</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Game select */}
        <div>
          <label htmlFor="game-select" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Game
          </label>
          <select
            id="game-select"
            value={gameId}
            onChange={(e) => setGameId(e.target.value)}
            disabled={loading}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          >
            {games.length === 0 && <option value={gameId}>{gameId}</option>}
            {games.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name} ({g.node_count} nodes)
              </option>
            ))}
          </select>
        </div>

        {/* Optimizer select */}
        <div>
          <label htmlFor="optimizer-select" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Optimizer
          </label>
          <select
            id="optimizer-select"
            value={optimizer}
            onChange={(e) => setOptimizer(e.target.value)}
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
          className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-gray-900"
        >
          {loading ? (
            <>
              <svg
                className="-ml-1 mr-2 h-4 w-4 animate-spin text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Running...
            </>
          ) : (
            'Run Analysis'
          )}
        </button>
        <button
          onClick={() => onRunCompare(gameId, simulationTime)}
          disabled={loading}
          className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 dark:focus:ring-offset-gray-900"
        >
          Compare Free vs Paid
        </button>
      </div>
    </div>
  )
}
