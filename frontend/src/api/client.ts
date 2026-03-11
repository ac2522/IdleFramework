import type { ApiError } from './types'

export class ApiClientError extends Error {
  readonly apiError: ApiError

  constructor(apiError: ApiError) {
    super(apiError.detail)
    this.apiError = apiError
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
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
  if (res.status === 204) return undefined as T
  return res.json()
}
