import type { AnalysisResult } from '../../api/types'
import { formatNumber, formatTime } from '../../utils/formatting'

interface ResultsPanelProps {
  result: AnalysisResult
}

export default function ResultsPanel({ result }: ResultsPanelProps) {
  const opt = result.optimizer_result

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-base font-semibold">Summary</h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500 dark:text-gray-400">Game</dt>
          <dd className="font-medium">{result.game_name}</dd>
          <dt className="text-gray-500 dark:text-gray-400">Simulation Time</dt>
          <dd className="font-medium">{formatTime(result.simulation_time)}</dd>
          {opt && (
            <>
              <dt className="text-gray-500 dark:text-gray-400">Purchases</dt>
              <dd className="font-medium">{opt.purchases.length}</dd>
              <dt className="text-gray-500 dark:text-gray-400">Final Production</dt>
              <dd className="font-medium">{formatNumber(opt.final_production)}/s</dd>
              <dt className="text-gray-500 dark:text-gray-400">Final Balance</dt>
              <dd className="font-medium">{formatNumber(opt.final_balance)}</dd>
            </>
          )}
        </dl>
      </div>

      {/* Dead upgrades */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-base font-semibold">Dead Upgrades</h3>
        {result.dead_upgrades.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No dead upgrades found.</p>
        ) : (
          <ul className="space-y-2">
            {result.dead_upgrades.map((du) => (
              <li
                key={du.upgrade_id}
                className="flex items-start gap-2 rounded-md bg-red-50 p-2 text-sm dark:bg-red-900/20"
              >
                <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-red-500" />
                <div>
                  <span className="font-medium text-red-800 dark:text-red-300">{du.upgrade_id}</span>
                  <span className="ml-1 text-red-700 dark:text-red-400">— {du.reason}</span>
                  {du.cost !== undefined && (
                    <span className="ml-1 text-red-600 dark:text-red-500">(cost: {formatNumber(du.cost)})</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Progression walls */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-base font-semibold">Progression Walls</h3>
        {result.progression_walls.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No progression walls detected.</p>
        ) : (
          <ul className="space-y-2">
            {result.progression_walls.map((pw, i) => (
              <li
                key={i}
                className="flex items-start gap-2 rounded-md bg-yellow-50 p-2 text-sm dark:bg-yellow-900/20"
              >
                <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-yellow-500" />
                <div>
                  <span className="text-yellow-800 dark:text-yellow-300">{pw.reason}</span>
                  {pw.severity && (
                    <span className="ml-2 inline-block rounded-full bg-yellow-200 px-2 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-800 dark:text-yellow-200">
                      {pw.severity}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Dominant strategy */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-base font-semibold">Dominant Strategy</h3>
        {!result.dominant_strategy || !result.dominant_strategy.dominant_gen ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No dominant generator detected — well balanced.</p>
        ) : (
          <div className="text-sm">
            <p>
              <span className="font-medium text-purple-700 dark:text-purple-400">
                {result.dominant_strategy.dominant_gen}
              </span>{' '}
              dominates with{' '}
              <span className="font-medium">{(result.dominant_strategy.ratio * 100).toFixed(1)}%</span> of
              total production.
            </p>
            <div className="mt-2">
              <p className="mb-1 text-gray-500 dark:text-gray-400">Production by generator:</p>
              <div className="space-y-1">
                {Object.entries(result.dominant_strategy.productions).map(([gen, prod]) => (
                  <div key={gen} className="flex justify-between">
                    <span>{gen}</span>
                    <span className="font-mono">{formatNumber(prod)}/s</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Purchase timeline table */}
      {opt && opt.purchases.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <h3 className="mb-3 text-base font-semibold">Purchase Timeline</h3>
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                <tr>
                  <th className="px-2 py-2">Time</th>
                  <th className="px-2 py-2">Node</th>
                  <th className="px-2 py-2 text-right">Cost</th>
                  <th className="px-2 py-2 text-right">Qty</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {opt.purchases.map((p, i) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="whitespace-nowrap px-2 py-1.5 font-mono text-xs">
                      {formatTime(p.time)}
                    </td>
                    <td className="px-2 py-1.5">{p.node_id}</td>
                    <td className="px-2 py-1.5 text-right font-mono text-xs">
                      {formatNumber(p.cost)}
                    </td>
                    <td className="px-2 py-1.5 text-right">{p.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
