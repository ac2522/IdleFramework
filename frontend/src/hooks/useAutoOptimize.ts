import { useState, useCallback } from 'react'
import type { AutoOptimizeResponse } from '../api/types'

interface UseAutoOptimizeReturn {
  result: AutoOptimizeResponse | null
  loading: boolean
  error: string | null
  run: (params?: { target_time?: number; max_steps?: number }) => Promise<void>
  clear: () => void
}

export function useAutoOptimize(
  runAutoOptimize: (params?: { target_time?: number; max_steps?: number }) => Promise<AutoOptimizeResponse>
): UseAutoOptimizeReturn {
  const [result, setResult] = useState<AutoOptimizeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (params?: { target_time?: number; max_steps?: number }) => {
    setLoading(true)
    setError(null)
    try {
      const res = await runAutoOptimize(params)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Auto-optimize failed')
    } finally {
      setLoading(false)
    }
  }, [runAutoOptimize])

  const clear = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { result, loading, error, run, clear }
}
