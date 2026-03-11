import { useAnalysis } from '../hooks/useAnalysis'
import AnalysisControls from '../components/analysis/AnalysisControls'
import ResultsPanel from '../components/analysis/ResultsPanel'
import ChartPanel from '../components/analysis/ChartPanel'
import ComparisonView from '../components/analysis/ComparisonView'

export default function AnalyzePage() {
  const { loading, error, result, compareResult, runAnalysis, runCompare } = useAnalysis()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Game Analysis</h1>

      {/* Controls */}
      <AnalysisControls loading={loading} onRunAnalysis={runAnalysis} onRunCompare={runCompare} />

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Loading spinner */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <svg
            className="h-8 w-8 animate-spin text-blue-600"
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
          <span className="ml-3 text-gray-500 dark:text-gray-400">Running analysis...</span>
        </div>
      )}

      {/* Comparison view */}
      {compareResult && !loading && <ComparisonView compareResult={compareResult} />}

      {/* Results: two-column layout */}
      {result && !loading && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left column: results */}
          <div>
            <ResultsPanel result={result} />
          </div>

          {/* Right column: charts */}
          <div>
            <ChartPanel result={result} />
          </div>
        </div>
      )}
    </div>
  )
}
