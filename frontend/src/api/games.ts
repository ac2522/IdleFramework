import { apiFetch } from './client'
import type { GameSummary } from './types'

export async function listGames(): Promise<{ games: GameSummary[] }> {
  return apiFetch('/games/')
}

export async function getGame(gameId: string): Promise<Record<string, unknown>> {
  return apiFetch(`/games/${gameId}`)
}

export async function createGame(gameJson: Record<string, unknown>): Promise<{ id: string; name: string }> {
  return apiFetch('/games/', { method: 'POST', body: JSON.stringify(gameJson) })
}

export async function deleteGame(gameId: string): Promise<void> {
  await fetch(`/api/v1/games/${gameId}`, { method: 'DELETE' })
}
