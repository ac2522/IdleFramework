import { apiFetch } from './client'
import type { AnalysisResult, CompareResult } from './types'

export async function runAnalysis(params: {
  game_id: string
  simulation_time?: number
  optimizer?: string
}): Promise<AnalysisResult> {
  return apiFetch('/analysis/run', { method: 'POST', body: JSON.stringify(params) })
}

export async function compareStrategies(params: {
  game_id: string
  strategies?: string[]
  simulation_time?: number
}): Promise<CompareResult> {
  return apiFetch('/analysis/compare', { method: 'POST', body: JSON.stringify(params) })
}

export async function generateReport(params: {
  game_id: string
  simulation_time?: number
}): Promise<string> {
  const res = await fetch('/api/v1/analysis/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return res.text()
}
