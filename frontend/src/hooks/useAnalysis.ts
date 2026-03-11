import { useState, useCallback } from 'react'
import { runAnalysis as apiRunAnalysis, compareStrategies } from '../api/analysis'
import type { AnalysisResult, CompareResult } from '../api/types'

interface AnalysisState {
  loading: boolean
  error: string | null
  result: AnalysisResult | null
  compareResult: CompareResult | null
}

export function useAnalysis() {
  const [state, setState] = useState<AnalysisState>({
    loading: false,
    error: null,
    result: null,
    compareResult: null,
  })

  const runAnalysis = useCallback(
    async (gameId: string, simulationTime: number, optimizer: string) => {
      setState((prev) => ({ ...prev, loading: true, error: null, compareResult: null }))
      try {
        const result = await apiRunAnalysis({
          game_id: gameId,
          simulation_time: simulationTime,
          optimizer,
        })
        setState({ loading: false, error: null, result, compareResult: null })
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Analysis failed'
        setState((prev) => ({ ...prev, loading: false, error: message }))
      }
    },
    [],
  )

  const runCompare = useCallback(async (gameId: string, simulationTime: number) => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const compareResult = await compareStrategies({
        game_id: gameId,
        simulation_time: simulationTime,
      })
      setState((prev) => ({ ...prev, loading: false, error: null, compareResult }))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Comparison failed'
      setState((prev) => ({ ...prev, loading: false, error: message }))
    }
  }, [])

  return {
    ...state,
    runAnalysis,
    runCompare,
  }
}
