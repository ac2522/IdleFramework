import { useState, useCallback, useRef } from 'react'
import type { SessionState, AutoOptimizeResponse } from '../api/types'
import * as engine from '../api/engine'

interface UseGameSessionReturn {
  state: SessionState | null
  loading: boolean
  error: string | null
  start: (gameId: string, initialBalance?: number) => Promise<void>
  advanceTime: (seconds: number) => Promise<void>
  purchaseNode: (nodeId: string, count?: number) => Promise<void>
  doPrestige: () => Promise<void>
  runAutoOptimize: (params?: { target_time?: number; max_steps?: number }) => Promise<AutoOptimizeResponse>
  clearError: () => void
}

export function useGameSession(): UseGameSessionReturn {
  const [state, setState] = useState<SessionState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sessionRef = useRef<string | null>(null)

  const clearError = useCallback(() => setError(null), [])

  const start = useCallback(async (gameId: string, initialBalance = 50) => {
    setLoading(true)
    setError(null)
    try {
      const s = await engine.startSession(gameId, initialBalance)
      sessionRef.current = s.session_id
      setState(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start session')
    } finally {
      setLoading(false)
    }
  }, [])

  const advanceTime = useCallback(async (seconds: number) => {
    const sid = sessionRef.current
    if (!sid) return
    try {
      const s = await engine.advance(sid, seconds)
      setState(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to advance time')
    }
  }, [])

  const purchaseNode = useCallback(async (nodeId: string, count = 1) => {
    const sid = sessionRef.current
    if (!sid) return
    try {
      const s = await engine.purchase(sid, nodeId, count)
      setState(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to purchase')
    }
  }, [])

  const doPrestige = useCallback(async () => {
    const sid = sessionRef.current
    if (!sid) return
    try {
      const s = await engine.prestige(sid)
      setState(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to prestige')
    }
  }, [])

  const runAutoOptimize = useCallback(async (params?: { target_time?: number; max_steps?: number }) => {
    const sid = sessionRef.current
    if (!sid) throw new Error('No active session')
    return engine.autoOptimize(sid, params)
  }, [])

  return { state, loading, error, start, advanceTime, purchaseNode, doPrestige, runAutoOptimize, clearError }
}
