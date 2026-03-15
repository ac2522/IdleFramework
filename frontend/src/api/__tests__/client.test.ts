import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/mocks/server'
import { listGames } from '../games'

describe('API client', () => {
  it('fetches game list successfully', async () => {
    const result = await listGames()
    expect(result.games).toHaveLength(1)
    expect(result.games[0].id).toBe('minicap')
    expect(result.games[0].name).toBe('MiniCap')
    expect(result.games[0].bundled).toBe(true)
  })

  it('throws on server error', async () => {
    server.use(
      http.get('/api/v1/games/', () => {
        return HttpResponse.json(
          { error: 'server_error', detail: 'Internal failure', status: 500 },
          { status: 500 },
        )
      }),
    )
    await expect(listGames()).rejects.toThrow()
  })
})
