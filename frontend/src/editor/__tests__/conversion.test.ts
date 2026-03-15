import { describe, it, expect } from 'vitest'
import { graphToGame, gameToGraph } from '../conversion'
import type { GameDefinitionJSON } from '../conversion'
import type { EditorNode } from '../types'
import type { Edge } from '@xyflow/react'

describe('graphToGame', () => {
  it('converts a simple graph to game JSON', () => {
    const nodes: EditorNode[] = [
      {
        id: 'res-1',
        type: 'resource',
        position: { x: 0, y: 0 },
        data: {
          nodeType: 'resource',
          label: 'Gold',
          name: 'Gold',
          initial_value: 100,
          tags: [],
          activation_mode: 'automatic',
          pull_mode: 'pull_any',
          cooldown_time: null,
        },
      },
      {
        id: 'gen-1',
        type: 'generator',
        position: { x: 200, y: 0 },
        data: {
          nodeType: 'generator',
          label: 'Miner',
          name: 'Miner',
          cost_base: 10,
          cost_growth_rate: 1.15,
          base_production: 1.0,
          cycle_time: 1.0,
          tags: [],
          activation_mode: 'automatic',
          pull_mode: 'pull_any',
          cooldown_time: null,
        },
      },
    ]
    const edges: Edge[] = [
      {
        id: 'e1',
        source: 'gen-1',
        target: 'res-1',
        type: 'resource',
        data: { edgeType: 'production_target' },
      },
    ]

    const game = graphToGame(nodes, edges, { name: 'Test Game', stacking_groups: {} })

    expect(game.schema_version).toBe('1.0')
    expect(game.name).toBe('Test Game')
    expect(game.nodes).toHaveLength(2)
    expect(game.edges).toHaveLength(1)
    expect(game.stacking_groups).toEqual({})

    // Check node conversion
    const resNode = game.nodes.find((n) => n.id === 'res-1')
    expect(resNode).toBeDefined()
    expect(resNode!.type).toBe('resource')
    expect(resNode!.initial_value).toBe(100)

    const genNode = game.nodes.find((n) => n.id === 'gen-1')
    expect(genNode).toBeDefined()
    expect(genNode!.type).toBe('generator')
    expect(genNode!.cost_base).toBe(10)

    // Check edge conversion
    expect(game.edges[0].edge_type).toBe('production_target')
    expect(game.edges[0].source).toBe('gen-1')
    expect(game.edges[0].target).toBe('res-1')
  })

  it('includes optional metadata fields', () => {
    const nodes: EditorNode[] = []
    const edges: Edge[] = []

    const game = graphToGame(nodes, edges, {
      name: 'With Description',
      description: 'A test game',
      stacking_groups: { group1: 'multiplicative' },
      time_unit: 'seconds',
    })

    expect(game.description).toBe('A test game')
    expect(game.time_unit).toBe('seconds')
    expect(game.stacking_groups).toEqual({ group1: 'multiplicative' })
  })
})

describe('gameToGraph', () => {
  it('converts a game JSON to editor nodes and edges', () => {
    const gameJson: GameDefinitionJSON = {
      schema_version: '1.0',
      name: 'Test',
      nodes: [
        { id: 'gold', type: 'resource', name: 'Gold', initial_value: 50 },
        { id: 'miner', type: 'generator', name: 'Miner', cost_base: 10, cost_growth_rate: 1.15, base_production: 1, cycle_time: 1 },
      ],
      edges: [
        { id: 'e1', source: 'miner', target: 'gold', edge_type: 'production_target' },
      ],
      stacking_groups: {},
    }

    const { nodes, edges } = gameToGraph(gameJson)

    expect(nodes).toHaveLength(2)
    expect(edges).toHaveLength(1)

    // Check node data
    const resNode = nodes.find((n) => n.id === 'gold')
    expect(resNode).toBeDefined()
    expect(resNode!.type).toBe('resource')
    expect(resNode!.data.nodeType).toBe('resource')
    expect(resNode!.data.label).toBe('Gold')

    // Check edge data
    expect(edges[0].source).toBe('miner')
    expect(edges[0].target).toBe('gold')
    expect(edges[0].type).toBe('resource') // production_target is a resource edge type
    expect((edges[0].data as Record<string, unknown>).edgeType).toBe('production_target')

    // Check positions were assigned (dagre layout)
    expect(typeof resNode!.position.x).toBe('number')
    expect(typeof resNode!.position.y).toBe('number')
  })
})

describe('round-trip', () => {
  it('round-trips a game through graph and back', () => {
    const gameJson: GameDefinitionJSON = {
      schema_version: '1.0',
      name: 'Round Trip Test',
      nodes: [
        { id: 'gold', type: 'resource', name: 'Gold', initial_value: 50 },
        { id: 'miner', type: 'generator', name: 'Miner', cost_base: 10, cost_growth_rate: 1.15, base_production: 1, cycle_time: 1 },
      ],
      edges: [
        { id: 'e1', source: 'miner', target: 'gold', edge_type: 'production_target' },
      ],
      stacking_groups: {},
    }

    const { nodes, edges } = gameToGraph(gameJson)
    const result = graphToGame(nodes, edges, { name: 'Round Trip Test', stacking_groups: {} })

    expect(result.nodes).toHaveLength(2)
    expect(result.edges).toHaveLength(1)
    expect(result.name).toBe('Round Trip Test')

    // Verify node types survived the round trip
    const resNode = result.nodes.find((n) => n.id === 'gold')
    expect(resNode!.type).toBe('resource')
    const genNode = result.nodes.find((n) => n.id === 'miner')
    expect(genNode!.type).toBe('generator')

    // Verify edge type survived the round trip
    expect(result.edges[0].edge_type).toBe('production_target')
  })
})
