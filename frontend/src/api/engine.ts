import { apiFetch } from './client'
import type { SessionState, AutoOptimizeResponse } from './types'

export async function startSession(gameId: string, initialBalance = 50): Promise<SessionState> {
  return apiFetch('/engine/start', {
    method: 'POST',
    body: JSON.stringify({ game_id: gameId, initial_balance: initialBalance }),
  })
}

export async function getState(sessionId: string): Promise<SessionState> {
  return apiFetch(`/engine/${sessionId}/state`)
}

export async function advance(sessionId: string, seconds = 1): Promise<SessionState> {
  return apiFetch(`/engine/${sessionId}/advance`, {
    method: 'POST',
    body: JSON.stringify({ seconds }),
  })
}

export async function purchase(sessionId: string, nodeId: string, count = 1): Promise<SessionState> {
  return apiFetch(`/engine/${sessionId}/purchase`, {
    method: 'POST',
    body: JSON.stringify({ node_id: nodeId, count }),
  })
}

export async function prestige(sessionId: string): Promise<SessionState> {
  return apiFetch(`/engine/${sessionId}/prestige`, { method: 'POST' })
}

export async function autoOptimize(sessionId: string, params?: {
  target_time?: number
  max_steps?: number
}): Promise<AutoOptimizeResponse> {
  return apiFetch(`/engine/${sessionId}/auto-optimize`, {
    method: 'POST',
    body: JSON.stringify(params ?? {}),
  })
}
