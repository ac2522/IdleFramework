import { useAnalysis } from '../hooks/useAnalysis'
import AnalysisControls from '../components/analysis/AnalysisControls'
import ResultsPanel from '../components/analysis/ResultsPanel'
import ChartPanel from '../components/analysis/ChartPanel'
import ComparisonView from '../components/analysis/ComparisonView'
import Spinner from '../components/ui/Spinner'
import ErrorBanner from '../components/ui/ErrorBanner'

export default function AnalyzePage() {
  const { loading, error, result, compareResult, runAnalysis, runCompare } = useAnalysis()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Game Analysis</h1>

      {/* Controls */}
      <AnalysisControls loading={loading} onRunAnalysis={runAnalysis} onRunCompare={runCompare} />

      {/* Error */}
      {error && <ErrorBanner message={error} />}

      {/* Loading spinner */}
      {loading && <Spinner size="lg" label="Running analysis..." className="py-12" />}

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
