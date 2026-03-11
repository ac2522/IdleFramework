import { apiFetch, ApiClientError } from './client'
import type { AnalysisResult, CompareResult, ApiError, OptimizerType } from './types'

export async function runAnalysis(params: {
  game_id: string
  simulation_time?: number
  optimizer?: OptimizerType
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
  if (!res.ok) {
    let apiError: ApiError
    try {
      const body = await res.json()
      apiError = body.detail ?? body
    } catch {
      apiError = { error: 'unknown', detail: res.statusText, status: res.status }
    }
    throw new ApiClientError(apiError)
  }
  return res.text()
}
