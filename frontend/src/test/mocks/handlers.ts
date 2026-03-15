import { http, HttpResponse } from 'msw'

const baseUrl = '/api/v1'

export const handlers = [
  http.get(`${baseUrl}/games/`, () => {
    return HttpResponse.json({
      games: [
        { id: 'minicap', name: 'MiniCap', node_count: 14, edge_count: 12, bundled: true },
      ],
    })
  }),

  http.post(`${baseUrl}/engine/start`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({
      session_id: 'test-session-123',
      game_id: body.game_id,
      elapsed_time: 0,
      resources: { gold: { current_value: 50, production_rate: 0 } },
      generators: {},
      upgrades: {},
      prestige: null,
      achievements: [],
    })
  }),

  http.post(`${baseUrl}/engine/:sessionId/advance`, () => {
    return HttpResponse.json({
      session_id: 'test-session-123',
      game_id: 'minicap',
      elapsed_time: 10,
      resources: { gold: { current_value: 60, production_rate: 1 } },
      generators: {},
      upgrades: {},
      prestige: null,
      achievements: [],
    })
  }),
]
